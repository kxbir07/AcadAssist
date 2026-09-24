"""Tests for exam scheduling, upcoming exam queries, and exam proximity assessment rules."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.assessment.services.exam_service import ExamService
from app.assessment.schemas import ExamCreateRequest
from app.core.config import settings


def test_exam_creation_and_upcoming_retrieval(db_session: Session):
    """Test creating past and future exams and retrieving upcoming exams."""
    user_id = "user_exam_001"
    now = datetime.now(timezone.utc)

    # 1. Past exam (5 days ago)
    ExamService.create_exam(
        db=db_session,
        user_id=user_id,
        request=ExamCreateRequest(
            subject_id="operating_systems",
            title="OS Past Exam",
            exam_date=now - timedelta(days=5),
        ),
    )

    # 2. Future exam (10 days in future)
    future_exam = ExamService.create_exam(
        db=db_session,
        user_id=user_id,
        request=ExamCreateRequest(
            subject_id="operating_systems",
            title="OS Midterm",
            exam_date=now + timedelta(days=10),
        ),
    )

    # All exams
    all_exams = ExamService.get_exams(db=db_session, user_id=user_id)
    assert len(all_exams) == 2

    # Upcoming exams
    upcoming = ExamService.get_upcoming_exams(db=db_session, user_id=user_id)
    assert len(upcoming) == 1
    assert upcoming[0].exam_id == future_exam.exam_id
    assert upcoming[0].title == "OS Midterm"


def test_exam_proximity_focus_rules():
    """Test deterministic proximity rules: >14d, 7-14d, 3-7d, <=2d."""
    now = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Case 1: 20 days (>14d) -> 'normal'
    date_20d = now + timedelta(days=20)
    days, focus = ExamService.calculate_exam_focus(date_20d, current_time=now)
    assert days == 20
    assert focus == "normal"

    # Case 2: 10 days (7-14d) -> 'increased'
    date_10d = now + timedelta(days=10)
    days, focus = ExamService.calculate_exam_focus(date_10d, current_time=now)
    assert days == 10
    assert focus == "increased"

    # Case 3: 4 days (3-7d) -> 'targeted_weak_topic'
    date_4d = now + timedelta(days=4)
    days, focus = ExamService.calculate_exam_focus(date_4d, current_time=now)
    assert days == 4
    assert focus == "targeted_weak_topic"

    # Case 4: 1 day (<=2d) -> 'revision_and_targeted'
    date_1d = now + timedelta(days=1)
    days, focus = ExamService.calculate_exam_focus(date_1d, current_time=now)
    assert days == 1
    assert focus == "revision_and_targeted"


def test_configurable_exam_thresholds():
    """Test dynamically configuring exam proximity threshold windows."""
    now = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    date_5d = now + timedelta(days=5)

    # Default: 5 days is within 3-7d window -> 'targeted_weak_topic'
    _, focus_default = ExamService.calculate_exam_focus(date_5d, current_time=now)
    assert focus_default == "targeted_weak_topic"

    # Temporarily change thresholds
    orig_normal = settings.assessment.exam_normal_days
    orig_increased = settings.assessment.exam_increased_days
    orig_weak = settings.assessment.exam_weak_topic_days
    orig_rev = settings.assessment.exam_revision_days

    try:
        settings.assessment.exam_normal_days = 30
        settings.assessment.exam_increased_days = 20
        settings.assessment.exam_weak_topic_days = 10
        settings.assessment.exam_revision_days = 5

        # Under new config, 5 days is <= revision threshold (5d) -> 'revision_and_targeted'
        _, focus_custom = ExamService.calculate_exam_focus(date_5d, current_time=now)
        assert focus_custom == "revision_and_targeted"
    finally:
        settings.assessment.exam_normal_days = orig_normal
        settings.assessment.exam_increased_days = orig_increased
        settings.assessment.exam_weak_topic_days = orig_weak
        settings.assessment.exam_revision_days = orig_rev
