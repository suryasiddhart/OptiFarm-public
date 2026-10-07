"""
Login attempt service — per-account brute-force protection.

Failed logins are counted per mobile number in appschema.login_attempts.
After `max_attempts` failures within `lockout_minutes` the number is locked
for `lockout_minutes`; a successful login clears the record. State lives in
Postgres so it is shared by all API replicas and survives restarts.
"""

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_locked_until(db: Session, mobileno: str) -> datetime | None:
    """Return the lock expiry if the number is currently locked, else None."""
    sql = """
        SELECT locked_until FROM appschema.login_attempts
        WHERE mobileno = :mobileno AND locked_until > now()
    """
    row = db.execute(text(sql), {"mobileno": mobileno}).fetchone()
    return row.locked_until if row else None


def record_failed_login(db: Session, mobileno: str, max_attempts: int,
                        lockout_minutes: int) -> datetime | None:
    """Count a failed login; lock the number when the limit is reached.

    The count restarts when the previous failure is older than the lockout
    window or a previous lock has expired. Returns the new lock expiry if this
    failure triggered a lock, else None.
    """
    sql = """
        INSERT INTO appschema.login_attempts AS la (mobileno, failed_count, last_failed_at)
        VALUES (:mobileno, 1, now())
        ON CONFLICT (mobileno) DO UPDATE SET
            failed_count = CASE
                WHEN la.locked_until IS NOT NULL AND la.locked_until <= now() THEN 1
                WHEN la.last_failed_at < now() - make_interval(mins => :minutes) THEN 1
                ELSE la.failed_count + 1
            END,
            locked_until = CASE
                WHEN la.locked_until <= now() THEN NULL
                ELSE la.locked_until
            END,
            last_failed_at = now()
        RETURNING failed_count
    """
    failed_count = db.execute(
        text(sql), {"mobileno": mobileno, "minutes": lockout_minutes}
    ).scalar_one()

    locked_until = None
    if failed_count >= max_attempts:
        lock_sql = """
            UPDATE appschema.login_attempts
            SET locked_until = now() + make_interval(mins => :minutes)
            WHERE mobileno = :mobileno
            RETURNING locked_until
        """
        locked_until = db.execute(
            text(lock_sql), {"mobileno": mobileno, "minutes": lockout_minutes}
        ).scalar_one()
    db.commit()
    return locked_until


def clear_failed_logins(db: Session, mobileno: str) -> None:
    """Reset the counter after a successful login."""
    db.execute(
        text("DELETE FROM appschema.login_attempts WHERE mobileno = :mobileno"),
        {"mobileno": mobileno},
    )
    db.commit()
