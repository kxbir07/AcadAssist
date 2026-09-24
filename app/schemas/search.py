"""Pydantic schemas for the search_knowledge contract.

Matches the frozen contract:
POST /api/knowledge/search
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class SearchKnowledgeRequest(BaseModel):
    """Request payload for searching the knowledge base."""

    user_id: Optional[str] = Field(default=None, description="UUID of the student user")
    query: str = Field(..., description="Search query string")
    course_id: Optional[str] = Field(default=None, description="Optional UUID filter for course")
    subject_id: Optional[str] = Field(default=None, description="Optional UUID filter for subject")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of chunks to return")


class ChunkResult(BaseModel):
    """Single retrieved knowledge base chunk."""

    chunk_id: str = Field(..., description="UUID of the chunk")
    document_id: str = Field(..., description="UUID of the source document")
    course_id: Optional[str] = Field(default=None, description="UUID of the course")
    subject_id: Optional[str] = Field(default=None, description="UUID of the subject")
    content: str = Field(..., description="Text content of the retrieved chunk")
    document_title: str = Field(..., description="Title of the source document")
    section_title: Optional[str] = Field(default=None, description="Section or chapter title")
    filename: str = Field(..., description="Original filename of the document")
    page_number: Optional[int] = Field(default=None, description="Page number if applicable")
    slide_number: Optional[int] = Field(default=None, description="Slide number if applicable")
    score: float = Field(..., description="Retrieval similarity score")


class SearchKnowledgeResponse(BaseModel):
    """Response payload containing retrieved knowledge chunks."""

    results: List[ChunkResult] = Field(default_factory=list, description="List of matching chunks")


__all__ = ["SearchKnowledgeRequest", "ChunkResult", "SearchKnowledgeResponse"]
