"""API routes for Study Plans and Tasks (Person 4)."""

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.shared import User
from app.models.study_plan import StudyPlan, StudyTask
from app.schemas.study import (
    StudyPlanCreateRequest,
    StudyPlanResponse,
    StudyTaskResponse,
    TaskUpdateRequest,
    TodayPlanResponse,
)
from app.services.planner import create_study_plan, get_today_plan, update_task_status

router = APIRouter(prefix="/plans", tags=["Study Plans"])
tasks_router = APIRouter(prefix="/tasks", tags=["Study Tasks"])


@router.post("", response_model=StudyPlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: StudyPlanCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and store a new exam-aware study plan for authenticated user."""
    # Ensure client-supplied user_id cannot impersonate another user
    target_user_id = current_user.user_id
    if payload.user_id and payload.user_id != target_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create a study plan for another user",
        )

    try:
        plan = create_study_plan(
            user_id=target_user_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            available_minutes_per_day=payload.available_minutes_per_day,
            db=db,
        )
        return plan
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create study plan: {str(e)}",
        )


@router.get("", response_model=List[StudyPlanResponse])
def list_plans(
    user_id: Optional[str] = Query(None, description="Optional legacy user ID filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all study plans for the authenticated user."""
    if user_id and user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to study plans of another user is forbidden",
        )
    plans = (
        db.query(StudyPlan)
        .filter(StudyPlan.user_id == current_user.user_id)
        .order_by(StudyPlan.created_at.desc())
        .all()
    )
    return plans


@router.get("/today", response_model=TodayPlanResponse)
def get_today_study_plan(
    user_id: Optional[str] = Query(None, description="Optional legacy user ID"),
    target_date: Optional[date] = Query(None, description="Optional target date (defaults to today)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve today's scheduled study tasks for the authenticated user."""
    if user_id and user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to another user's daily plan is forbidden",
        )
    try:
        plan_data = get_today_plan(user_id=current_user.user_id, target_date=target_date, db=db)
        return TodayPlanResponse(**plan_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve today's plan: {str(e)}",
        )


@router.get("/{plan_id}", response_model=StudyPlanResponse)
def get_plan_by_id(
    plan_id: str,
    user_id: Optional[str] = Query(None, description="Optional legacy user ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a specific study plan and its tasks scoped to authenticated user."""
    if user_id and user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to another user's study plan is forbidden",
        )
    plan = (
        db.query(StudyPlan)
        .filter(StudyPlan.study_plan_id == plan_id, StudyPlan.user_id == current_user.user_id)
        .first()
    )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan '{plan_id}' not found or access unauthorized",
        )
    return plan


@tasks_router.patch("/{task_id}", response_model=StudyTaskResponse)
def patch_task(
    task_id: str,
    payload: TaskUpdateRequest,
    user_id: Optional[str] = Query(None, description="Optional legacy user ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update study task completion status or reschedule time scoped to authenticated user."""
    if user_id and user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to another user's task is forbidden",
        )
    try:
        task = update_task_status(
            task_id=task_id,
            status=payload.status,
            user_id=current_user.user_id,
            rescheduled_date=payload.rescheduled_date,
            rescheduled_time=payload.rescheduled_time,
            db=db,
        )
        return task
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}",
        )

