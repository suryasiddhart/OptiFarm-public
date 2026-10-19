"""MQTT → Kafka bridge.

Subscribes to optifarm/v1/devices/+/telemetry and produces each message to
the telemetry topic unchanged, keyed by the device ID taken from the topic
(never from the payload), so all of a device's messages land in one
partition in arrival order. The receive time is attached as the
`received_at` header for devices that don't send a timestamp.

Delivery guarantee: the MQTT session is persistent and messages are
acknowledged to the broker (manual PUBACK) only after Kafka confirmed the
write. If the bridge dies in between, the broker redelivers on reconnect;
the resulting duplicates are dropped by the consumer's
ON CONFLICT (deviceid, rtctime) DO NOTHING.
"""

import logging
import signal
import sys
import threading
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
from confluent_kafka import KafkaError, KafkaException, Producer

from config import Settings, deviceid_from_topic, telemetry_subscription

logger = logging.getLogger("bridge")


class Bridge:
    def __init__(self, settings: Settings, producer: Producer, mqtt_client: mqtt.Client):
        self.settings = settings
        self.producer = producer
        self.mqtt = mqtt_client
        self.fatal = threading.Event()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logger.error("MQTT connect refused: %s", reason_code)
            return
        logger.info("Connected to MQTT (session present: %s)", flags.session_present)
        client.subscribe(telemetry_subscription(self.settings), qos=1)

    def on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        deviceid = deviceid_from_topic(self.settings, msg.topic)
        if deviceid is None:
            logger.warning("Ignoring message on unexpected topic %s", msg.topic)
            client.ack(msg.mid, msg.qos)
            return
        received_at = datetime.now(timezone.utc).isoformat()

        def delivered(err: KafkaError | None, _record):
            if err is not None:
                # Leave the message un-acked and restart: the broker redelivers
                # it once the bridge reconnects.
                logger.error("Kafka delivery failed for %s: %s", deviceid, err)
                self.fatal.set()
                return
            client.ack(msg.mid, msg.qos)

        try:
            self.producer.produce(
                self.settings.kafka_telemetry_topic,
                key=deviceid.encode(),
                value=msg.payload,
                headers={"received_at": received_at.encode(), "mqtt_topic": msg.topic.encode()},
                on_delivery=delivered,
            )
        except KafkaException as exc:
            if exc.args[0].code() == KafkaError.MSG_SIZE_TOO_LARGE:
                # Can never be delivered (the broker's max_packet_size should stop these
                # first): drop it instead of retrying it forever.
                logger.error("Dropping %d-byte message from %s: larger than Kafka allows",
                             len(msg.payload), deviceid)
                client.ack(msg.mid, msg.qos)
                return
            logger.error("Kafka produce failed for %s: %s", deviceid, exc)
            self.fatal.set()
        except BufferError:
            # Local queue full (Kafka unreachable for a while): restart, the
            # broker keeps the un-acked messages.
            logger.error("Kafka producer queue full")
            self.fatal.set()


def build(settings: Settings) -> Bridge:
    producer = Producer({
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "enable.idempotence": True,   # implies acks=all; keeps per-partition order on retry
        "acks": "all",
        "linger.ms": 20,
        "compression.type": "lz4",
        "message.timeout.ms": 120000,
    })
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="optifarm-bridge",
        clean_session=False,          # broker queues QoS 1 messages while we're away
        protocol=mqtt.MQTTv311,
    )
    client.manual_ack_set(True)
    client.username_pw_set(settings.mqtt_bridge_username, settings.mqtt_bridge_password)
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    bridge = Bridge(settings, producer, client)
    client.on_connect = bridge.on_connect
    client.on_message = bridge.on_message
    return bridge


def main() -> int:
    settings = Settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    bridge = build(settings)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())

    bridge.mqtt.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=30)
    bridge.mqtt.loop_start()
    logger.info("Bridging %s → %s", telemetry_subscription(settings), settings.kafka_telemetry_topic)
    try:
        while not stop.is_set() and not bridge.fatal.is_set():
            bridge.producer.poll(0.2)   # runs delivery callbacks (which send the PUBACKs)
    finally:
        bridge.producer.flush(10)
        bridge.mqtt.disconnect()
        bridge.mqtt.loop_stop()
    return 1 if bridge.fatal.is_set() else 0


if __name__ == "__main__":
    sys.exit(main())
