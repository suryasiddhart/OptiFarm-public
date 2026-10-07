"""Login attempt tracking for per-account lockout

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-08
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keyed by mobile number (not userid) so unknown numbers are throttled
    # exactly like registered ones and the lockout can't be used to probe
    # which numbers exist.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS appschema.login_attempts (
            mobileno varchar NOT NULL,
            failed_count int4 DEFAULT 0 NOT NULL,
            last_failed_at timestamptz DEFAULT now() NOT NULL,
            locked_until timestamptz NULL,
            CONSTRAINT login_attempts_pkey PRIMARY KEY (mobileno)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS appschema.login_attempts")
