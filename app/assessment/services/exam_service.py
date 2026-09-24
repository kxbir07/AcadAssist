"""Exam management and exam-aware assessment service for Person 3 Assessment Subsystem.

Provides CRUD for scheduled academic exams and determines exam-proximity assessment focus.
"""

from typing import List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.assessment.models import Exam, generate_uuid, utc_now
from app.assessment.schemas import ExamCreateRequest, ExamResponse
from app.assessment.exceptions import InvalidExamDateError
from app.core.config import settings


class ExamService:
    """Service handling exam records and exam proximity rules."""

    @classmethod
    def calculate_exam_focus(
        cls,
        exam_date: datetime,
        current_time: Optional[datetime] = None,
    ) -> Tuple[int, str]:
        """Calculate days remaining until exam and the corresponding assessment focus.

        Configurable Proximity Rules:
        - > 14 days (exam_normal_days) -> 'normal'
        - 7 to 14 days (exam_increased_days) -> 'increased'
        - 3 to 7 days (exam_weak_topic_days) -> 'targeted_weak_topic'
        - <= 2 days (exam_revision_days) -> 'revision_and_targeted'

        Returns:
            Tuple of (days_until_exam, assessment_focus_string)
        """
        if current_time is None:
            current_time = utc_now()

        # Handle timezone awareness normalization
        if exam_date.tzinfo is None and current_time.tzinfo is not None:
            exam_date = exam_date.replace(tzinfo=timezone.utc)
        elif exam_date.tzinfo is not None and current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)

        delta = exam_date - current_time
        total_secs = delta.total_seconds()
        days = max(0, int(round(total_secs / 86400.0)))

        if days > settings.assessment.exam_normal_days:
            focus = "normal"
        elif days >= settings.assessment.exam_increased_days:
            focus = "increased"
        elif days >= settings.assessment.exam_weak_topic_days:
            focus = "targeted_weak_topic"
        else:
            focus = "revision_and_targeted"

        return max(0, days), focus

    @classmethod
    def create_exam(
        cls,
        db: Session,
        user_id: str,
        request: ExamCreateRequest,
    ) -> ExamResponse:
        """Create and persist a new scheduled exam."""
        exam_id = generate_uuid()
        exam = Exam(
            exam_id=exam_id,
            user_id=user_id,
            course_id=request.course_id,
            subject_id=request.subject_id,
            title=request.title,
            exam_date=request.exam_date,
            created_at=utc_now(),
        )

        db.add(exam)
        db.commit()
        db.refresh(exam)

        days_until, focus = cls.calculate_exam_focus(exam.exam_date)

        return ExamResponse(
            exam_id=exam.exam_id,
            user_id=exam.user_id,
            course_id=exam.course_id,
            subject_id=exam.subject_id,
            title=exam.title,
            exam_date=exam.exam_date,
            created_at=exam.created_at,
            days_until_exam=days_until,
            assessment_focus=focus,
        )

    @classmethod
    def get_exams(
        cls,
        db: Session,
        user_id: str,
        subject_id: Optional[str] = None,
    ) -> List[ExamResponse]:
        """Retrieve all scheduled exams for a student."""
        stmt = select(Exam).where(Exam.user_id == user_id)
        if subject_id:
            stmt = stmt.where(Exam.subject_id == subject_id)
        stmt = stmt.order_by(Exam.exam_date.asc())

        exams = db.execute(stmt).scalars().all()
        now = utc_now()

        responses = []
        for e in exams:
            days_until, focus = cls.calculate_exam_focus(e.exam_date, current_time=now)
            responses.append(
                ExamResponse(
                    exam_id=e.exam_id,
                    user_id=e.user_id,
                    course_id=e.course_id,
                    subject_id=e.subject_id,
                    title=e.title,
                    exam_date=e.exam_date,
                    created_at=e.created_at,
                    days_until_exam=days_until,
                    assessment_focus=focus,
                )
            )
        return responses

    @classmethod
    def get_upcoming_exams(
        cls,
        db: Session,
        user_id: str,
        subject_id: Optional[str] = None,
    ) -> List[ExamResponse]:
        """Retrieve upcoming future exams (exam_date >= now) for a student."""
        now = utc_now()
        stmt = select(Exam).where(
            Exam.user_id == user_id,
            Exam.exam_date >= now,
        )
        if subject_id:
            stmt = stmt.where(Exam.subject_id == subject_id)
        stmt = stmt.order_by(Exam.exam_date.asc())

        exams = db.execute(stmt).scalars().all()

        responses = []
        for e in exams:
            days_until, focus = cls.calculate_exam_focus(e.exam_date, current_time=now)
            responses.append(
                ExamResponse(
                    exam_id=e.exam_id,
                    user_id=e.user_id,
                    course_id=e.course_id,
                    subject_id=e.subject_id,
                    title=e.title,
                    exam_date=e.exam_date,
                    created_at=e.created_at,
                    days_until_exam=days_until,
                    assessment_focus=focus,
                )
            )
        return responses
