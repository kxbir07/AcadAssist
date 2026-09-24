"""Pydantic schemas for Document operations."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Document entity response schema."""

    model_config = ConfigDict(from_attributes=True)

    document_id: str
    user_id: str
    course_id: str
    subject_id: str
    filename: str
    file_type: str
    title: str
    description: str | None = None
    storage_path: str
    visibility: str = "private"
    checksum: str | None = None
    size_bytes: int = 0
    status: str
    processing_error: str | None = None
    uploaded_at: datetime
    processed_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentListResponse(BaseModel):
    """Paginated list of document responses."""

    documents: list[DocumentResponse]
    total: int


class DocumentProcessResponse(BaseModel):
    """Response returned when triggering document processing."""

    document_id: str
    status: str
    message: str
    processed_at: datetime | None = None


class DocumentSummaryRequest(BaseModel):
    """Request schema for summarizing a document."""

    mode: str = Field(
        default="quick",
        description="Summary mode: quick, detailed, exam, or revision",
    )


class DocumentSummaryResponse(BaseModel):
    """Response returned from document summarization contract."""

    document_id: str
    title: str
    filename: str
    mode: str
    status: str
    summary: str
    total_chunks: int = 0
    sections: list[dict[str, Any]] = Field(default_factory=list)
