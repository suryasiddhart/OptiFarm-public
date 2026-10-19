"""
Pydantic models (schemas) for request/response validation.

These are NOT SQLAlchemy ORM models — we use raw SQL (text mode).
These schemas define the shape of data entering and leaving the API.
"""

import math
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from utils.grid import CELL_KEY_PATTERN


# ─── User ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    firstname: str
    lastname: str
    mobileno: str
    emailid: str | None = None
    password: str | None = None


class UserLogin(BaseModel):
    mobileno: str
    password: str


class UserResponse(BaseModel):
    userid: int
    firstname: str
    lastname: str
    mobileno: str
    emailid: str | None
    activationstatus: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LogoutResponse(BaseModel):
    message: str
    userid: int


# ─── Field ───────────────────────────────────────────────────────────────────

class FieldCreate(BaseModel):
    # No userid: the owner is the authenticated caller (an extra "userid" in
    # the request body is ignored).
    fieldlength: float
    fieldbreadth: float
    croptype: str
    cropsubtype: str
    cropinterval: float
    fieldlat: float
    fieldlong: float
    soildata: dict | None = None
    labels: dict | None = None
    imagedata: str | None = None


class FieldResponse(BaseModel):
    fieldid: int
    userid: int
    fieldlength: float
    fieldbreadth: float
    croptype: str
    cropsubtype: str
    cropinterval: float
    fieldlat: float
    fieldlong: float
    soildata: dict | None
    labels: dict | None
    imagedata: str | None
    inference: dict | None

    model_config = {"from_attributes": True}


# ─── Moisture ────────────────────────────────────────────────────────────────

# Grid cell key m<row>_<col> (1-based), see utils/grid.py
CellKey = Annotated[str, StringConstraints(pattern=CELL_KEY_PATTERN)]


class MoistureCreate(BaseModel):
    # No userinfo: readings are recorded for the authenticated caller.
    # One value per grid cell of the field; any subset of cells is accepted.
    moisture: dict[CellKey, float] = Field(min_length=1,
                                           examples=[{"m1_1": 31.4, "m1_2": 32.34}])
    deviceid: str
    fieldid: int
    rtctime: str | None = None

    @field_validator("moisture")
    @classmethod
    def finite(cls, cells: dict[str, float]) -> dict[str, float]:
        bad = [k for k, v in cells.items() if not math.isfinite(v)]
        if bad:
            raise ValueError(f"moisture must be finite numbers: {', '.join(bad)}")
        return cells


class MoistureResponse(BaseModel):
    # None for readings stored before the grid format (moisture_legacy)
    moisture: dict[str, float] | None
    rtctime: datetime
    deviceid: str
    userinfo: int
    fieldid: int | None

    model_config = {"from_attributes": True}


# ─── Device ──────────────────────────────────────────────────────────────────

# Used as the MQTT username and inside the topic, so no "/", "+", "#".
DEVICE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$"


# Display name: trimmed, 1-100 characters
DeviceName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class DeviceCreate(BaseModel):
    # No userinfo: devices are owned by the authenticated caller.
    devicename: DeviceName = Field(examples=["North corner sensor"])
    deviceid: str | None = Field(default=None, pattern=DEVICE_ID_PATTERN,
                                 description="Omit to have one generated")
    # Required: the device reports the moisture grid of this field
    fieldid: int


class DeviceUpdate(BaseModel):
    fieldid: int


class DeviceResponse(BaseModel):
    deviceid: str
    devicename: str
    userinfo: int
    fieldid: int | None
    status: str
    last_seen: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceCredentials(DeviceResponse):
    """Returned once, on create and on rotate: the passkey is not stored."""
    passkey: str
    mqtt_topic: str
