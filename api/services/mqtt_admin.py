"""
Mosquitto dynamic-security admin client.

Device credentials are pushed to the running broker by publishing commands to
$CONTROL/dynamic-security/v1 and waiting for the matching reply on
$CONTROL/dynamic-security/v1/response. Changes apply immediately (no broker
restart). On broker start the full config is rebuilt from appschema.devices
by ingest/dynsec_sync.py, so the database stays the source of truth.
"""

import json
import logging
import threading
import uuid

import paho.mqtt.client as mqtt

from config.settings import settings

logger = logging.getLogger(__name__)

CONTROL_TOPIC = "$CONTROL/dynamic-security/v1"
RESPONSE_TOPIC = f"{CONTROL_TOPIC}/response"
# Shared role created by dynsec_sync: publish only to optifarm/v1/devices/%u/telemetry
DEVICE_ROLE = "device"


class BrokerError(Exception):
    """The broker could not be reached or rejected a command."""


def _run_commands(commands: list[dict]) -> list[dict]:
    if not settings.mqtt_admin_password:
        raise BrokerError("MQTT admin credentials are not configured")

    correlation = uuid.uuid4().hex
    for command in commands:
        command["correlationData"] = correlation

    done = threading.Event()
    responses: list[dict] = []
    subscribed = threading.Event()
    connect_error: list[str] = []

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            connect_error.append(str(reason_code))
            subscribed.set()

    def on_subscribe(client, userdata, mid, reason_codes, properties):
        subscribed.set()

    def on_message(client, userdata, msg):
        try:
            body = json.loads(msg.payload)
        except ValueError:
            return
        for response in body.get("responses", []):
            if response.get("correlationData") == correlation:
                responses.append(response)
        if len(responses) >= len(commands):
            done.set()

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"optifarm-api-{correlation[:12]}",
        protocol=mqtt.MQTTv5,
    )
    client.username_pw_set(settings.mqtt_admin_username, settings.mqtt_admin_password)
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    timeout = settings.mqtt_admin_timeout_seconds
    try:
        client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=30)
        client.loop_start()
        client.subscribe(RESPONSE_TOPIC, qos=1)
        if not subscribed.wait(timeout):
            raise BrokerError("Timed out subscribing to the dynamic-security response topic")
        if connect_error:
            raise BrokerError(f"MQTT admin login rejected: {connect_error[0]}")
        client.publish(CONTROL_TOPIC, json.dumps({"commands": commands}), qos=1)
        if not done.wait(timeout):
            raise BrokerError("Timed out waiting for the broker to apply device credentials")
    except (OSError, ValueError) as exc:
        raise BrokerError(f"MQTT broker unreachable: {exc}") from exc
    finally:
        client.loop_stop()
        client.disconnect()

    errors = [r for r in responses if r.get("error")]
    if errors:
        raise BrokerError("; ".join(f"{r['command']}: {r['error']}" for r in errors))
    return responses


def create_device_client(deviceid: str, passkey: str) -> None:
    try:
        _run_commands([{
            "command": "createClient",
            "username": deviceid,
            "password": passkey,
            "roles": [{"rolename": DEVICE_ROLE}],
        }])
    except BrokerError as exc:
        if "already exists" not in str(exc):
            raise
        # Stale broker client with no devices row (e.g. its owner was deleted
        # since the last broker restart): the caller holds the new row, so
        # replace the client with a fresh one.
        _run_commands([
            {"command": "deleteClient", "username": deviceid},
            {"command": "createClient", "username": deviceid, "password": passkey,
             "roles": [{"rolename": DEVICE_ROLE}]},
        ])


def set_device_passkey(deviceid: str, passkey: str) -> None:
    _run_commands([{"command": "setClientPassword", "username": deviceid, "password": passkey}])


def disable_device_client(deviceid: str) -> None:
    _run_commands([{"command": "disableClient", "username": deviceid}])


def delete_device_client(deviceid: str) -> None:
    """Best-effort cleanup when the DB write fails after the broker accepted a client."""
    try:
        _run_commands([{"command": "deleteClient", "username": deviceid}])
    except BrokerError:
        logger.exception("Could not remove MQTT client %s after a failed device insert", deviceid)
