"""Device display name

appschema.devices.devicename: a free-text name shown in the UI (e.g. "North
corner sensor"). deviceid stays the generated, MQTT-safe identifier used as
the broker username. Existing devices are named after their deviceid.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-18
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE appschema.devices ADD COLUMN devicename varchar(100) NULL")
    op.execute("UPDATE appschema.devices SET devicename = deviceid")
    op.execute("ALTER TABLE appschema.devices ALTER COLUMN devicename SET NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE appschema.devices DROP COLUMN devicename")
