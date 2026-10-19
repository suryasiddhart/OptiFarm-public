"""
SQLAlchemy ORM models for FarmApp.

These models reflect the schema defined in db_DDL.txt and are used
by Alembic for auto-generating migrations.
"""

from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Boolean,
    CheckConstraint,
    Text,
    ForeignKey,
    Index,
    Sequence,
    JSON,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

from db.base import Base


class UserDetail(Base):
    """appschema.userdetails — registered users."""

    __tablename__ = "userdetails"
    __table_args__ = {"schema": "appschema"}

    userid = Column(
        Integer,
        Sequence("useridseq", schema="appschema"),
        primary_key=True,
        server_default=text("nextval('appschema.useridseq'::regclass)"),
    )
    firstname = Column(String, nullable=False)
    lastname = Column(String, nullable=False)
    mobileno = Column(String, nullable=False, unique=True)
    emailid = Column(String, nullable=True)
    password = Column(String, nullable=True)
    activationstatus = Column(Boolean, nullable=False)

    def __repr__(self):
        return f"<UserDetail(userid={self.userid}, mobileno={self.mobileno})>"


class FieldDetail(Base):
    """appschema.fielddetails — field information per user."""

    __tablename__ = "fielddetails"
    __table_args__ = {"schema": "appschema"}

    fieldid = Column(
        Integer,
        Sequence("fieldidseq", schema="appschema"),
        primary_key=True,
        server_default=text("nextval('appschema.fieldidseq'::regclass)"),
    )
    userid = Column(
        Integer,
        ForeignKey("appschema.userdetails.userid", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
    )
    fieldlength = Column(Float, nullable=False)
    fieldbreadth = Column(Float, nullable=False)
    croptype = Column(String, nullable=False)
    cropsubtype = Column(String, nullable=False)
    cropinterval = Column(Float, nullable=False)
    fieldlat = Column(Float, nullable=False)
    fieldlong = Column(Float, nullable=False)
    soildata = Column(JSON, nullable=True)
    labels = Column(JSON, nullable=True)
    imagedata = Column(Text, nullable=True)
    inference = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<FieldDetail(fieldid={self.fieldid}, croptype={self.croptype})>"


class Device(Base):
    """appschema.devices — field devices, each owned by a user.

    passkey_* hold the PBKDF2-SHA512 hash of the device's MQTT passkey; the
    plaintext passkey is only ever returned once by the API.
    """

    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'disabled')", name="devices_status_check"),
        Index("idx_devices_userinfo", "userinfo"),
        {"schema": "appschema"},
    )

    deviceid = Column(String(64), primary_key=True)
    # Display name shown in the UI; deviceid is the generated MQTT username
    devicename = Column(String(100), nullable=False)
    userinfo = Column(
        Integer,
        ForeignKey("appschema.userdetails.userid", ondelete="CASCADE"),
        nullable=False,
    )
    fieldid = Column(
        Integer,
        ForeignKey("appschema.fielddetails.fieldid", ondelete="SET NULL"),
        nullable=True,
    )
    passkey_hash = Column(String, nullable=False)
    passkey_salt = Column(String, nullable=False)
    passkey_iterations = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False, server_default=text("'active'"))
    last_seen = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self):
        return f"<Device(deviceid={self.deviceid}, userinfo={self.userinfo})>"


class TokenBlacklist(Base):
    """appschema.token_blacklist — blacklisted JWT tokens for logout support."""

    __tablename__ = "token_blacklist"
    __table_args__ = (
        Index("idx_token_blacklist_expires", "expires_at"),
        {"schema": "appschema"},
    )

    token_hash = Column(String(64), primary_key=True)
    userid = Column(
        Integer,
        ForeignKey("appschema.userdetails.userid", ondelete="CASCADE"),
        nullable=False,
    )
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self):
        return f"<TokenBlacklist(token_hash={self.token_hash[:8]}...)>"
