"""Tests for strict multi-user tenant isolation across all assessment operations."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.assessment.services.quiz_service import quiz_service
from app.assessment.services.exam_service import ExamService
from app.assessment.schemas import SubmittedAnswer, ExamCreateRequest
from app.assessment.exceptions import QuizAccessDeniedError
from app.assessment.models import Question
from sqlalchemy import select


def test_user_isolation_quizzes(db_session: Session):
    """Verify that a user cannot access another user's quiz."""
    user_1 = "student_alpha"
    user_2 = "student_beta"

    quiz_1 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_1,
        subject_id="operating_systems",
        count=3,
    )

    # student_1 can access
    assert quiz_service.get_quiz_by_id(db=db_session, user_id=user_1, quiz_id=quiz_1.quiz_id) is not None

    # student_2 is blocked
    with pytest.raises(QuizAccessDeniedError):
        quiz_service.get_quiz_by_id(db=db_session, user_id=user_2, quiz_id=quiz_1.quiz_id)


def test_user_isolation_performance(db_session: Session):
    """Verify performance metrics are isolated between users."""
    user_1 = "student_alpha"
    user_2 = "student_beta"

    # student_1 generates and submits quiz with 100% score
    quiz_1 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_1,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        count=3,
    )
    questions = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_1.quiz_id)
    ).scalars().all()
    answers = [SubmittedAnswer(question_id=q.question_id, selected_answer=q.correct_answer) for q in questions]
    quiz_service.submit_quiz(db=db_session, user_id=user_1, quiz_id=quiz_1.quiz_id, answers=answers)

    # Check student_1 metrics
    perf_1 = quiz_service.get_performance(db=db_session, user_id=user_1)
    assert perf_1.attempt_count == 1
    assert perf_1.overall_accuracy == 100.0

    # Check student_2 metrics (must be completely empty)
    perf_2 = quiz_service.get_performance(db=db_session, user_id=user_2)
    assert perf_2.attempt_count == 0
    assert perf_2.overall_accuracy == 0.0
    assert perf_2.total_questions_attempted == 0


def test_user_isolation_exams(db_session: Session):
    """Verify exam schedules are isolated between users."""
    user_1 = "student_alpha"
    user_2 = "student_beta"

    exam_date = datetime.now(timezone.utc) + timedelta(days=5)
    ExamService.create_exam(
        db=db_session,
        user_id=user_1,
        request=ExamCreateRequest(subject_id="operating_systems", title="OS Midterm", exam_date=exam_date),
    )

    exams_1 = ExamService.get_exams(db=db_session, user_id=user_1)
    assert len(exams_1) == 1

    exams_2 = ExamService.get_exams(db=db_session, user_id=user_2)
    assert len(exams_2) == 0
