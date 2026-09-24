"""Schemas package exports."""

from app.schemas.document import (
    DocumentListResponse,
    DocumentProcessResponse,
    DocumentResponse,
    DocumentSummaryRequest,
    DocumentSummaryResponse,
)
from app.schemas.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
)
from app.schemas.study import (
    ProgressResponse,
    RecommendationItem,
    RecommendationsResponse,
    StudyPlanCreateRequest,
    StudyPlanResponse,
    StudyTaskResponse,
    TaskUpdateRequest,
    TodayPlanResponse,
    WeeklyReportCreateRequest,
    WeeklyReportResponse,
)

__all__ = [
    "DocumentResponse",
    "DocumentListResponse",
    "DocumentProcessResponse",
    "DocumentSummaryRequest",
    "DocumentSummaryResponse",
    "KnowledgeSearchRequest",
    "KnowledgeSearchResponse",
    "KnowledgeSearchResult",
    "ProgressResponse",
    "RecommendationItem",
    "RecommendationsResponse",
    "StudyPlanCreateRequest",
    "StudyPlanResponse",
    "StudyTaskResponse",
    "TodayPlanResponse",
    "TaskUpdateRequest",
    "WeeklyReportCreateRequest",
    "WeeklyReportResponse",
]
