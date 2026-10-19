"""Device data simulator: publishes moisture telemetry to MQTT like field devices.

One asyncio task per configured device, each with its own MQTT connection
(username = deviceid, password = the device passkey issued by POST /devices/),
publishing to optifarm/v1/devices/<deviceid>/telemetry. Connections are
retried with backoff; SIGTERM disconnects cleanly.

    python main.py                          # uses devices.yaml + env/.env settings
    MQTT_HOST=localhost python main.py
"""

import asyncio
import json
import logging
import random
import signal
import ssl
import sys
from datetime import datetime, timezone

import aiomqtt

from config import DeviceConfig, Settings, load_devices
from generator import FieldMoistureGenerator, MoistureProfile

logger = logging.getLogger("simulator")


def build_payloads(cells: dict[str, float], at: datetime, send_ts: bool,
                   max_cells: int) -> list[dict]:
    """One or more messages for a grid reading; parts share the same ts and are merged."""
    keys = list(cells)
    payloads = []
    for start in range(0, len(keys), max_cells):
        payload: dict = {"readings": {"moisture": {k: cells[k] for k in keys[start:start + max_cells]}}}
        if send_ts:
            payload["ts"] = at.isoformat().replace("+00:00", "Z")
        payloads.append(payload)
    return payloads


def make_generator(device: DeviceConfig) -> FieldMoistureGenerator:
    profile = MoistureProfile()
    if device.start is not None:
        profile.start = device.start
    if device.min is not None:
        profile.min_value = device.min
    if device.max is not None:
        profile.max_value = device.max
    rows, cols = device.grid
    seed = device.seed if device.seed is not None else device.deviceid
    return FieldMoistureGenerator(profile, seed, rows, cols, device.cell_spread)


def tls_context(settings: Settings) -> ssl.SSLContext | None:
    if not settings.mqtt_tls:
        return None
    return ssl.create_default_context(cafile=settings.mqtt_ca_file or None)


async def run_device(device: DeviceConfig, settings: Settings) -> None:
    interval = device.interval_seconds or settings.simulator_interval_seconds
    topic = f"{settings.mqtt_topic_prefix.rstrip('/')}/{device.deviceid}/telemetry"
    passkey = device.resolve_passkey()
    generator = make_generator(device)
    log = logger.getChild(device.deviceid)

    if settings.simulator_jitter_start:
        await asyncio.sleep(random.uniform(0, interval))

    backoff = 1.0
    last = datetime.now(timezone.utc)
    while True:
        try:
            async with aiomqtt.Client(
                settings.mqtt_host,
                settings.mqtt_port,
                username=device.deviceid,
                password=passkey,
                identifier=device.deviceid,
                keepalive=settings.mqtt_keepalive,
                tls_context=tls_context(settings),
            ) as client:
                log.info("connected to %s:%s", settings.mqtt_host, settings.mqtt_port)
                backoff = 1.0
                while True:
                    now = datetime.now(timezone.utc)
                    cells = generator.next(now, (now - last).total_seconds())
                    last = now
                    payloads = build_payloads(cells, now, device.send_ts, device.max_cells_per_message)
                    for payload in payloads:
                        await client.publish(topic, json.dumps(payload), qos=settings.mqtt_qos)
                        log.debug("published %s", payload)
                    log.info("%d cells in %d message(s), average moisture=%.2f", len(cells),
                             len(payloads), sum(cells.values()) / len(cells))
                    await asyncio.sleep(interval)
        except aiomqtt.MqttError as exc:
            log.warning("MQTT error: %s; reconnecting in %.0fs", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)


async def run(settings: Settings, devices: list[DeviceConfig]) -> None:
    tasks = [asyncio.create_task(run_device(d, settings), name=d.deviceid) for d in devices]
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: [t.cancel() for t in tasks])
    logger.info("Simulating %d device(s) against %s:%s (tls=%s)",
                len(devices), settings.mqtt_host, settings.mqtt_port, settings.mqtt_tls)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for task, result in zip(tasks, results):
        if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
            logger.error("device %s stopped: %s", task.get_name(), result)


def main() -> int:
    settings = Settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        devices = load_devices(settings.simulator_devices_file)
        for device in devices:
            device.resolve_passkey()
    except (OSError, ValueError) as exc:
        logger.error("Invalid simulator configuration: %s", exc)
        return 2
    asyncio.run(run(settings, devices))
    logger.info("Simulator stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
