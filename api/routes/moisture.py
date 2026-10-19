"""
Moisture routes — sensor data ingestion and retrieval.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from config.database import get_db
from models.schemas import MoistureResponse
from middleware.auth import get_current_user
from services.field_service import get_field_by_id
from services.moisture_service import get_moisture_by_field, get_moisture_by_user
from utils.grid import cells_outside_grid, grid_size

router = APIRouter(prefix="/moisture", tags=["Moisture"])

@router.get("/field/{field_id}", response_model=list[MoistureResponse])
def list_moisture_by_field(field_id: int, limit: int = Query(100, ge=1, le=1000),
                           db: Session = Depends(get_db),
                           current_user: dict = Depends(get_current_user)):
    if not get_field_by_id(db, field_id, current_user["userid"]):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    readings = get_moisture_by_field(db, field_id, current_user["userid"], limit)
    return [MoistureResponse(**r) for r in readings]


@router.get("/my", response_model=list[MoistureResponse])
def list_my_moisture(limit: int = Query(100, ge=1, le=1000),
                     db: Session = Depends(get_db),
                     current_user: dict = Depends(get_current_user)):
    readings = get_moisture_by_user(db, current_user["userid"], limit)
    return [MoistureResponse(**r) for r in readings]
