"""Kafka → TimescaleDB consumer.

Reads telemetry in batches, validates each message, maps the device to its
owner (userinfo) and field, checks the moisture cells against that field's
grid, and bulk-upserts into appschema.moisturedata. A reading that already
exists for (deviceid, rtctime) gets the new cells merged in, so redelivered
messages are harmless and a grid may arrive in several parts. Kafka offsets are committed only after the database commit; if
the write fails the batch is re-read from the last committed offsets.

Messages that can never be stored (bad JSON, schema errors, implausible
timestamps, unknown or disabled devices, devices without a field, cells
outside the field's grid) go to the DLQ topic with the reason
in the `error` header.
"""

import json
import logging
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from confluent_kafka import Consumer, Message, Producer, TopicPartition
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config import Settings
from grid import cells_outside_grid, grid_size
from schemas import Row, Telemetry, to_rows

logger = logging.getLogger("consumer")

INSERT_SQL = text("""
    INSERT INTO appschema.moisturedata (moisture, rtctime, deviceid, userinfo, fieldid)
    VALUES (CAST(:moisture AS jsonb), :rtctime, :deviceid, :userinfo, :fieldid)
    ON CONFLICT (deviceid, rtctime) DO UPDATE
        SET moisture = COALESCE(appschema.moisturedata.moisture, '{}'::jsonb) || EXCLUDED.moisture
""")
LAST_SEEN_SQL = text("""
    UPDATE appschema.devices
    SET last_seen = GREATEST(COALESCE(last_seen, :seen), :seen)
    WHERE deviceid = :deviceid
""")
DEVICES_SQL = text("""
    SELECT d.deviceid, d.userinfo, d.fieldid, d.status,
           f.fieldlength, f.fieldbreadth, f.cropinterval
    FROM appschema.devices d
    LEFT JOIN appschema.fielddetails f ON f.fieldid = d.fieldid
    WHERE d.deviceid = ANY(:ids)
""")


@dataclass(frozen=True)
class DeviceInfo:
    userinfo: int
    fieldid: int | None
    active: bool
    grid: tuple[int, int] | None = None   # (rows, cols) of the device's field


def _device_info(row) -> DeviceInfo:
    grid = None
    if row.fieldid is not None and row.cropinterval:
        grid = grid_size(row.fieldlength, row.fieldbreadth, row.cropinterval)
    return DeviceInfo(row.userinfo, row.fieldid, row.status == "active", grid)


class DeviceDirectory:
    """deviceid → owner/field, cached so each batch costs at most one query."""

    def __init__(self, engine: Engine, ttl_seconds: float):
        self.engine = engine
        self.ttl = ttl_seconds
        self._cache: dict[str, tuple[float, DeviceInfo | None]] = {}

    def lookup(self, deviceids: set[str]) -> dict[str, DeviceInfo | None]:
        now = time.monotonic()
        missing = [d for d in deviceids if d not in self._cache or self._cache[d][0] < now]
        if missing:
            with self.engine.connect() as conn:
                found = {r.deviceid: _device_info(r) for r in conn.execute(DEVICES_SQL, {"ids": missing})}
            for deviceid in missing:
                self._cache[deviceid] = (now + self.ttl, found.get(deviceid))
        return {d: self._cache[d][1] for d in deviceids}


@dataclass
class BatchResult:
    rows: list[dict] = field(default_factory=list)
    last_seen: dict[str, datetime] = field(default_factory=dict)
    rejected: list[tuple[Message, str]] = field(default_factory=list)


def _received_at(msg: Message) -> datetime:
    for name, value in msg.headers() or []:
        if name == "received_at" and value:
            return datetime.fromisoformat(value.decode())
    _, millis = msg.timestamp()
    return datetime.fromtimestamp(millis / 1000, timezone.utc)


