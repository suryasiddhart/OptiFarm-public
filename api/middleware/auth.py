"""
JWT authentication middleware / dependency.

Uses python-jose for token creation and verification.
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config.settings import settings
from config.database import get_db
from services.user_service import get_user_by_id
from services.token_service import is_token_blacklisted

security = HTTPBearer()


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    """Decode JWT and return the authenticated user dict."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # breakpoint() 
    # Check if token is blacklisted (user has logged out)
    if is_token_blacklisted(db, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        userid: int = int(payload.get("sub"))
        if userid is None:
            raise credentials_exception
    except JWTError as exc:
        import logging
        logging.error(f"JWT decode failed: {exc}")
        raise credentials_exception

    user = get_user_by_id(db, userid)
    if user is None:
        raise credentials_exception
    return user
