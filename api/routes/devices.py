"""
Device routes — register field devices and manage their MQTT passkeys.

The passkey is returned only by create and rotate-passkey; the database
keeps just its hash.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from config.database import get_db
from middleware.auth import get_current_user
from models.schemas import DeviceCreate, DeviceCredentials, DeviceResponse, DeviceUpdate
from services import device_service
from services.field_service import get_field_by_id
from services.mqtt_admin import BrokerError

router = APIRouter(prefix="/devices", tags=["Devices"])

TOPIC_TEMPLATE = "optifarm/v1/devices/{deviceid}/telemetry"


def _broker_unavailable(exc: BrokerError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                         detail=f"MQTT broker did not apply the change: {exc}")


def _credentials(device: dict, passkey: str) -> DeviceCredentials:
    return DeviceCredentials(**device, passkey=passkey,
                             mqtt_topic=TOPIC_TEMPLATE.format(deviceid=device["deviceid"]))


@router.post("/", response_model=DeviceCredentials, status_code=status.HTTP_201_CREATED)
def add_device(payload: DeviceCreate, db: Session = Depends(get_db),
               current_user: dict = Depends(get_current_user)):
    if not get_field_by_id(db, payload.fieldid, current_user["userid"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    try:
        device, passkey = device_service.create_device(
            db, userid=current_user["userid"], deviceid=payload.deviceid,
            devicename=payload.devicename, fieldid=payload.fieldid)
    except device_service.DeviceExistsError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device ID already registered")
    except BrokerError as exc:
        raise _broker_unavailable(exc)
    return _credentials(device, passkey)


@router.get("/", response_model=list[DeviceResponse])
def list_devices(fieldid: int | None = Query(None, description="Only this field's devices"),
                 include_disabled: bool = Query(False, description="Also list deleted (disabled) devices"),
                 db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    devices = device_service.get_devices_by_user(db, current_user["userid"], fieldid=fieldid,
                                                 include_disabled=include_disabled)
    return [DeviceResponse(**d) for d in devices]


@router.get("/{deviceid}", response_model=DeviceResponse)
def get_device(deviceid: str, db: Session = Depends(get_db),
               current_user: dict = Depends(get_current_user)):
    device = device_service.get_device(db, deviceid, current_user["userid"])
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceResponse(**device)


@router.post("/{deviceid}/rotate-passkey", response_model=DeviceCredentials)
def rotate_device_passkey(deviceid: str, db: Session = Depends(get_db),
                          current_user: dict = Depends(get_current_user)):
    try:
        result = device_service.rotate_passkey(db, deviceid, current_user["userid"])
    except BrokerError as exc:
        raise _broker_unavailable(exc)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active device not found")
    device, passkey = result
    return _credentials(device, passkey)


@router.delete("/{deviceid}", response_model=DeviceResponse)
def disable_device(deviceid: str, db: Session = Depends(get_db),
                   current_user: dict = Depends(get_current_user)):
    try:
        device = device_service.disable_device(db, deviceid, current_user["userid"])
    except BrokerError as exc:
        raise _broker_unavailable(exc)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return DeviceResponse(**device)
