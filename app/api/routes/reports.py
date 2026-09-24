"""API routes for weekly reports (Person 4)."""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.shared import User
from app.schemas.study import WeeklyReportCreateRequest, WeeklyReportResponse
from app.services.reports import generate_weekly_report, get_weekly_reports

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/weekly", response_model=WeeklyReportResponse, status_code=status.HTTP_201_CREATED)
def create_weekly_report(
    payload: WeeklyReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and store a new weekly study report for authenticated user."""
    target_user_id = current_user.user_id
    if payload.user_id and payload.user_id != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot generate weekly report for another user",
        )
    try:
        report = generate_weekly_report(
            user_id=target_user_id,
            week_start=payload.week_start,
            week_end=payload.week_end,
            db=db,
        )
        return WeeklyReportResponse(**report)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate weekly report: {str(e)}",
        )


@router.get("/weekly", response_model=List[WeeklyReportResponse])
def get_user_weekly_reports(
    user_id: Optional[str] = Query(None, description="Optional legacy user ID filter"),
    week_start: Optional[date] = Query(None, description="Filter by week start date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve saved weekly reports for the authenticated user."""
    if user_id and user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to another user's weekly reports is forbidden",
        )
    try:
        reports = get_weekly_reports(user_id=current_user.user_id, week_start=week_start, db=db)
        return [WeeklyReportResponse(**r) for r in reports]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch weekly reports: {str(e)}",
        )

