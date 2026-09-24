"""FastAPI router for Performance Analytics and Weak Topics in Person 3 Assessment Subsystem."""

from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.assessment.schemas import (
    PerformanceMetricsResponse,
    WeakTopicsResponse,
)
from app.assessment.services.quiz_service import quiz_service
from app.assessment.api.dependencies import get_current_user_id

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get("", response_model=PerformanceMetricsResponse)
def get_performance_metrics(
    subject_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Retrieve comprehensive assessment performance analytics for the authenticated user."""
    return quiz_service.get_performance(db=db, user_id=user_id, subject_id=subject_id)


@router.get("/weak-topics", response_model=WeakTopicsResponse)
def get_weak_topics(
    subject_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Retrieve detected weak topics for the authenticated user."""
    return quiz_service.get_weak_topics(db=db, user_id=user_id, subject_id=subject_id)
