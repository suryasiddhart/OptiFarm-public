"""
Moisture service — raw SQL queries against appschema.moisturedata.
"""

import json

from sqlalchemy import text
from sqlalchemy.orm import Session

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
