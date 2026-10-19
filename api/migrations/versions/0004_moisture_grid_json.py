"""Moisture readings as a per-cell grid (jsonb)

moisturedata.moisture becomes jsonb holding one value per grid cell of the
reading's field, keyed m<row>_<col> (1-based):

    {"m1_1": 31.4, "m1_2": 32.34, "m2_1": 12.33, "m2_2": 56.78}

The grid is rows = floor(fieldlength / cropinterval), cols =
floor(fieldbreadth / cropinterval) (see api/utils/grid.py). Earlier readings
were a single number with no grid position; they are kept unchanged in
moisture_legacy instead of being guessed onto a cell.

Rename/add column work on a hypertable with compression enabled, so no
chunks need to be decompressed.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE appschema.moisturedata RENAME COLUMN moisture TO moisture_legacy")
    op.execute("ALTER TABLE appschema.moisturedata ADD COLUMN moisture jsonb NULL")


def downgrade() -> None:
    # Grid readings can't be turned back into one number: they are dropped.
    op.execute("ALTER TABLE appschema.moisturedata DROP COLUMN moisture")
    op.execute("ALTER TABLE appschema.moisturedata RENAME COLUMN moisture_legacy TO moisture")
