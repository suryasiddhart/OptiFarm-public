"""
Authentication routes — register and login.
"""

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt
from sqlalchemy.orm import Session

from config.database import get_db
from config.settings import settings
from models.schemas import UserCreate, UserLogin, TokenResponse, UserResponse, LogoutResponse
from services.user_service import create_user, get_user_by_mobileno
from middleware.auth import create_access_token, get_current_user, security
from services.login_attempt_service import (
    clear_failed_logins,
    get_locked_until,
    record_failed_login,
)
from services.token_service import blacklist_token
from utils.password import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_mobileno(db, payload.mobileno)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mobile number already registered",
        )

    hashed = hash_password(payload.password) if payload.password else None
    user = create_user(
        db,
        firstname=payload.firstname,
        lastname=payload.lastname,
        mobileno=payload.mobileno,
        emailid=payload.emailid,
        password=hashed,
    )
    token = create_access_token(data={"sub": str(user["userid"])})
    #token = create_access_token(data={"sub": user["userid"]})
    return UserResponse(**user)


def _too_many_attempts(locked_until: datetime) -> HTTPException:
    retry_after = max(1, math.ceil((locked_until - datetime.now(timezone.utc)).total_seconds()))
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many failed login attempts. Try again later.",
        headers={"Retry-After": str(retry_after)},
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    # Locked numbers are refused without checking the password
    locked_until = get_locked_until(db, payload.mobileno)
    if locked_until:
        raise _too_many_attempts(locked_until)

    user = get_user_by_mobileno(db, payload.mobileno)
    # verify_password() runs bcrypt even for unknown users (constant timing)
    if not verify_password(payload.password, user.get("password") if user else None) or not user:
        locked_until = record_failed_login(
            db, payload.mobileno, settings.login_max_attempts, settings.login_lockout_minutes
        )
        if locked_until:
            raise _too_many_attempts(locked_until)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mobile number or password",
        )

    clear_failed_logins(db, payload.mobileno)

    #token = create_access_token(data={"sub": user["userid"]})
    token = create_access_token(data={"sub": str(user["userid"])})
    return TokenResponse(access_token=token, user=UserResponse(**user))


@router.post("/logout", response_model=LogoutResponse)
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logout by blacklisting the current JWT token."""
    token = credentials.credentials
    # breakpoint()  # Debugging line to inspect the token and user info
    # Decode the token to get its expiry time
    payload = jwt.decode(
        token, settings.secret_key, algorithms=[settings.algorithm]
    )
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

    # Blacklist the token so it can't be used again
    blacklist_token(db, token, current_user["userid"], expires_at)

    return LogoutResponse(
        message="Successfully logged out. Token has been revoked.",
        userid=current_user["userid"],
    )
