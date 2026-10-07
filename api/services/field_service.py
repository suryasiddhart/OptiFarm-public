"""
Field service — raw SQL queries against appschema.fielddetails.
"""

from sqlalchemy import text
import json
from sqlalchemy.orm import Session


def create_field(db: Session, userid: int, fieldlength: float, fieldbreadth: float,
                 croptype: str, cropsubtype: str, cropinterval: float,
                 fieldlat: float, fieldlong: float,
                 soildata: dict | None, labels: dict | None,
                 imagedata: str | None) -> dict:
    sql = """
        INSERT INTO appschema.fielddetails
            (userid, fieldlength, fieldbreadth, croptype, cropsubtype, cropinterval,
             fieldlat, fieldlong, soildata, labels, imagedata)
        VALUES
            (:userid, :fieldlength, :fieldbreadth, :croptype, :cropsubtype, :cropinterval,
             :fieldlat, :fieldlong, :soildata, :labels, :imagedata)
        RETURNING *
    """
    result = db.execute(text(sql), {
        "userid": userid,
        "fieldlength": fieldlength,
        "fieldbreadth": fieldbreadth,
        "croptype": croptype,
        "cropsubtype": cropsubtype,
        "cropinterval": cropinterval,
        "fieldlat": fieldlat,
        "fieldlong": fieldlong,
        "soildata": json.dumps(soildata) if soildata is not None else None,
        "labels": json.dumps(labels) if labels is not None else None,
        "imagedata": imagedata,
    })
    db.commit()
    row = result.fetchone()
    return dict(row._mapping)


def get_fields_by_user(db: Session, userid: int) -> list[dict]:
    sql = """
        SELECT * FROM appschema.fielddetails
        WHERE userid = :userid
        ORDER BY fieldid
    """
    result = db.execute(text(sql), {"userid": userid})
    return [dict(row._mapping) for row in result.fetchall()]


def get_field_by_id(db: Session, fieldid: int, userid: int) -> dict | None:
    """Return the field only if it belongs to `userid` (None otherwise)."""
    sql = """
        SELECT * FROM appschema.fielddetails
        WHERE fieldid = :fieldid AND userid = :userid
    """
    result = db.execute(text(sql), {"fieldid": fieldid, "userid": userid})
    row = result.fetchone()
    return dict(row._mapping) if row else None


def update_field_inference(db: Session, fieldid: int, inference: dict) -> dict | None:
    sql = """
        UPDATE appschema.fielddetails
        SET inference = :inference
        WHERE fieldid = :fieldid
        RETURNING *
    """
    result = db.execute(text(sql), {
        "fieldid": fieldid,
        "inference": json.dumps(inference) if inference is not None else None,
    })
    db.commit()
    row = result.fetchone()
    return dict(row._mapping) if row else None
