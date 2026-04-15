"""
Auth router: login, current-user profile and user-management (Admin-only).
"""

import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from .. import models
from ..database import get_db
from ..auth import verify_password, get_password_hash, create_access_token
from ..dependencies import get_current_active_user, require_admin

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
    redirect_slashes=False,
)

# ──────────────────────────────────────────────
# Pydantic schemas (local to this router)
# ──────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    avatar_color: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class CreateUserPayload(BaseModel):
    employee_number: str
    password: str
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    role: str = "HR"          # 'Admin' | 'HR'


class DeactivateUserPayload(BaseModel):
    employee_number: str


class AdminResetPasswordPayload(BaseModel):
    new_password: str


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _user_to_dict(user: models.User) -> dict:
    """Serialise a User row into a safe dict (no password hash)."""
    return {
        "id": user.id,
        "employee_number": user.employee_number,
        "name": user.name,
        "email": user.email,
        "phone": user.phone,
        "company": user.company,
        "location": user.location,
        "avatar_color": user.avatar_color,
        "role": user.role,
        "is_active": user.is_active,
        "force_reset": user.force_reset,
        "created_at": user.created_at,
    }


# ──────────────────────────────────────────────
# Login
# ──────────────────────────────────────────────

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Authenticate with employee_number (sent as 'username') + password.
    Returns a JWT and the user's profile dict.
    """
    user = db.query(models.User).filter(
        models.User.employee_number == form_data.username
    ).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect employee number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Block immediately if the account is deactivated
    if user.is_active != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact your administrator.",
        )

    token = create_access_token(data={"sub": user.employee_number})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _user_to_dict(user),
    }


# ──────────────────────────────────────────────
# Current-user profile (any authenticated user)
# ──────────────────────────────────────────────

@router.get("/me")
def get_me(current_user: models.User = Depends(get_current_active_user)):
    """Return the currently logged-in user's profile."""
    return _user_to_dict(current_user)


@router.get("/me/stats")
def get_me_stats(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Return stats strictly owned by the current user, bypassing any Admin 'see all' logic."""
    jobs_posted = db.query(models.JobPosting).filter(models.JobPosting.created_by_id == current_user.id).count()
    resumes_screened = (
        db.query(models.Candidate)
        .join(models.JobPosting)
        .filter(models.JobPosting.created_by_id == current_user.id)
        .count()
    )
    return {"jobs_posted": jobs_posted, "resumes_screened": resumes_screened}


@router.patch("/me")
def update_profile(
    payload: UserProfileUpdate,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update the current user's profile fields."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return _user_to_dict(current_user)


@router.post("/me/change-password")
def change_password(
    payload: PasswordChange,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change the password for the currently logged-in user."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.password_hash = get_password_hash(payload.new_password)
    current_user.force_reset = 0  # Clear any forced-reset flag
    db.commit()
    return {"message": "Password changed successfully"}


# ──────────────────────────────────────────────
# User Management (Admin-only)
# ──────────────────────────────────────────────

@router.get("/users")
def list_users(
    _: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users. Requires Admin role."""
    users = db.query(models.User).all()
    return [_user_to_dict(u) for u in users]


@router.post("/users")
def create_user(
    payload: CreateUserPayload,
    _: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new HR or Admin user. Requires Admin role."""
    existing = db.query(models.User).filter(
        models.User.employee_number == payload.employee_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee number already registered")

    new_user = models.User(
        employee_number=payload.employee_number,
        password_hash=get_password_hash(payload.password),
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        location=payload.location,
        role=payload.role,
        is_active=1,
        force_reset=0,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return _user_to_dict(new_user)


@router.patch("/users/{employee_number}/deactivate")
def deactivate_user(
    employee_number: str,
    _: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Offboarding: Set is_active=0 for the specified user WITHOUT deleting them
    or their associated screening history. This preserves data integrity.

    SQL equivalent:
        UPDATE users SET is_active = 0 WHERE employee_number = :emp_num;
    """
    user = db.query(models.User).filter(
        models.User.employee_number == employee_number
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = 0
    db.commit()
    return {"message": f"User {employee_number} has been deactivated.", "user": _user_to_dict(user)}


@router.patch("/users/{employee_number}/reactivate")
def reactivate_user(
    employee_number: str,
    _: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Reactivate a previously deactivated user."""
    user = db.query(models.User).filter(
        models.User.employee_number == employee_number
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = 1
    db.commit()
    return {"message": f"User {employee_number} has been reactivated.", "user": _user_to_dict(user)}


@router.patch("/users/{employee_number}/reset-password")
def admin_reset_password(
    employee_number: str,
    payload: AdminResetPasswordPayload,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Admin-only: Reset another user's password without needing the old password.
    Sets force_reset=0 so the user is not forced through the reset flow again.
    """
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = db.query(models.User).filter(
        models.User.employee_number == employee_number
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # An admin cannot reset their OWN password via this endpoint.
    # They must ask the other admin to do it.
    if user.employee_number == admin.employee_number:
        raise HTTPException(status_code=403, detail="You cannot reset your own password. Ask another Admin.")

    user.password_hash = get_password_hash(payload.new_password)
    user.force_reset = 0
    db.commit()
    return {"message": f"Password for {employee_number} has been reset."}