def prepare_batch(messages: list[Message], directory: DeviceDirectory, settings: Settings) -> BatchResult:
    """Validate and enrich a batch; no side effects besides the device lookup."""
    result = BatchResult()
    parsed: list[tuple[Message, str, list[Row], datetime]] = []
    max_age = timedelta(days=settings.reading_max_age_days)
    max_skew = timedelta(seconds=settings.reading_max_future_skew_seconds)

    for msg in messages:
        deviceid = (msg.key() or b"").decode()
        if not deviceid:
            result.rejected.append((msg, "missing device key"))
            continue
        try:
            received_at = _received_at(msg)
            telemetry = Telemetry.model_validate_json(msg.value() or b"")
            rows = to_rows(deviceid, telemetry, received_at, max_age, max_skew)
        except ValidationError as exc:
            result.rejected.append((msg, f"invalid payload: {exc.errors(include_url=False)}"))
            continue
        except ValueError as exc:
            result.rejected.append((msg, str(exc)))
            continue
        parsed.append((msg, deviceid, rows, received_at))

    devices = directory.lookup({deviceid for _, deviceid, _, _ in parsed})
    for msg, deviceid, rows, received_at in parsed:
        info = devices.get(deviceid)
        if info is None:
            result.rejected.append((msg, "unknown device"))
            continue
        if not info.active:
            result.rejected.append((msg, "device disabled"))
            continue
        if info.grid is None:
            result.rejected.append((msg, "device has no field assigned (PATCH /devices/{id})"))
            continue
        n_rows, n_cols = info.grid
        outside = sorted({key for r in rows for key in cells_outside_grid(r.moisture, n_rows, n_cols)})
        if outside:
            result.rejected.append(
                (msg, f"cells outside the field's {n_rows} x {n_cols} grid: {', '.join(outside[:20])}"))
            continue
        result.rows.extend({"moisture": json.dumps(r.moisture), "rtctime": r.rtctime,
                            "deviceid": r.deviceid, "userinfo": info.userinfo,
                            "fieldid": info.fieldid} for r in rows)
        result.last_seen[deviceid] = max(received_at, result.last_seen.get(deviceid, received_at))
    return result


def store(engine: Engine, batch: BatchResult) -> None:
    if not batch.rows:
        return
    with engine.begin() as conn:
        conn.execute(INSERT_SQL, batch.rows)
        conn.execute(LAST_SEEN_SQL, [{"deviceid": d, "seen": t} for d, t in batch.last_seen.items()])


def send_to_dlq(producer: Producer, topic: str, rejected: list[tuple[Message, str]]) -> None:
    for msg, reason in rejected:
        logger.warning("DLQ %s (partition %s offset %s): %s",
                       (msg.key() or b"").decode(), msg.partition(), msg.offset(), reason)
        headers = list(msg.headers() or []) + [
            ("error", reason.encode()),
            ("source", json.dumps({"topic": msg.topic(), "partition": msg.partition(),
                                   "offset": msg.offset()}).encode()),
        ]
        producer.produce(topic, key=msg.key(), value=msg.value(), headers=headers)
    producer.flush(30)


def process(messages: list[Message], consumer: Consumer, producer: Producer, engine: Engine,
            directory: DeviceDirectory, settings: Settings) -> None:
    """Store a batch, then commit its offsets. Raises (without committing) on failure."""
    batch = prepare_batch(messages, directory, settings)
    store(engine, batch)
    if batch.rejected:
        send_to_dlq(producer, settings.kafka_dlq_topic, batch.rejected)
    consumer.commit(asynchronous=False)
    logger.info("Stored %d readings from %d messages (%d to DLQ)",
                len(batch.rows), len(messages), len(batch.rejected))


def rewind(consumer: Consumer, messages: list[Message]) -> None:
    """Seek each partition back to the first message of the failed batch."""
    first: dict[tuple[str, int], int] = {}
    for msg in messages:
        key = (msg.topic(), msg.partition())
        first[key] = min(first.get(key, msg.offset()), msg.offset())
    for (topic, partition), offset in first.items():
        consumer.seek(TopicPartition(topic, partition, offset))


def main() -> int:
    settings = Settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    engine = create_engine(settings.database_url, pool_size=2, pool_pre_ping=True)
    directory = DeviceDirectory(engine, settings.device_cache_ttl_seconds)
    consumer = Consumer({
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "group.id": settings.kafka_consumer_group,
        "enable.auto.commit": False,
        "auto.offset.reset": "earliest",
        "partition.assignment.strategy": "cooperative-sticky",
    })
    producer = Producer({"bootstrap.servers": settings.kafka_bootstrap_servers,
                         "enable.idempotence": True})
    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    consumer.subscribe([settings.kafka_telemetry_topic])
    logger.info("Consuming %s as group %s", settings.kafka_telemetry_topic, settings.kafka_consumer_group)
    try:
        while running:
            messages = consumer.consume(settings.batch_max_messages, settings.batch_timeout_seconds)
            errors = [m for m in messages if m.error()]
            for m in errors:
                logger.error("Kafka error: %s", m.error())
            messages = [m for m in messages if not m.error()]
            if not messages:
                continue
            try:
                process(messages, consumer, producer, engine, directory, settings)
            except Exception:
                logger.exception("Batch failed; retrying from the last committed offsets in %.0fs",
                                 settings.retry_backoff_seconds)
                rewind(consumer, messages)
                time.sleep(settings.retry_backoff_seconds)
    finally:
        consumer.close()
        producer.flush(10)
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main())
