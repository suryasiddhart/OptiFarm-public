"""
SQLAlchemy Declarative Base with shared metadata.

All models inherit from this Base and share the same metadata,
which is used by Alembic for autogenerate support.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
