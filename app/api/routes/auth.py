"""Authentication API endpoints for AcadAssist."""

import re
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.shared import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128, description="Full student name")
    email: str = Field(..., description="Student email address")
    password: str = Field(..., min_length=8, description="Account password (min 8 chars)")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Student email address")
    password: str = Field(..., description="Account password")


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
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.user_id, "email": user.email})

    return AuthResponse(
        access_token=token,
        token_type="bearer",
        user=UserPayload(
            id=user.user_id,
            name=user.name,
            email=user.email,
            role=user.role,
            academic_level=user.academic_level,
            field_of_study=user.field_of_study,
            bio=user.bio,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
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
        user=UserPayload(
            id=user.user_id,
            name=user.name,
            email=user.email,
            role=user.role,
            academic_level=user.academic_level,
            field_of_study=user.field_of_study,
            bio=user.bio,
            created_at=user.created_at.isoformat() if user.created_at else None,
        ),
    )


@router.get("/me", response_model=UserPayload)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve identity profile of currently authenticated user."""
    return UserPayload(
        id=current_user.user_id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        academic_level=current_user.academic_level,
        field_of_study=current_user.field_of_study,
        bio=current_user.bio,
        created_at=current_user.created_at.isoformat() if current_user.created_at else None,
    )


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Acknowledge authenticated session termination."""
    return {"status": "success", "message": "Successfully logged out."}


__all__ = ["router"]
