"""FastAPI router for Exams in Person 3 Assessment Subsystem."""

from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.assessment.schemas import (
    ExamCreateRequest,
    ExamResponse,
)
from app.assessment.services.exam_service import ExamService
from app.assessment.api.dependencies import get_current_user_id

router = APIRouter(prefix="/exams", tags=["Exams"])


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    request: ExamCreateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Schedule and persist a new academic exam."""
    return ExamService.create_exam(db=db, user_id=user_id, request=request)


@router.get("", response_model=List[ExamResponse])
def get_exams(
    subject_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Retrieve all scheduled exams for the authenticated user."""
    return ExamService.get_exams(db=db, user_id=user_id, subject_id=subject_id)


@router.get("/upcoming", response_model=List[ExamResponse])
def get_upcoming_exams(
    subject_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Retrieve upcoming future exams for the authenticated user."""
    return ExamService.get_upcoming_exams(db=db, user_id=user_id, subject_id=subject_id)
