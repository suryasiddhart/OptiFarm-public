"""
Moisture service — raw SQL queries against appschema.moisturedata.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session
import datetime
from datetime import timezone


def create_moisture_reading(db: Session, moisture: float, deviceid: str,
                            userinfo: int, fieldid: int | None, rtctime: str | None) -> dict:
    sql = """
        INSERT INTO appschema.moisturedata (moisture, deviceid, userinfo, fieldid, rtctime)
        VALUES (:moisture, :deviceid, :userinfo, :fieldid, :rtctime)
        RETURNING moisture, rtctime, deviceid, userinfo, fieldid
    """
    result = db.execute(text(sql), {
        "moisture": moisture,
        "deviceid": deviceid,
        "userinfo": userinfo,
        "fieldid": fieldid,
        "rtctime": rtctime
    })
    db.commit()
    row = result.fetchone()
    return dict(row._mapping)


def get_moisture_by_field(db: Session, fieldid: int, userid: int, limit: int = 100) -> list[dict]:
    """Readings for a field, restricted to rows owned by `userid`."""
    sql = """
        SELECT moisture, rtctime, deviceid, userinfo, fieldid
        FROM appschema.moisturedata
        WHERE fieldid = :fieldid AND userinfo = :userid
        ORDER BY rtctime DESC
        LIMIT :limit
    """
    result = db.execute(text(sql), {"fieldid": fieldid, "userid": userid, "limit": limit})
    return [dict(row._mapping) for row in result.fetchall()]


def get_moisture_by_user(db: Session, userinfo: int, limit: int = 100) -> list[dict]:
    sql = """
        SELECT moisture, rtctime, deviceid, userinfo, fieldid
        FROM appschema.moisturedata
        WHERE userinfo = :userinfo
        ORDER BY rtctime DESC
        LIMIT :limit
    """
    result = db.execute(text(sql), {"userinfo": userinfo, "limit": limit})
    return [dict(row._mapping) for row in result.fetchall()]
