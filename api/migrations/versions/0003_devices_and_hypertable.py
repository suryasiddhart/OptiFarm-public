"""Device registry and moisturedata hypertable

- appschema.devices: every field device belongs to a user and holds the
  PBKDF2-SHA512 hash of its MQTT passkey (Mosquitto dynamic-security
  "$7$" format, split into hash/salt/iterations). The MQTT broker config
  is regenerated from this table (ingest/dynsec_sync.py).
- appschema.moisturedata: unique (deviceid, rtctime) so redelivered
  readings are dropped with ON CONFLICT DO NOTHING, then converted to a
  TimescaleDB hypertable with compression.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-12
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS appschema.devices (
            deviceid varchar(64) NOT NULL,
            userinfo int4 NOT NULL,
            fieldid int4 NULL,
            passkey_hash varchar NOT NULL,
            passkey_salt varchar NOT NULL,
            passkey_iterations int4 NOT NULL,
            status varchar(16) DEFAULT 'active' NOT NULL,
            last_seen timestamptz NULL,
            created_at timestamptz DEFAULT now() NOT NULL,
            CONSTRAINT devices_pkey PRIMARY KEY (deviceid),
            CONSTRAINT devices_status_check CHECK (status IN ('active', 'disabled')),
            CONSTRAINT devices_userinfo_fkey FOREIGN KEY (userinfo)
                REFERENCES appschema.userdetails(userid) ON DELETE CASCADE,
            CONSTRAINT devices_fieldid_fkey FOREIGN KEY (fieldid)
                REFERENCES appschema.fielddetails(fieldid) ON DELETE SET NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_devices_userinfo ON appschema.devices (userinfo)")

    # Existing duplicate readings would block the unique index; keep one per key.
    op.execute(
        """
        DELETE FROM appschema.moisturedata a
        USING appschema.moisturedata b
        WHERE a.ctid < b.ctid
          AND a.deviceid = b.deviceid
          AND a.rtctime = b.rtctime
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS moisturedata_device_time_uq
            ON appschema.moisturedata (deviceid, rtctime)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_moisturedata_field_time
            ON appschema.moisturedata (fieldid, rtctime DESC)
        """
    )

    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute(
        """
        SELECT create_hypertable('appschema.moisturedata', 'rtctime',
                                 migrate_data => true, if_not_exists => true)
        """
    )
    op.execute(
        """
        ALTER TABLE appschema.moisturedata SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'deviceid'
        )
        """
    )
    op.execute(
        """
        SELECT add_compression_policy('appschema.moisturedata', INTERVAL '7 days',
                                      if_not_exists => true)
        """
    )


def downgrade() -> None:
    # A hypertable can't be turned back into a plain table in place: copy the
    # rows into a fresh table with the 0001 definition and swap it in.
    op.execute("SELECT remove_compression_policy('appschema.moisturedata', if_exists => true)")
    op.execute(
        """
        CREATE TABLE appschema.moisturedata_plain (
            moisture float4 NULL,
            rtctime timestamptz NOT NULL,
            deviceid varchar NOT NULL,
            userinfo int4 NOT NULL,
            fieldid int4 NULL,
            CONSTRAINT fieldinfo FOREIGN KEY (fieldid)
                REFERENCES appschema.fielddetails(fieldid),
            CONSTRAINT userinfo FOREIGN KEY (userinfo)
                REFERENCES appschema.userdetails(userid)
        )
        """
    )
    op.execute(
        """
        INSERT INTO appschema.moisturedata_plain (moisture, rtctime, deviceid, userinfo, fieldid)
        SELECT moisture, rtctime, deviceid, userinfo, fieldid FROM appschema.moisturedata
        """
    )
    op.execute("DROP TABLE appschema.moisturedata")
    op.execute("ALTER TABLE appschema.moisturedata_plain RENAME TO moisturedata")
    op.execute("DROP TABLE IF EXISTS appschema.devices")
