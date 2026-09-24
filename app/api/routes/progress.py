"""API routes for progress tracking and recommendations (Person 4)."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.shared import User
from app.schemas.study import ProgressResponse, RecommendationsResponse
from app.services.progress import get_progress
from app.services.recommendations import get_recommendations

router = APIRouter(prefix="/progress", tags=["Progress"])


@router.get("", response_model=ProgressResponse)
def get_user_progress(
    user_id: Optional[str] = Query(None, description="Optional legacy user ID filter"),
    course_id: Optional[str] = Query(None, description="Filter by course ID"),
    subject_id: Optional[str] = Query(None, description="Filter by subject ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve deterministic academic progress metrics for authenticated user."""
    if user_id and user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to another user's progress is forbidden",
        )
    try:
        data = get_progress(user_id=current_user.user_id, course_id=course_id, subject_id=subject_id, db=db)
        return ProgressResponse(**data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate progress: {str(e)}",
        )


@router.get("/recommendations", response_model=RecommendationsResponse)
def get_user_recommendations(
    user_id: Optional[str] = Query(None, description="Optional legacy user ID filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve actionable, deterministic study recommendations for authenticated user."""
    if user_id and user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to another user's recommendations is forbidden",
        )
    try:
        recs = get_recommendations(user_id=current_user.user_id, db=db)
        return RecommendationsResponse(user_id=current_user.user_id, recommendations=recs)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}",
        )

