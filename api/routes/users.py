"""
User routes — profile and account management.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from models.schemas import UserResponse
from middleware.auth import get_current_user
from services.user_service import activate_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: dict = Depends(get_current_user)):
    return UserResponse(**current_user)


@router.post("/activate", response_model=UserResponse)
def activate_account(current_user: dict = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    user = activate_user(db, current_user["userid"])
    return UserResponse(**user)
