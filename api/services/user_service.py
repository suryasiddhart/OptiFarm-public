"""
User service — raw SQL queries against appschema.userdetails.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from config.database import execute_raw


def create_user(db: Session, firstname: str, lastname: str, mobileno: str,
                emailid: str | None, password: str | None) -> dict:
    sql = """
        INSERT INTO appschema.userdetails (firstname, lastname, mobileno, emailid, password, activationstatus)
        VALUES (:firstname, :lastname, :mobileno, :emailid, :password, true)
        RETURNING userid, firstname, lastname, mobileno, emailid, activationstatus
    """
    result = db.execute(text(sql), {
        "firstname": firstname,
        "lastname": lastname,
        "mobileno": mobileno,
        "emailid": emailid,
        "password": password,
    })
    db.commit()
    row = result.fetchone()
    return dict(row._mapping)


def get_user_by_mobileno(db: Session, mobileno: str) -> dict | None:
    sql = """
        SELECT userid, firstname, lastname, mobileno, emailid, password, activationstatus
        FROM appschema.userdetails
        WHERE mobileno = :mobileno
    """
    result = db.execute(text(sql), {"mobileno": mobileno})
    row = result.fetchone()
    return dict(row._mapping) if row else None


def get_user_by_id(db: Session, userid: int) -> dict | None:
    sql = """
        SELECT userid, firstname, lastname, mobileno, emailid, activationstatus
        FROM appschema.userdetails
        WHERE userid = :userid
    """
    result = db.execute(text(sql), {"userid": userid})
    row = result.fetchone()
    return dict(row._mapping) if row else None


def activate_user(db: Session, userid: int) -> dict | None:
    sql = """
        UPDATE appschema.userdetails
        SET activationstatus = true
        WHERE userid = :userid
        RETURNING userid, firstname, lastname, mobileno, emailid, activationstatus
    """
    result = db.execute(text(sql), {"userid": userid})
    db.commit()
    row = result.fetchone()
    return dict(row._mapping) if row else None
