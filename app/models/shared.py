"""Shared AcadAssist application entities and models.

These entities map directly to the single shared application database tables.
All models use extend_existing=True to guarantee no duplicate tables are created.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String, Text

from app.database.base import Base


def generate_uuid() -> str:
    """Generate a UUID4 string."""
    return str(uuid.uuid4())


class User(Base):
    """User entity in shared database."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    user_id = Column(String(64), primary_key=True, default=generate_uuid)
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=True)
    role = Column(String(64), nullable=False, default="student")
    academic_level = Column(String(64), nullable=True, default="Undergraduate")
    field_of_study = Column(String(128), nullable=True, default="Computer Science")
    bio = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def id(self) -> str:
        return self.user_id


class Course(Base):
    """Academic Course entity in shared database."""

    __tablename__ = "courses"
    __table_args__ = {"extend_existing": True}

    course_id = Column(String(64), primary_key=True, default=generate_uuid)
    name = Column(String(128), nullable=False)
    code = Column(String(32), nullable=True)


class Subject(Base):
    """Academic Subject entity within a Course in shared database."""

    __tablename__ = "subjects"
    __table_args__ = {"extend_existing": True}

    subject_id = Column(String(64), primary_key=True, default=generate_uuid)
    course_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)


class Topic(Base):
    """Topic entity within a Subject in shared database."""

    __tablename__ = "topics"
    __table_args__ = {"extend_existing": True}

    topic_id = Column(String(64), primary_key=True, default=generate_uuid)
    subject_id = Column(String(64), nullable=False, index=True)
    course_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    difficulty = Column(String(32), nullable=False, default="medium")
    estimated_minutes = Column(Integer, nullable=False, default=60)


class TopicMastery(Base):
    """Authoritative topic mastery records produced by Person 3 / consumed by Person 4."""

    __tablename__ = "topic_mastery"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(64), nullable=False, index=True)
    topic_id = Column(String(64), nullable=False, index=True)
    mastery_percentage = Column(Float, nullable=False, default=0.0)
    quizzes_attempted = Column(Integer, nullable=False, default=0)
    quizzes_passed = Column(Integer, nullable=False, default=0)
    is_weak = Column(Boolean, nullable=False, default=False)
    is_completed = Column(Boolean, nullable=False, default=False)
    last_assessed_at = Column(DateTime, nullable=True)


# Re-export canonical Exam and QuizAttempt entities from Person 3 assessment subsystem
from app.assessment.models import Exam, QuizAttempt

__all__ = ["User", "Course", "Subject", "Topic", "Exam", "TopicMastery", "QuizAttempt"]
