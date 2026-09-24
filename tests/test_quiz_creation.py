"""Tests for Quiz creation, question generation, and quiz retrieval."""

import pytest
from sqlalchemy.orm import Session
from app.assessment.services.quiz_service import quiz_service
from app.assessment.models import Quiz, Question
from app.assessment.exceptions import QuizNotFoundError


def test_quiz_and_question_creation(db_session: Session):
    """Test creating a quiz with questions and verifying database persistence."""
    user_id = "user_test_001"
    quiz = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        difficulty="medium",
        count=5,
    )

    assert quiz.quiz_id is not None
    assert quiz.user_id == user_id
    assert quiz.subject_id == "operating_systems"
    assert quiz.difficulty == "medium"
    assert quiz.question_count == 5
    assert len(quiz.questions) == 5

    # Verify each question fields
    for q in quiz.questions:
        assert q.question_id is not None
        assert q.quiz_id == quiz.quiz_id
        assert q.question_text is not None
        assert len(q.options) >= 2
        assert q.topic_id == "Paging"


def test_quiz_retrieval(db_session: Session):
    """Test retrieving a quiz by ID."""
    user_id = "user_test_002"
    created = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["TLB"],
        difficulty="easy",
        count=3,
    )

    retrieved = quiz_service.get_quiz_by_id(
        db=db_session,
        user_id=user_id,
        quiz_id=created.quiz_id,
    )

    assert retrieved.quiz_id == created.quiz_id
    assert retrieved.user_id == user_id
    assert len(retrieved.questions) == 3


def test_quiz_retrieval_not_found(db_session: Session):
    """Test that retrieving a non-existent quiz raises QuizNotFoundError."""
    with pytest.raises(QuizNotFoundError):
        quiz_service.get_quiz_by_id(
            db=db_session,
            user_id="user_any",
            quiz_id="non_existent_quiz_uuid",
        )
