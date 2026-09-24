"""Pydantic schemas for the Chat API.

Defines the contract between the React frontend and the FastAPI backend for POST /api/chat.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    """Citation or reference to source material used by the Agent."""

    chunk_id: Optional[str] = Field(default=None, description="UUID of the retrieved chunk")
    document_title: str = Field(default="Academic Document", description="Title of the source document")
    title: Optional[str] = Field(default=None, description="Title alias for citation compatibility")
    filename: Optional[str] = Field(default=None, description="Filename of the source document")
    page_number: Optional[int] = Field(default=None, description="Page number of the reference")
    slide_number: Optional[int] = Field(default=None, description="Slide number of the reference")
    score: Optional[float] = Field(default=None, description="Relevance or retrieval score")
    content_snippet: Optional[str] = Field(default=None, description="Brief excerpt from the document")
    citation: Optional[str] = Field(default=None, description="Formatted citation text")

    def model_post_init(self, __context: Any) -> None:
        if self.title and not self.document_title:
            self.document_title = self.title


class ActionItem(BaseModel):
    """Structured action generated during tool execution (e.g. quiz ready, study plan created)."""

    type: str = Field(..., description="Action category (e.g. quiz_generated, plan_updated)")
    description: str = Field(..., description="Human-readable description of the action")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action-specific structured data")


class ChatRequest(BaseModel):
    """Request payload sent from React to POST /api/chat."""

    message: str = Field(..., min_length=1, description="Student's prompt or question")
    user_id: Optional[str] = Field(default=None, description="Optional legacy user ID. Server always derives identity from token.")
    document_id: Optional[str] = Field(default=None, description="Optional active document ID for grounded Q&A, summarization, and quizzes")
    course_id: Optional[str] = Field(default=None, description="Optional course context")
    subject_id: Optional[str] = Field(default=None, description="Optional subject context")


class ChatResponse(BaseModel):
    """Response payload returned from POST /api/chat to React."""

    message: str = Field(..., description="Agent's grounded response to the student")
    sources: List[SourceItem] = Field(default_factory=list, description="Preserved citations from retrieved knowledge")
    actions: List[ActionItem] = Field(default_factory=list, description="Follow-up actions or structured tool results")
    execution_mode: str = Field(default="local_orchestrator", description="Execution mode: cloud_foundry or local_orchestrator")


__all__ = ["SourceItem", "ActionItem", "ChatRequest", "ChatResponse"]
