"""Person 4 Weekly Report SQLAlchemy model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Date, DateTime, Float, Integer, JSON, String

from app.database.base import Base


def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


class WeeklyReport(Base):
    """Weekly report summarizing academic progress, performance, and recommendations."""

    __tablename__ = "weekly_reports"

    report_id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    study_time_minutes = Column(Integer, nullable=False, default=0)
    topics_completed = Column(Integer, nullable=False, default=0)
    quiz_accuracy = Column(Float, nullable=False, default=0.0)
    strong_topics = Column(JSON, nullable=False, default=list)
    weak_topics = Column(JSON, nullable=False, default=list)
    planner_completion = Column(Float, nullable=False, default=0.0)
    upcoming_exams = Column(JSON, nullable=False, default=list)
    recommendations = Column(JSON, nullable=False, default=list)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
