"""Document and Knowledge Chunk models owned by Person 2."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.base import Base


def generate_uuid() -> str:
    """Generate a standard UUID4 string."""
    return str(uuid.uuid4())


class Document(Base):
    """Document record tracking user uploads and processing state."""

    __tablename__ = "documents"
    __table_args__ = {"extend_existing": True}

    document_id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    course_id = Column(String(64), nullable=False, index=True)
    subject_id = Column(String(64), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(32), nullable=False)  # pdf, ppt, pptx, docx, txt
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    storage_path = Column(String(512), nullable=False)
    visibility = Column(String(32), nullable=False, default="private")  # private, public
    checksum = Column(String(64), nullable=True, index=True)
    size_bytes = Column(Integer, nullable=False, default=0)
    status = Column(String(32), nullable=False, default="uploaded")  # uploaded, queued, processing, processed, failed
    processing_error = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def id(self) -> str:
        return self.document_id

    @property
    def owner_user_id(self) -> str:
        return self.user_id


class Chunk(Base):
    """Individual searchable chunk extracted from a Document."""

    __tablename__ = "document_chunks"
    __table_args__ = {"extend_existing": True}

    chunk_id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    course_id = Column(String(64), nullable=False, index=True)
    subject_id = Column(String(64), nullable=False, index=True)
    visibility = Column(String(32), nullable=False, default="private")
    content = Column(Text, nullable=False)
    title = Column(String(255), nullable=True)
    section_title = Column(String(255), nullable=True)
    document_title = Column(String(255), nullable=True)
    filename = Column(String(255), nullable=False)
    page_number = Column(Integer, nullable=True)
    slide_number = Column(Integer, nullable=True)
    chunk_index = Column(Integer, nullable=False)
    total_chunks = Column(Integer, nullable=False)
    content_type = Column(String(64), nullable=False, default="text")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    content_vector = Column(Text, nullable=True)  # JSON-encoded 1536-dim vector for DB reference

