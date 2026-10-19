"""Settings for the ingest services (bridge, consumer, dynsec_sync).

All values come from environment variables; in Kubernetes the passwords and
DATABASE_URL are injected from Key Vault via External Secrets
(see pipelines/charts/ingest and pipelines/charts/mosquitto).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # MQTT (bridge subscribes as the "bridge" dynsec client)
    mqtt_host: str = "mosquitto"
    mqtt_port: int = 1883
    mqtt_bridge_username: str = "bridge"
    mqtt_bridge_password: str = ""
    mqtt_topic_prefix: str = "optifarm/v1/devices"

    # Kafka
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_telemetry_topic: str = "telemetry.raw"
    kafka_dlq_topic: str = "telemetry.dlq"
    kafka_consumer_group: str = "ingest-timescale"

    # Consumer batching
    batch_max_messages: int = 500
    batch_timeout_seconds: float = 1.0
    device_cache_ttl_seconds: float = 60.0
    retry_backoff_seconds: float = 5.0

    # Readings whose device timestamp is outside [now - max_age, now + max_skew]
    # are sent to the DLQ instead of being stored at a wrong time.
    reading_max_age_days: int = 30
    reading_max_future_skew_seconds: int = 300

    # Database (consumer and dynsec_sync)
    database_url: str = ""

    # dynsec_sync: fixed broker clients (devices come from appschema.devices)
    mqtt_admin_username: str = "admin"
    mqtt_admin_password: str = ""

    log_level: str = "INFO"

    model_config = SettingsConfigDict(extra="ignore")


def telemetry_subscription(settings: Settings) -> str:
    return f"{settings.mqtt_topic_prefix}/+/telemetry"


def deviceid_from_topic(settings: Settings, topic: str) -> str | None:
    """optifarm/v1/devices/<deviceid>/telemetry -> <deviceid> (None if it doesn't match)."""
    prefix = settings.mqtt_topic_prefix.rstrip("/") + "/"
    if not topic.startswith(prefix) or not topic.endswith("/telemetry"):
        return None
    deviceid = topic[len(prefix):-len("/telemetry")]
    return deviceid if deviceid and "/" not in deviceid else None
