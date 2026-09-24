"""FastAPI router for Quizzes and Submissions in Person 3 Assessment Subsystem."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.assessment.schemas import (
    QuizCreateRequest,
    QuizResponse,
    QuizSubmissionRequest,
    QuizSubmissionResponse,
)
from app.assessment.services.quiz_service import quiz_service
from app.assessment.api.dependencies import get_current_user_id
from app.assessment.exceptions import (
    QuizNotFoundError,
    QuizAccessDeniedError,
    QuizAlreadySubmittedError,
    InvalidQuestionSubmissionError,
    InsufficientQuestionsError,
)

from sqlalchemy import select
from app.assessment.models import QuizAttempt

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])


@router.post("", response_model=QuizResponse, status_code=status.HTTP_201_CREATED)
def create_quiz(
    request: QuizCreateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Generate a new adaptive, non-repeating quiz for the authenticated user."""
    try:
        return quiz_service.generate_quiz(
            db=db,
            user_id=user_id,
            subject_id=request.subject_id,
            topic_ids=request.topic_ids,
            difficulty=request.difficulty,
            count=request.count or 10,
            course_id=request.course_id,
            title=request.title,
            document_id=request.document_id,
            source_type=request.source_type,
        )
    except InsufficientQuestionsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/attempts")
def get_user_quiz_attempts(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Retrieve quiz attempt history for the authenticated user."""
    stmt = (
        select(QuizAttempt)
        .where(QuizAttempt.user_id == user_id)
        .order_by(QuizAttempt.completed_at.desc())
    )
    attempts = db.execute(stmt).scalars().all()
    results = []
    for att in attempts:
        quiz_title = att.quiz.title if att.quiz else (att.topic_id or "Practice Quiz")
        quiz_subject = att.quiz.subject_id if att.quiz else "Academic Subject"
        results.append({
            "attempt_id": att.attempt_id,
            "quiz_id": att.quiz_id,
            "title": quiz_title,
            "subject": quiz_subject,
            "score": att.score or 0,
            "total": att.total_questions or 0,
            "percentage": att.score_percentage or 0.0,
            "completed_at": att.completed_at.isoformat() if att.completed_at else None,
        })
    return results


@router.get("/{quiz_id}", response_model=QuizResponse)
def get_quiz(
    quiz_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Retrieve quiz details and questions for the authenticated user."""
    try:
        return quiz_service.get_quiz_by_id(db=db, user_id=user_id, quiz_id=quiz_id)
    except QuizNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz '{quiz_id}' not found.",
        )
    except QuizAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to this quiz is forbidden for current user.",
        )


@router.post("/{quiz_id}/submit", response_model=QuizSubmissionResponse)
def submit_quiz(
    quiz_id: str,
    submission: QuizSubmissionRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Submit quiz answers for deterministic backend evaluation and attempt recording."""
    try:
        return quiz_service.submit_quiz(
            db=db,
            user_id=user_id,
            quiz_id=quiz_id,
            answers=submission.answers,
        )
    except QuizNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quiz '{quiz_id}' not found.",
        )
    except QuizAccessDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to submit this quiz.",
        )
    except QuizAlreadySubmittedError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Quiz '{quiz_id}' has already been submitted.",
        )
    except InvalidQuestionSubmissionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
