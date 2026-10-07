"""
Token blacklist service — raw SQL queries against appschema.token_blacklist.

DDL for the blacklist table:
    CREATE TABLE appschema.token_blacklist (
        token_hash VARCHAR(64) PRIMARY KEY,
        userid INT NOT NULL REFERENCES appschema.userdetails(userid) ON DELETE CASCADE,
        expires_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    CREATE INDEX idx_token_blacklist_expires ON appschema.token_blacklist(expires_at);
"""

import hashlib

from sqlalchemy import text
from sqlalchemy.orm import Session


def _hash_token(token: str) -> str:
    """SHA-256 hash of the token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


def blacklist_token(db: Session, token: str, userid: int, expires_at) -> None:
    """Add a token to the blacklist."""
    token_hash = _hash_token(token)
    sql = """
        INSERT INTO appschema.token_blacklist (token_hash, userid, expires_at)
        VALUES (:token_hash, :userid, :expires_at)
        ON CONFLICT (token_hash) DO NOTHING
    """
    db.execute(text(sql), {
        "token_hash": token_hash,
        "userid": userid,
        "expires_at": expires_at,
    })
    db.commit()


def is_token_blacklisted(db: Session, token: str) -> bool:
    """Check if a token has been blacklisted."""
    token_hash = _hash_token(token)
    sql = """
        SELECT 1 FROM appschema.token_blacklist
        WHERE token_hash = :token_hash AND expires_at > NOW()
    """
    result = db.execute(text(sql), {"token_hash": token_hash})
    return result.fetchone() is not None


def clean_expired_tokens(db: Session) -> int:
    """Remove expired blacklist entries. Returns number of rows deleted."""
    sql = "DELETE FROM appschema.token_blacklist WHERE expires_at <= NOW()"
    result = db.execute(text(sql))
    db.commit()
    return result.rowcount
