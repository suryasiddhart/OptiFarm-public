"""
Alembic environment for FarmApp.

- DATABASE_URL comes from config.settings (same loading as the API:
  K8s secretKeyRef in-cluster, .env for local development).
- Migrations are hand-written raw SQL (the app uses sqlalchemy.text()),
  so there is no target_metadata / autogenerate.
- The alembic_version table lives in the application schema.
- A Postgres advisory lock serialises concurrent runs (one migrate
  initContainer per backend replica).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool, text
from sqlalchemy.schema import CreateSchema

from config.settings import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

APP_SCHEMA = settings.database_schema
# Arbitrary constant identifying the FarmApp migration lock
MIGRATION_LOCK_ID = 727274


def run_migrations_offline() -> None:
    """Emit SQL to stdout instead of executing it (alembic upgrade --sql)."""
    context.configure(
        url=settings.database_url,
        target_metadata=None,
        version_table_schema=APP_SCHEMA,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(settings.database_url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        connection.execute(text("SELECT pg_advisory_lock(:id)"), {"id": MIGRATION_LOCK_ID})
        try:
            # The version table is created inside the app schema, so the
            # schema must exist before Alembic touches it.
            connection.execute(CreateSchema(APP_SCHEMA, if_not_exists=True))
            connection.commit()

            context.configure(
                connection=connection,
                target_metadata=None,
                version_table_schema=APP_SCHEMA,
            )
            with context.begin_transaction():
                context.run_migrations()
        finally:
            connection.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": MIGRATION_LOCK_ID})
            connection.commit()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
