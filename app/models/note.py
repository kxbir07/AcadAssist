"""Note database model for user-created and AI-generated study notes."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Text

from app.database.base import Base


def generate_uuid() -> str:
    """Generate a standard UUID4 string."""
    return str(uuid.uuid4())


class Note(Base):
    """Note entity belonging to an authenticated user."""

    __tablename__ = "notes"
    __table_args__ = {"extend_existing": True}

    note_id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    document_id = Column(String(36), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    subject = Column(String(128), nullable=True)
    note_type = Column(String(32), nullable=False, default="Summary")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def id(self) -> str:
        return self.note_id


__all__ = ["Note"]
