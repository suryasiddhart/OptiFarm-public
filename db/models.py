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
    Text,
    ForeignKey,
    Index,
    Sequence,
    JSON,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP

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


class MoistureData(Base):
    """appschema.moisturedata — moisture readings from devices."""

    __tablename__ = "moisturedata"
    __table_args__ = {"schema": "appschema"}

    # This table has no single-column PK in the DDL.
    # We use a synthetic auto-increment id for ORM convenience,
    # but the real-world key is (rtctime, deviceid, userinfo) or similar.
    # Alembic will still generate the DDL faithfully.
    id = Column(Integer, primary_key=True, autoincrement=True)
    moisture = Column(Float, nullable=True)
    rtctime = Column(TIMESTAMP(timezone=True), nullable=False)
    deviceid = Column(String, nullable=False)
    userinfo = Column(
        Integer,
        ForeignKey("appschema.userdetails.userid"),
        nullable=False,
    )
    fieldid = Column(
        Integer,
        ForeignKey("appschema.fielddetails.fieldid"),
        nullable=True,
    )

    def __repr__(self):
        return f"<MoistureData(rtctime={self.rtctime}, deviceid={self.deviceid})>"


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
