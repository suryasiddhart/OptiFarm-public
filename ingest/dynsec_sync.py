"""Generate Mosquitto's dynamic-security.json from appschema.devices.

Runs as an initContainer on the Mosquitto pod, so every broker start loads
credentials that match the database:
  - "admin"  — dynsec administration (used by the API to push device changes)
  - "bridge" — read-only subscriber on optifarm/v1/devices/+/telemetry
  - one client per active device: username = deviceid, password = the stored
    PBKDF2-SHA512 passkey hash, role "device" (publish only to its own topic)

Between restarts the API keeps the running broker in step through the
$CONTROL/dynamic-security/v1 topic (api/services/mqtt_admin.py).

Usage: python dynsec_sync.py /mosquitto/dynsec/dynamic-security.json
"""

import base64
import hashlib
import json
import logging
import os
import secrets
import sys
import tempfile

from sqlalchemy import create_engine, text

from config import Settings

logger = logging.getLogger("dynsec_sync")

ITERATIONS = 1000

ACTIVE_DEVICES_SQL = text("""
    SELECT deviceid, passkey_hash, passkey_salt, passkey_iterations
    FROM appschema.devices
    WHERE status = 'active'
    ORDER BY deviceid
""")


def encode_password(password: str) -> str:
    salt = secrets.token_bytes(64)
    digest = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, ITERATIONS, 64)
    return f"$7${ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def build_config(settings: Settings, devices: list[dict]) -> dict:
    if not settings.mqtt_admin_password or not settings.mqtt_bridge_password:
        raise SystemExit("MQTT_ADMIN_PASSWORD and MQTT_BRIDGE_PASSWORD must be set")
    prefix = settings.mqtt_topic_prefix.rstrip("/")
    control = "$CONTROL/dynamic-security/#"
    roles = [
        {"rolename": "admin", "acls": [
            {"acltype": "publishClientSend", "topic": control, "allow": True},
            {"acltype": "publishClientReceive", "topic": control, "allow": True},
            {"acltype": "subscribePattern", "topic": control, "allow": True},
            {"acltype": "unsubscribePattern", "topic": "#", "allow": True},
        ]},
        {"rolename": "bridge", "acls": [
            {"acltype": "subscribePattern", "topic": f"{prefix}/+/telemetry", "allow": True},
            {"acltype": "publishClientReceive", "topic": f"{prefix}/+/telemetry", "allow": True},
        ]},
        # %u is replaced by the client's username (= deviceid) at check time
        {"rolename": "device", "acls": [
            {"acltype": "publishClientSend", "topic": f"{prefix}/%u/telemetry", "allow": True},
        ]},
    ]
    clients = [
        {"username": settings.mqtt_admin_username, "textName": "OptiFarm API (dynsec admin)",
         "encoded_password": encode_password(settings.mqtt_admin_password),
         "roles": [{"rolename": "admin"}]},
        {"username": settings.mqtt_bridge_username, "textName": "MQTT to Kafka bridge",
         "encoded_password": encode_password(settings.mqtt_bridge_password),
         "roles": [{"rolename": "bridge"}]},
    ]
    reserved = {settings.mqtt_admin_username, settings.mqtt_bridge_username}
    for device in devices:
        if device["deviceid"] in reserved:
            logger.warning("Skipping device %s: name is reserved for a system client", device["deviceid"])
            continue
        clients.append({
            "username": device["deviceid"],
            "encoded_password": f"$7${device['passkey_iterations']}${device['passkey_salt']}${device['passkey_hash']}",
            "roles": [{"rolename": "device"}],
        })
    return {
        "clients": clients,
        "groups": [],
        "roles": roles,
        "defaultACLAccess": {
            "publishClientSend": False,
            "publishClientReceive": True,
            "subscribe": False,
            "unsubscribe": True,
        },
    }


def write_atomically(path: str, config: dict) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".dynsec-")
    with os.fdopen(fd, "w") as f:
        json.dump(config, f, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    settings = Settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    engine = create_engine(settings.database_url)
    try:
        with engine.connect() as conn:
            devices = [dict(r._mapping) for r in conn.execute(ACTIVE_DEVICES_SQL)]
    finally:
        engine.dispose()
    write_atomically(sys.argv[1], build_config(settings, devices))
    logger.info("Wrote %s with %d active devices", sys.argv[1], len(devices))
    return 0


if __name__ == "__main__":
    sys.exit(main())
