"""Pydantic schemas for Knowledge search operations."""

from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    """Payload for POST /api/knowledge/search."""

    user_id: str | None = Field(default=None, description="Optional requesting user ID (authenticated identity takes precedence)")
    query: str = Field(..., min_length=1, description="Natural language search query")
    course_id: str | None = Field(default=None, description="Optional Course filter")
    subject_id: str | None = Field(default=None, description="Optional Subject filter")
    top_k: int = Field(default=5, ge=1, le=50, description="Max results (1 to 50)")


class KnowledgeSearchResult(BaseModel):
    """Individual chunk search result item."""

    chunk_id: str
    document_id: str
    course_id: str
    subject_id: str
    content: str
    document_title: str
    section_title: str | None = None
    filename: str
    page_number: int | None = None
    slide_number: int | None = None
    score: float


class KnowledgeSearchResponse(BaseModel):
    """Standardized response schema for knowledge retrieval."""

    results: list[KnowledgeSearchResult] = Field(default_factory=list)
