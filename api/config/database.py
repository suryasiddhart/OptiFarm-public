"""
Database connection and session management using SQLAlchemy in text mode.

Uses raw SQL via `sqlalchemy.text()` rather than ORM models.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from config.settings import settings

engine = create_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def execute_raw(sql: str, params: dict | None = None, db: Session | None = None):
    """
    Execute a raw SQL statement using text mode.

    Args:
        sql: Raw SQL string (e.g. "SELECT * FROM appschema.userdetails WHERE userid = :uid")
        params: Dictionary of bind parameters
        db: Optional existing session; if None, creates a new one.

    Returns:
        sqlalchemy.engine.CursorResult
    """
    close = False
    if db is None:
        db = SessionLocal()
        close = True
    try:
        result = db.execute(text(sql), params or {})
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
    finally:
        if close:
            db.close()
