"""Tests for adaptive difficulty logic and configurable thresholds."""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.assessment.services.quiz_service import quiz_service
from app.assessment.services.adaptive_difficulty_service import AdaptiveDifficultyService
from app.assessment.models import Question
from app.assessment.schemas import SubmittedAnswer
from app.core.config import settings


def test_adaptive_difficulty_below_50_percent(db_session: Session):
    """Test that student scoring below 50% receives 'easy' difficulty in next quiz."""
    user_id = "user_adapt_low"

    # 1. First quiz
    quiz_1 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        difficulty="medium",
        count=4,
    )

    db_q = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_1.quiz_id)
    ).scalars().all()

    # Answer only 1 out of 4 correct (25% accuracy)
    answers = [
        SubmittedAnswer(
            question_id=db_q[0].question_id,
            selected_answer=db_q[0].correct_answer,
        ),
        SubmittedAnswer(
            question_id=db_q[1].question_id,
            selected_answer="Wrong answer",
        ),
        SubmittedAnswer(
            question_id=db_q[2].question_id,
            selected_answer="Wrong answer",
        ),
        SubmittedAnswer(
            question_id=db_q[3].question_id,
            selected_answer="Wrong answer",
        ),
    ]

    quiz_service.submit_quiz(db=db_session, user_id=user_id, quiz_id=quiz_1.quiz_id, answers=answers)

    # 2. Next generated quiz should automatically adapt to 'easy'
    quiz_2 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        count=4,
    )

    assert quiz_2.difficulty == "easy"


def test_adaptive_difficulty_50_to_75_percent(db_session: Session):
    """Test that student scoring between 50% and 75% receives 'medium' difficulty."""
    user_id = "user_adapt_mid"

    quiz_1 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["TLB"],
        difficulty="easy",
        count=4,
    )

    db_q = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_1.quiz_id)
    ).scalars().all()

    # Answer 2 out of 4 correct (50.0% accuracy)
    answers = [
        SubmittedAnswer(question_id=db_q[0].question_id, selected_answer=db_q[0].correct_answer),
        SubmittedAnswer(question_id=db_q[1].question_id, selected_answer=db_q[1].correct_answer),
        SubmittedAnswer(question_id=db_q[2].question_id, selected_answer="Wrong answer"),
        SubmittedAnswer(question_id=db_q[3].question_id, selected_answer="Wrong answer"),
    ]

    quiz_service.submit_quiz(db=db_session, user_id=user_id, quiz_id=quiz_1.quiz_id, answers=answers)

    quiz_2 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["TLB"],
        count=4,
    )

    assert quiz_2.difficulty == "medium"


def test_adaptive_difficulty_above_75_percent(db_session: Session):
    """Test that student scoring above 75% receives 'hard' difficulty."""
    user_id = "user_adapt_high"

    quiz_1 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Virtual Memory"],
        difficulty="medium",
        count=4,
    )

    db_q = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_1.quiz_id)
    ).scalars().all()

    # Answer all 4 correct (100% accuracy)
    answers = [
        SubmittedAnswer(question_id=q.question_id, selected_answer=q.correct_answer)
        for q in db_q
    ]

    quiz_service.submit_quiz(db=db_session, user_id=user_id, quiz_id=quiz_1.quiz_id, answers=answers)

    quiz_2 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Virtual Memory"],
        count=4,
    )

    assert quiz_2.difficulty == "hard"


def test_configurable_adaptive_thresholds():
    """Test that changing threshold configurations dynamically adjusts difficulty determination."""
    # Test with default thresholds (50, 75)
    assert AdaptiveDifficultyService.determine_difficulty(45.0) == "easy"
    assert AdaptiveDifficultyService.determine_difficulty(60.0) == "medium"
    assert AdaptiveDifficultyService.determine_difficulty(80.0) == "hard"

    # Temporarily override thresholds
    original_easy = settings.assessment.adaptive_easy_threshold
    original_hard = settings.assessment.adaptive_hard_threshold

    try:
        settings.assessment.adaptive_easy_threshold = 40.0
        settings.assessment.adaptive_hard_threshold = 60.0

        assert AdaptiveDifficultyService.determine_difficulty(35.0) == "easy"
        assert AdaptiveDifficultyService.determine_difficulty(45.0) == "medium"  # Now medium because > 40.0
        assert AdaptiveDifficultyService.determine_difficulty(65.0) == "hard"    # Now hard because > 60.0
    finally:
        settings.assessment.adaptive_easy_threshold = original_easy
        settings.assessment.adaptive_hard_threshold = original_hard
