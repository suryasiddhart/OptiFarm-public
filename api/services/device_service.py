"""
Device service — raw SQL queries against appschema.devices.

Every write that changes MQTT credentials keeps the database and the broker
in step: the row is written in an open transaction, the broker is updated,
and the transaction is committed only if the broker accepted the change.
"""

import secrets

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services import mqtt_admin
from utils.passkey import generate_passkey, hash_passkey

class DeviceExistsError(Exception):
    pass


def get_devices_by_user(db: Session, userid: int, fieldid: int | None = None,
                        include_disabled: bool = False) -> list[dict]:
    """The user's devices, optionally only one field's; deleted (disabled) ones skipped by default."""
    sql = """
        SELECT deviceid, devicename, userinfo, fieldid, status, last_seen, created_at FROM appschema.devices
        WHERE userinfo = :userid
          AND (CAST(:fieldid AS int4) IS NULL OR fieldid = :fieldid)
          AND (:include_disabled OR status = 'active')
        ORDER BY created_at
    """
    result = db.execute(text(sql), {"userid": userid, "fieldid": fieldid,
                                    "include_disabled": include_disabled})
    return [dict(row._mapping) for row in result.fetchall()]


def get_device(db: Session, deviceid: str, userid: int) -> dict | None:
    """Return the device only if it belongs to `userid` (None otherwise)."""
    sql = """
        SELECT deviceid, devicename, userinfo, fieldid, status, last_seen, created_at FROM appschema.devices
        WHERE deviceid = :deviceid AND userinfo = :userid
    """
    row = db.execute(text(sql), {"deviceid": deviceid, "userid": userid}).fetchone()
    return dict(row._mapping) if row else None


def create_device(db: Session, userid: int, deviceid: str | None, devicename: str,
                  fieldid: int | None) -> tuple[dict, str]:
    """Create a device and its MQTT client. Returns (device, plaintext passkey)."""
    deviceid = deviceid or f"dev-{secrets.token_hex(6)}"
    passkey = generate_passkey()
    stored = hash_passkey(passkey)
    sql = """
        INSERT INTO appschema.devices
            (deviceid, devicename, userinfo, fieldid, passkey_hash, passkey_salt, passkey_iterations)
        VALUES
            (:deviceid, :devicename, :userinfo, :fieldid, :hash, :salt, :iterations)
        RETURNING deviceid, devicename, userinfo, fieldid, status, last_seen, created_at
    """
    try:
        row = db.execute(text(sql), {
            "deviceid": deviceid,
            "devicename": devicename,
            "userinfo": userid,
            "fieldid": fieldid,
            "hash": stored.hash,
            "salt": stored.salt,
            "iterations": stored.iterations,
        }).fetchone()
    except IntegrityError as exc:
        db.rollback()
        raise DeviceExistsError(deviceid) from exc

    try:
        mqtt_admin.create_device_client(deviceid, passkey)
    except mqtt_admin.BrokerError:
        db.rollback()
        raise

    try:
        db.commit()
    except Exception:
        db.rollback()
        mqtt_admin.delete_device_client(deviceid)
        raise
    return dict(row._mapping), passkey


def rotate_passkey(db: Session, deviceid: str, userid: int) -> tuple[dict, str] | None:
    passkey = generate_passkey()
    stored = hash_passkey(passkey)
    sql = """
        UPDATE appschema.devices
        SET passkey_hash = :hash, passkey_salt = :salt, passkey_iterations = :iterations
        WHERE deviceid = :deviceid AND userinfo = :userid AND status = 'active'
        RETURNING deviceid, devicename, userinfo, fieldid, status, last_seen, created_at
    """
    row = db.execute(text(sql), {
        "deviceid": deviceid,
        "userid": userid,
        "hash": stored.hash,
        "salt": stored.salt,
        "iterations": stored.iterations,
    }).fetchone()
    if row is None:
        db.rollback()
        return None
    try:
        mqtt_admin.set_device_passkey(deviceid, passkey)
    except mqtt_admin.BrokerError:
        db.rollback()
        raise
    db.commit()
    return dict(row._mapping), passkey


def disable_device(db: Session, deviceid: str, userid: int) -> dict | None:
    sql = """
        UPDATE appschema.devices
        SET status = 'disabled'
        WHERE deviceid = :deviceid AND userinfo = :userid
        RETURNING deviceid, devicename, userinfo, fieldid, status, last_seen, created_at
    """
    row = db.execute(text(sql), {"deviceid": deviceid, "userid": userid}).fetchone()
    if row is None:
        db.rollback()
        return None
    try:
        mqtt_admin.disable_device_client(deviceid)
    except mqtt_admin.BrokerError:
        db.rollback()
        raise
    db.commit()
    return dict(row._mapping)
