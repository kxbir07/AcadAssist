"""HTTP API endpoints exposing the 11 AcadAssist Tools for Microsoft Foundry.

All endpoints strictly enforce Zero Trust server-derived authentication via get_current_user.
Clients cannot specify arbitrary user IDs to bypass authorization.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.shared import User
from app.schemas.tools import (
    CreateStudyPlanParams,
    GenerateQuizParams,
    GenerateWeeklyReportParams,
    GetPerformanceParams,
    GetProgressParams,
    GetTodayPlanParams,
    GetUpcomingExamsParams,
    GetWeakTopicsParams,
    SearchKnowledgeParams,
    SubmitQuizParams,
    SummarizeDocumentParams,
)
from app.azure.adapters import ToolDispatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["Foundry Tools"])

_dispatcher: Optional[ToolDispatcher] = None


def get_dispatcher() -> ToolDispatcher:
    """Retrieve or initialize the ToolDispatcher instance."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = ToolDispatcher()
    return _dispatcher


def _enforce_user_identity(params_user_id: Optional[str], current_user: User) -> str:
    """Enforce zero-trust server-derived user identity.

    - Rejects empty user_id string with 400.
    - Rejects user_id mismatch with 403.
    - Returns current_user.user_id as the authoritative identity.
    """
    if params_user_id is not None:
        clean = params_user_id.strip()
        if not clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The 'user_id' field is mandatory.",
            )
        if clean != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: Cannot execute tool as another user",
            )
    return current_user.user_id


