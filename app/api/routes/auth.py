"""Authentication and user profile management API endpoints for AcadAssist."""

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.shared import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Full student name")
    email: str = Field(..., description="Student email address")
    password: str = Field(..., min_length=8, description="Account password (min 8 chars)")
    role: Optional[str] = Field(default="student", description="User role")
    academic_level: Optional[str] = Field(default="Undergraduate", description="Academic level")
    field_of_study: Optional[str] = Field(default="Computer Science", description="Field of study")
    bio: Optional[str] = Field(default=None, description="Short student bio")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Student email address")
    password: str = Field(..., description="Account password")


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=128)
    email: Optional[str] = Field(default=None)
    role: Optional[str] = Field(default=None, max_length=64)
    academic_level: Optional[str] = Field(default=None, max_length=64)
    field_of_study: Optional[str] = Field(default=None, max_length=128)
    bio: Optional[str] = Field(default=None)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, description="Current account password")
    new_password: str = Field(..., min_length=8, description="New account password (min 8 chars)")


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="Registered account email address")


class ForgotPasswordResponse(BaseModel):
    status: str = "success"
    message: str
    reset_token: Optional[str] = None
    expires_in_minutes: int = 15


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=10, description="Signed password reset token")
    new_password: str = Field(..., min_length=8, description="New account password (min 8 chars)")


class WorkspaceStatePayload(BaseModel):
    enrolled_courses: Optional[list[str]] = None
    course_progress: Optional[Dict[str, Any]] = None
    course_preferences: Optional[list[str]] = None
    events: Optional[list[Dict[str, Any]]] = None
    study_goals: Optional[list[Dict[str, Any]]] = None
    profile_extra: Optional[Dict[str, Any]] = None


class UserPayload(BaseModel):
    id: str
    name: str
    email: str
    role: str = "student"
    academic_level: Optional[str] = "Undergraduate"
    field_of_study: Optional[str] = "Computer Science"
    bio: Optional[str] = None
    created_at: Optional[str] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPayload


def _validate_email(email_str: str) -> str:
    cleaned = email_str.strip().lower()
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid email format.",
        )
    return cleaned


def _to_user_payload(user: User) -> UserPayload:
    return UserPayload(
        id=user.user_id,
        name=user.name,
        email=user.email,
        role=user.role or "student",
        academic_level=user.academic_level or "Undergraduate",
        field_of_study=user.field_of_study or "Computer Science",
        bio=user.bio,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


def _password_fingerprint(password_hash: Optional[str]) -> str:
    if not password_hash:
        return "no_hash"
    return password_hash[-16:]


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new student account with securely hashed credentials."""
    cleaned_email = _validate_email(payload.email)

    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters long.",
        )

    # Enforce duplicate email check at database level
    existing = db.query(User).filter(User.email == cleaned_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    hashed = hash_password(payload.password)
    user = User(
        name=payload.name.strip(),
        email=cleaned_email,
        password_hash=hashed,
        role=(payload.role or "student").strip(),
        academic_level=(payload.academic_level or "Undergraduate").strip(),
        field_of_study=(payload.field_of_study or "Computer Science").strip(),
        bio=payload.bio.strip() if payload.bio else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.user_id, "email": user.email})

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=_to_user_payload(user),
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate student credentials and issue signed JWT session token."""
    cleaned_email = _validate_email(payload.email)

    user = db.query(User).filter(User.email == cleaned_email).first()
    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user.user_id, "email": user.email})

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=_to_user_payload(user),
    )


@router.get("/me", response_model=UserPayload)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve identity profile of currently authenticated user."""
    return _to_user_payload(current_user)


@router.put("/profile", response_model=UserPayload)
@router.patch("/profile", response_model=UserPayload)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile fields for the currently authenticated user."""
    if payload.email is not None:
        cleaned_email = _validate_email(payload.email)
        if cleaned_email != current_user.email:
            conflict = (
                db.query(User)
                .filter(User.email == cleaned_email, User.user_id != current_user.user_id)
                .first()
            )
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Another account with this email address already exists.",
                )
            current_user.email = cleaned_email

    if payload.name is not None and payload.name.strip():
        current_user.name = payload.name.strip()
    if payload.role is not None and payload.role.strip():
        current_user.role = payload.role.strip()
    if payload.academic_level is not None and payload.academic_level.strip():
        current_user.academic_level = payload.academic_level.strip()
    if payload.field_of_study is not None and payload.field_of_study.strip():
        current_user.field_of_study = payload.field_of_study.strip()
    if payload.bio is not None:
        current_user.bio = payload.bio.strip()

    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return _to_user_payload(current_user)


