"""
Pydantic models (schemas) for request/response validation.

These are NOT SQLAlchemy ORM models — we use raw SQL (text mode).
These schemas define the shape of data entering and leaving the API.
"""

from datetime import datetime
from pydantic import BaseModel, Field


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

class MoistureCreate(BaseModel):
    # No userinfo: readings are recorded for the authenticated caller.
    moisture: float
    deviceid: str
    fieldid: int | None = None
    rtctime: str | None = None


class MoistureResponse(BaseModel):
    moisture: float
    rtctime: datetime
    deviceid: str
    userinfo: int
    fieldid: int | None

    model_config = {"from_attributes": True}
