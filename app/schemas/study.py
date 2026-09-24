"""Pydantic schemas for Person 4 Study Intelligence."""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# --- Progress Schemas ---
class ProgressResponse(BaseModel):
    """Deterministic progress response."""
    course_completion: float = Field(..., description="Course completion percentage (0.0-100.0)")
    subject_completion: float = Field(..., description="Subject completion percentage (0.0-100.0)")
    topic_mastery: Dict[str, float] = Field(..., description="Map of topic_id to mastery percentage")
    quiz_accuracy: float = Field(..., description="Average quiz accuracy percentage")
    study_consistency: float = Field(..., description="Study consistency percentage based on active days")
    planner_completion: float = Field(..., description="Percentage of planned tasks completed")
    study_time: int = Field(..., description="Total completed study time in minutes")
    completed_topics: List[str] = Field(default_factory=list, description="IDs of completed topics")
    remaining_topics: List[str] = Field(default_factory=list, description="IDs of remaining topics")


# --- Recommendation Schemas ---
class RecommendationItem(BaseModel):
    """Single actionable study recommendation."""
    topic_id: str
    topic_name: str
    urgency: str  # critical, high, medium, normal
    action: str
    reason: str
    exam_id: Optional[str] = None
    days_until_exam: Optional[int] = None
    mastery_percentage: float


class RecommendationsResponse(BaseModel):
    """List of study recommendations for a user."""
    user_id: str
    recommendations: List[RecommendationItem]


# --- Plan & Task Schemas ---
class StudyPlanCreateRequest(BaseModel):
    """Request payload to generate a study plan."""
    user_id: str
    start_date: date
    end_date: date
    available_minutes_per_day: Optional[int] = Field(None, ge=30, le=720)


class StudyTaskResponse(BaseModel):
    """Single study task response."""
    task_id: str
    study_plan_id: Optional[str] = None
    user_id: str
    course_id: Optional[str] = None
    subject_id: Optional[str] = None
    topic_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    scheduled_date: date
    start_time: Optional[str] = None
    duration_minutes: int
    priority: str
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class StudyPlanResponse(BaseModel):
    """Study plan with associated tasks."""
    study_plan_id: str
    user_id: str
    start_date: date
    end_date: date
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tasks: List[StudyTaskResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class TodayPlanResponse(BaseModel):
    """Today's scheduled tasks."""
    date: str
    user_id: str
    total_tasks: int
    total_scheduled_minutes: int
    completed_minutes: int
    tasks: List[StudyTaskResponse] = Field(default_factory=list)


class TaskUpdateRequest(BaseModel):
    """Request payload to update task status or reschedule."""
    status: str = Field(..., description="New status: pending, in_progress, completed, skipped")
    rescheduled_date: Optional[date] = None
    rescheduled_time: Optional[str] = None


# --- Weekly Report Schemas ---
class WeeklyReportCreateRequest(BaseModel):
    """Request payload to generate a weekly report."""
    user_id: str
    week_start: date
    week_end: date


class WeeklyReportResponse(BaseModel):
    """Weekly report response."""
    report_id: Optional[str] = None
    user_id: str
    week_start: str
    week_end: str
    study_time_minutes: int
    topics_completed: int
    quiz_accuracy: float
    strong_topics: List[Any] = Field(default_factory=list)
    weak_topics: List[Any] = Field(default_factory=list)
    planner_completion: float
    upcoming_exams: List[Any] = Field(default_factory=list)
    recommendations: List[Any] = Field(default_factory=list)
    generated_at: Optional[str] = None