@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify current password and update account password hash."""
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password must be at least 8 characters long.",
        )

    if current_user.password_hash:
        if not verify_password(payload.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )

    current_user.password_hash = hash_password(payload.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "message": "Password changed successfully."}


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Issue a signed, time-limited password reset token.

    When SMTP email delivery is not configured in local development, returns the
    reset token in the response so the local password reset flow can be completed safely.
    """
    cleaned_email = _validate_email(payload.email)
    user = db.query(User).filter(User.email == cleaned_email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with that email address.",
        )

    reset_token = create_access_token(
        {
            "sub": user.user_id,
            "email": user.email,
            "purpose": "password_reset",
            "fp": _password_fingerprint(user.password_hash),
        },
        expires_delta=timedelta(minutes=15),
    )

    return ForgotPasswordResponse(
        status="success",
        message="Password reset token generated. Enter the verification token and your new password to complete recovery.",
        reset_token=None if settings.is_production() else reset_token,
        expires_in_minutes=15,
    )


@router.post("/reset-password")
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Verify a signed password reset token and set a new bcrypt-hashed password."""
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password must be at least 8 characters long.",
        )

    claims = decode_access_token(payload.token.strip())
    if not claims or claims.get("purpose") != "password_reset" or "sub" not in claims:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token.",
        )

    user = db.query(User).filter(User.user_id == claims["sub"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    # Verify fingerprint so a reset token can only be used once
    expected_fp = _password_fingerprint(user.password_hash)
    if claims.get("fp") != expected_fp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset token has already been used or invalidated.",
        )

    user.password_hash = hash_password(payload.new_password)
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "success", "message": "Password has been reset successfully. You can now sign in."}


@router.get("/workspace-state")
def get_workspace_state(
    current_user: User = Depends(get_current_user),
):
    """Retrieve persisted per-user workspace state (courses, lessons, quizzes, events)."""
    raw = getattr(current_user, "workspace_state", None)
    if not raw:
        return {
            "user_id": current_user.user_id,
            "enrolled_courses": None,
            "course_progress": {},
            "course_preferences": [],
            "events": [],
            "study_goals": [],
            "profile_extra": {},
        }
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            data = {}
    except Exception:
        data = {}

    return {
        "user_id": current_user.user_id,
        "enrolled_courses": data.get("enrolled_courses"),
        "course_progress": data.get("course_progress") or {},
        "course_preferences": data.get("course_preferences") or [],
        "events": data.get("events") or [],
        "study_goals": data.get("study_goals") or [],
        "profile_extra": data.get("profile_extra") or {},
    }


@router.put("/workspace-state")
def save_workspace_state(
    payload: WorkspaceStatePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Persist per-user workspace state (courses, lessons, quizzes, events) in the database."""
    raw = getattr(current_user, "workspace_state", None)
    try:
        existing = json.loads(raw) if raw else {}
        if not isinstance(existing, dict):
            existing = {}
    except Exception:
        existing = {}

    if payload.enrolled_courses is not None:
        existing["enrolled_courses"] = payload.enrolled_courses
    if payload.course_progress is not None:
        existing["course_progress"] = payload.course_progress
    if payload.course_preferences is not None:
        existing["course_preferences"] = payload.course_preferences
    if payload.events is not None:
        existing["events"] = payload.events
    if payload.study_goals is not None:
        existing["study_goals"] = payload.study_goals
    if payload.profile_extra is not None:
        existing["profile_extra"] = payload.profile_extra

    current_user.workspace_state = json.dumps(existing)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "status": "success",
        "user_id": current_user.user_id,
        "enrolled_courses": existing.get("enrolled_courses"),
        "course_progress": existing.get("course_progress") or {},
        "course_preferences": existing.get("course_preferences") or [],
        "events": existing.get("events") or [],
        "study_goals": existing.get("study_goals") or [],
        "profile_extra": existing.get("profile_extra") or {},
    }


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Acknowledge authenticated session termination."""
    return {"status": "success", "message": "Successfully logged out."}


__all__ = ["router"]
