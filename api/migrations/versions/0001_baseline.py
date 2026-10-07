"""Baseline schema: users, fields, moisture data, token blacklist

Converted from the original db/db_DDL.txt. Every statement uses
IF NOT EXISTS so this migration also succeeds on databases where the
schema was created by hand; it then only records revision 0001.

Revision ID: 0001
Revises:
Create Date: 2026-10-05
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS appschema")

    op.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS appschema.useridseq
            INCREMENT BY 1
            MINVALUE 100000
            MAXVALUE 9223372036854775807
            START 100000
            CACHE 1
            NO CYCLE
        """
    )
    op.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS appschema.fieldidseq
            INCREMENT BY 1
            MINVALUE 200000
            MAXVALUE 9223372036854775807
            START 200000
            CACHE 1
            NO CYCLE
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS appschema.userdetails (
            firstname varchar NOT NULL,
            lastname varchar NOT NULL,
            mobileno varchar NOT NULL,
            emailid varchar NULL,
            "password" varchar NULL,
            activationstatus bool NOT NULL,
            userid int4 DEFAULT nextval('appschema.useridseq'::regclass) NOT NULL,
            CONSTRAINT userdetails_pkey PRIMARY KEY (userid),
            CONSTRAINT userdetails_unique UNIQUE (mobileno)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS appschema.fielddetails (
            userid int4 NULL,
            fieldlength float4 NOT NULL,
            fieldbreadth float4 NOT NULL,
            croptype varchar NOT NULL,
            cropsubtype varchar NOT NULL,
            cropinterval float4 NOT NULL,
            fieldlat float4 NOT NULL,
            fieldlong float4 NOT NULL,
            soildata json NULL,
            labels json NULL,
            imagedata text NULL,
            fieldid int4 DEFAULT nextval('appschema.fieldidseq'::regclass) NOT NULL,
            inference json NULL,
            CONSTRAINT fielddetails_pk PRIMARY KEY (fieldid),
            CONSTRAINT userinfo FOREIGN KEY (userid)
                REFERENCES appschema.userdetails(userid) ON DELETE CASCADE ON UPDATE CASCADE
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS appschema.moisturedata (
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
        CREATE TABLE IF NOT EXISTS appschema.token_blacklist (
            token_hash varchar(64) NOT NULL,
            userid int4 NOT NULL,
            expires_at timestamptz NOT NULL,
            created_at timestamptz DEFAULT now() NOT NULL,
            CONSTRAINT token_blacklist_pkey PRIMARY KEY (token_hash),
            CONSTRAINT token_blacklist_userid_fkey FOREIGN KEY (userid)
                REFERENCES appschema.userdetails(userid) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_token_blacklist_expires
            ON appschema.token_blacklist USING btree (expires_at)
        """
    )


def downgrade() -> None:
    # Reverse dependency order; the schema itself is kept (it also holds
    # the alembic_version table).
    op.execute("DROP TABLE IF EXISTS appschema.token_blacklist")
    op.execute("DROP TABLE IF EXISTS appschema.moisturedata")
    op.execute("DROP TABLE IF EXISTS appschema.fielddetails")
    op.execute("DROP TABLE IF EXISTS appschema.userdetails")
    op.execute("DROP SEQUENCE IF EXISTS appschema.fieldidseq")
    op.execute("DROP SEQUENCE IF EXISTS appschema.useridseq")
