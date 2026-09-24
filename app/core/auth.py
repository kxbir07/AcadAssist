"""Authentication dependency and trusted identity resolution for AcadAssist."""

from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.shared import User

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db),
) -> User:
    """Resolve and authenticate the trusted server-side current user.

    In production:
    - Strictly enforces valid Bearer JWT tokens.
    - Resolves User from database.
    - Rejects unauthenticated or tampered requests with HTTP 401 Unauthorized.

    In test environments only:
    - Evaluates Bearer token first.
    - Allows X-User-ID fallback for test fixtures.

    Real development/staging/production requests require Bearer authentication.
    """
    token = auth.credentials if auth else None

    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            user_id = payload["sub"]
            user = db.query(User).filter(User.user_id == user_id).first()
            if user:
                return user
        # If token was supplied but is invalid/expired
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or malformed authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In test environments only, support the test fixture X-User-ID header
    if settings.ENVIRONMENT.lower() in ("test", "testing") and x_user_id and x_user_id.strip():
        uid = x_user_id.strip()
        user = db.query(User).filter(User.user_id == uid).first()
        if not user:
            user = User(
                user_id=uid,
                name=uid.replace("_", " ").title(),
                email=f"{uid}@test.local",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    # No valid authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide a valid Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user_optional(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Optional user resolution for endpoints that support public/anonymous previews."""
    try:
        return get_current_user(auth=auth, x_user_id=x_user_id, db=db)
    except HTTPException:
        return None


def get_current_user_id(current_user: User = Depends(get_current_user)) -> str:
    """Convenience dependency returning the trusted user_id string."""
    return current_user.user_id


__all__ = [
    "get_current_user",
    "get_current_user_optional",
    "get_current_user_id",
]
