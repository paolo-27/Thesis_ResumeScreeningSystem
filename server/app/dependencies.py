"""
FastAPI dependency functions for authentication and authorization.

Two-stage guard:
  1. get_current_user  – extracts and validates the JWT token.
  2. get_current_active_user – additionally checks is_active == 1.
  3. require_admin      – additionally checks role == 'Admin'.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from . import models
from .auth import decode_token

# tokenUrl points to our login endpoint (used by Swagger UI)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Stage 1: Validate JWT and return the corresponding User row."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    employee_number: str = payload.get("sub")
    if employee_number is None:
        raise credentials_exception

    user = db.query(models.User).filter(
        models.User.employee_number == employee_number
    ).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Stage 2: Block deactivated accounts immediately (is_active == 0).
    This enforces the offboarding process – once is_active is set to 0,
    the user cannot authenticate even with a valid token.
    """
    if current_user.is_active != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your administrator.",
        )

    return current_user


def require_admin(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """Stage 3: Restrict access to Admin-only routes."""
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user