@router.post(
    "/search_knowledge",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    operation_id="search_knowledge",
    summary="Search indexed course materials",
    description="Search indexed documents, lecture slides, and notes using BM25 and vector embeddings.",
)
def search_knowledge(
    params: SearchKnowledgeParams,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    effective_user_id = _enforce_user_identity(params.user_id, current_user)
    dispatcher = get_dispatcher()
    response = dispatcher.kb_adapter.search_knowledge(
        user_id=effective_user_id,
        query=params.query.strip(),
        course_id=params.course_id.strip() if params.course_id else None,
        subject_id=params.subject_id.strip() if params.subject_id else None,
        top_k=params.top_k,
    )
    return response.model_dump()


@router.post(
    "/summarize_document",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    operation_id="summarize_document",
    summary="Summarize an academic document",
    description="Retrieve document chunks and generate a grounded summary for the specified document.",
)
def summarize_document(
    params: SummarizeDocumentParams,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    effective_user_id = _enforce_user_identity(params.user_id, current_user)
    if not params.document_id or not params.document_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'document_id' field is mandatory.",
        )
    dispatcher = get_dispatcher()
    try:
        return dispatcher.kb_adapter.summarize_document(
            user_id=effective_user_id,
            document_id=params.document_id.strip(),
            mode=params.mode.strip(),
            db=db,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post(
    "/generate_quiz",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    operation_id="generate_quiz",
    summary="Generate an adaptive practice quiz",
    description="Generate adaptive quiz questions grounded in course materials.",
)
def generate_quiz(
    params: GenerateQuizParams,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    effective_user_id = _enforce_user_identity(params.user_id, current_user)
    dispatcher = get_dispatcher()
    return dispatcher.assessment_adapter.generate_quiz(
        user_id=effective_user_id,
        subject_id=params.subject_id.strip() if params.subject_id else None,
        topic_ids=params.topic_ids,
        difficulty=params.difficulty.strip() if params.difficulty else "medium",
        count=params.count,
        document_id=params.document_id,
        course_id=params.course_id,
    )


@router.post(
    "/submit_quiz",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    operation_id="submit_quiz",
    summary="Submit student quiz answers",
    description="Submit answers for a previously generated quiz, calculate score, and record history.",
)
def submit_quiz(
    params: SubmitQuizParams,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    effective_user_id = _enforce_user_identity(params.user_id, current_user)
    if not params.quiz_id or not params.quiz_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'quiz_id' field is mandatory.",
        )
    dispatcher = get_dispatcher()
    try:
        return dispatcher.assessment_adapter.submit_quiz(
            user_id=effective_user_id,
            quiz_id=params.quiz_id.strip(),
            answers=params.answers,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc).strip("'"),
        )


@router.post(
    "/get_performance",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    operation_id="get_performance",
    summary="Retrieve historical student performance metrics",
    description="Retrieve historical assessment scores, quiz statistics, and performance trends.",
)
def get_performance(
    params: GetPerformanceParams,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    effective_user_id = _enforce_user_identity(params.user_id, current_user)
    dispatcher = get_dispatcher()
    return dispatcher.assessment_adapter.get_performance(
        user_id=effective_user_id,
        subject_id=params.subject_id.strip() if params.subject_id else None,
    )


@router.post(
    "/get_weak_topics",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    operation_id="get_weak_topics",
    summary="Identify student weak topics",
    description="Identify topics where the student has struggled based on quiz and assessment history.",
)
def get_weak_topics(
    params: GetWeakTopicsParams,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    effective_user_id = _enforce_user_identity(params.user_id, current_user)
    dispatcher = get_dispatcher()
    return dispatcher.assessment_adapter.get_weak_topics(
        user_id=effective_user_id,
        subject_id=params.subject_id.strip() if params.subject_id else None,
    )


@router.post(
    "/get_progress",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    operation_id="get_progress",
    summary="Retrieve course completion progress",
    description="Retrieve current course completion percentage, reading milestone progress, and study streaks.",
)
def get_progress(
    params: GetProgressParams,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    effective_user_id = _enforce_user_identity(params.user_id, current_user)
    dispatcher = get_dispatcher()
    return dispatcher.study_adapter.get_progress(
        user_id=effective_user_id,
        course_id=params.course_id.strip() if params.course_id else None,
        subject_id=params.subject_id.strip() if params.subject_id else None,
    )


@router.post(
    "/get_upcoming_exams",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    operation_id="get_upcoming_exams",
    summary="Retrieve upcoming exams and deadlines",
    description="Retrieve scheduled exams, tests, and assignment deadlines.",
)
def get_upcoming_exams(
    params: GetUpcomingExamsParams,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    effective_user_id = _enforce_user_identity(params.user_id, current_user)
    dispatcher = get_dispatcher()
    return dispatcher.study_adapter.get_upcoming_exams(
        user_id=effective_user_id,
    )


@router.post(
    "/create_study_plan",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    operation_id="create_study_plan",
    summary="Create an optimized study plan",
    description="Create an optimized daily study plan tailored to weak topics and available study hours.",
)
def create_study_plan(
    params: CreateStudyPlanParams,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    effective_user_id = _enforce_user_identity(params.user_id, current_user)
    dispatcher = get_dispatcher()
    raw_dict = params.model_dump()
    duration = raw_dict.get("duration_days") or raw_dict.get("days")
    return dispatcher.study_adapter.create_study_plan(
        user_id=effective_user_id,
        start_date=params.start_date.strip() if params.start_date else None,
        end_date=params.end_date.strip() if params.end_date else None,
        duration_days=duration,
        current_date=raw_dict.get("current_date"),
    )


@router.post(
    "/get_today_plan",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    operation_id="get_today_plan",
    summary="Retrieve today's study schedule",
    description="Retrieve the student's scheduled study sessions and practice tasks for today.",
)
def get_today_plan(
    params: GetTodayPlanParams,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    effective_user_id = _enforce_user_identity(params.user_id, current_user)
    dispatcher = get_dispatcher()
    return dispatcher.study_adapter.get_today_plan(
        user_id=effective_user_id,
    )


@router.post(
    "/generate_weekly_report",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    operation_id="generate_weekly_report",
    summary="Generate a weekly learning summary",
    description="Generate a weekly learning summary including hours studied, concepts mastered, and streak status.",
)
def generate_weekly_report(
    params: GenerateWeeklyReportParams,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    effective_user_id = _enforce_user_identity(params.user_id, current_user)
    if not params.week_start or not params.week_start.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'week_start' field is mandatory.",
        )
    if not params.week_end or not params.week_end.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'week_end' field is mandatory.",
        )
    dispatcher = get_dispatcher()
    return dispatcher.study_adapter.generate_weekly_report(
        user_id=effective_user_id,
        week_start=params.week_start.strip(),
        week_end=params.week_end.strip(),
    )


__all__ = ["router"]
