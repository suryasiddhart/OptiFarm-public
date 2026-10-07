"""
Field routes — CRUD for farm fields.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from config.database import get_db
from models.schemas import FieldCreate, FieldResponse
from middleware.auth import get_current_user
from services.field_service import create_field, get_fields_by_user, get_field_by_id

router = APIRouter(prefix="/fields", tags=["Fields"])


@router.post("/", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
def add_field(payload: FieldCreate, db: Session = Depends(get_db),
              current_user: dict = Depends(get_current_user)):
    # The owner always comes from the JWT, never from the request body
    field = create_field(
        db,
        userid=current_user["userid"],
        fieldlength=payload.fieldlength,
        fieldbreadth=payload.fieldbreadth,
        croptype=payload.croptype,
        cropsubtype=payload.cropsubtype,
        cropinterval=payload.cropinterval,
        fieldlat=payload.fieldlat,
        fieldlong=payload.fieldlong,
        soildata=payload.soildata,
        labels=payload.labels,
        imagedata=payload.imagedata,
    )
    return FieldResponse(**field)


@router.get("/", response_model=list[FieldResponse])
def list_fields(db: Session = Depends(get_db),
                current_user: dict = Depends(get_current_user)):
    fields = get_fields_by_user(db, current_user["userid"])
    return [FieldResponse(**f) for f in fields]


@router.get("/{field_id}", response_model=FieldResponse)
def get_field(field_id: int, db: Session = Depends(get_db),
              current_user: dict = Depends(get_current_user)):
    # 404 (not 403) for other users' fields so IDs can't be probed
    field = get_field_by_id(db, field_id, current_user["userid"])
    if not field:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    return FieldResponse(**field)
