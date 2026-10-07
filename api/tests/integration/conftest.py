"""Integration test fixtures for FarmApp Backend.

These fixtures set up a test database connection for integration tests.
Tests marked with @pytest.mark.integration use these fixtures.

The DATABASE_URL environment variable must point to a running PostgreSQL
instance (TimescaleDB). In CI, this is provided by the pipeline's
service container.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def db_engine():
    """Create a SQLAlchemy engine connected to the test database."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://testuser:testpass@localhost:5432/farmapp_test",
    )
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for each test."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
