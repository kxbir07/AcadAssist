"""Person 4 Study Plan and Study Task SQLAlchemy models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.base import Base


def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


class StudyPlan(Base):
    """StudyPlan representing a scheduled planning period for a user."""

    __tablename__ = "study_plans"

    study_plan_id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(32), nullable=False, default="active")  # active, completed, cancelled
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tasks = relationship("StudyTask", back_populates="plan", cascade="all, delete-orphan")


class StudyTask(Base):
    """StudyTask representing a discrete study block."""

    __tablename__ = "study_tasks"

    task_id = Column(String(36), primary_key=True, default=generate_uuid)
    study_plan_id = Column(String(36), ForeignKey("study_plans.study_plan_id"), nullable=True, index=True)
    user_id = Column(String(64), nullable=False, index=True)
    course_id = Column(String(64), nullable=True)
    subject_id = Column(String(64), nullable=True)
    topic_id = Column(String(64), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(10), nullable=True)  # e.g. "09:00"
    duration_minutes = Column(Integer, nullable=False, default=45)
    priority = Column(String(32), nullable=False, default="normal")  # low, normal, medium, high, critical
    status = Column(String(32), nullable=False, default="pending")  # pending, in_progress, completed, skipped
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    plan = relationship("StudyPlan", back_populates="tasks")
