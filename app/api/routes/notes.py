"""API routes for user notes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.note import Note
from app.models.shared import User

router = APIRouter(prefix="/notes", tags=["Notes"])


class NoteCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    subject: Optional[str] = None
    note_type: str = "Summary"
    document_id: Optional[str] = None


class NoteUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    subject: Optional[str] = None
    note_type: Optional[str] = None


class NoteResponse(BaseModel):
    id: str
    user_id: str
    document_id: Optional[str] = None
    title: str
    content: str
    subject: Optional[str] = None
    note_type: str
    created_at: str
    updated_at: str


@router.get("", response_model=List[NoteResponse])
def list_notes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List notes strictly belonging to the authenticated user."""
    notes = (
        db.query(Note)
        .filter(Note.user_id == current_user.user_id)
        .order_by(Note.created_at.desc())
        .all()
    )
    return [
        NoteResponse(
            id=n.note_id,
            user_id=n.user_id,
            document_id=n.document_id,
            title=n.title,
            content=n.content,
            subject=n.subject,
            note_type=n.note_type,
            created_at=n.created_at.isoformat() if n.created_at else "",
            updated_at=n.updated_at.isoformat() if n.updated_at else "",
        )
        for n in notes
    ]


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    payload: NoteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new note for the authenticated user."""
    note = Note(
        user_id=current_user.user_id,
        document_id=payload.document_id,
        title=payload.title.strip(),
        content=payload.content.strip(),
        subject=payload.subject.strip() if payload.subject else None,
        note_type=payload.note_type,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteResponse(
        id=note.note_id,
        user_id=note.user_id,
        document_id=note.document_id,
        title=note.title,
        content=note.content,
        subject=note.subject,
        note_type=note.note_type,
        created_at=note.created_at.isoformat() if note.created_at else "",
        updated_at=note.updated_at.isoformat() if note.updated_at else "",
    )


@router.patch("/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: str,
    payload: NoteUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a note, strictly verifying ownership."""
    note = db.query(Note).filter(Note.note_id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    if note.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this note.")

    if payload.title is not None:
        note.title = payload.title.strip()
    if payload.content is not None:
        note.content = payload.content.strip()
    if payload.subject is not None:
        note.subject = payload.subject.strip()
    if payload.note_type is not None:
        note.note_type = payload.note_type

    db.commit()
    db.refresh(note)
    return NoteResponse(
        id=note.note_id,
        user_id=note.user_id,
        document_id=note.document_id,
        title=note.title,
        content=note.content,
        subject=note.subject,
        note_type=note.note_type,
        created_at=note.created_at.isoformat() if note.created_at else "",
        updated_at=note.updated_at.isoformat() if note.updated_at else "",
    )


@router.delete("/{note_id}")
def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a note, strictly verifying ownership."""
    note = db.query(Note).filter(Note.note_id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    if note.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this note.")

    db.delete(note)
    db.commit()
    return {"status": "success", "message": f"Note '{note_id}' deleted."}


__all__ = ["router"]
