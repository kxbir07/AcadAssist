"""Centralized document access control and authorization service for AcadAssist."""

from fastapi import HTTPException, status

from app.models.document import Document
from app.models.shared import User


def can_access_document(user: User, document: Document, require_owner: bool = False) -> bool:
    """Evaluate whether the given user has permission to access the document.

    Rules:
    - Document owner is always granted access.
    - Public documents are accessible for read/search/download/rag operations (require_owner=False).
    - Destructive actions (update, delete, status override) strictly require ownership (require_owner=True).
    - Future ACL / shared document access can be plugged in here.
    """
    if not user or not document:
        return False

    is_owner = document.user_id == user.user_id
    if is_owner:
        return True

    if not require_owner and getattr(document, "visibility", "private") == "public":
        return True

    return False


def verify_document_access(
    user: User,
    document: Document,
    require_owner: bool = False,
    error_message: str | None = None,
) -> None:
    """Enforce document access control, raising HTTP 403 Forbidden on failure."""
    if not can_access_document(user, document, require_owner=require_owner):
        detail = error_message or (
            "Forbidden: You do not own this document."
            if require_owner
            else "Forbidden: You do not have access to this document."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


__all__ = ["can_access_document", "verify_document_access"]
