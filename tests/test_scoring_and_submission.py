"""Tests for scoring, submission evaluation, attempt recording, and error validation."""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.assessment.services.quiz_service import quiz_service
from app.assessment.models import QuizAttempt, QuestionAttempt, Question
from app.assessment.schemas import SubmittedAnswer
from app.assessment.exceptions import (
    QuizAlreadySubmittedError,
    QuizAccessDeniedError,
    InvalidQuestionSubmissionError,
)


def test_scoring_and_submission_all_correct(db_session: Session):
    """Test submitting a quiz where all answers are correct."""
    user_id = "user_score_001"
    quiz_res = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        difficulty="easy",
        count=3,
    )

    # Fetch stored questions with correct_answer
    db_questions = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_res.quiz_id)
    ).scalars().all()

    answers = [
        SubmittedAnswer(
            question_id=q.question_id,
            selected_answer=q.correct_answer,
            time_taken=12.5,
        )
        for q in db_questions
    ]

    result = quiz_service.submit_quiz(
        db=db_session,
        user_id=user_id,
        quiz_id=quiz_res.quiz_id,
        answers=answers,
    )

    assert result.score == 3
    assert result.total == 3
    assert result.percentage == 100.0
    assert result.completed_at is not None

    # Verify QuizAttempt in DB
    quiz_attempt = db_session.execute(
        select(QuizAttempt).where(QuizAttempt.attempt_id == result.attempt_id)
    ).scalar_one()
    assert quiz_attempt.score == 3
    assert quiz_attempt.user_id == user_id

    # Verify QuestionAttempts in DB
    q_attempts = db_session.execute(
        select(QuestionAttempt).where(QuestionAttempt.attempt_id == result.attempt_id)
    ).scalars().all()
    assert len(q_attempts) == 3
    for qa in q_attempts:
        assert qa.is_correct is True
        assert qa.time_taken == 12.5


def test_scoring_mixed_answers(db_session: Session):
    """Test submitting a quiz with some correct and some incorrect answers."""
    user_id = "user_score_002"
    quiz_res = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        difficulty="medium",
        count=4,
    )

    db_questions = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_res.quiz_id)
    ).scalars().all()

    # Make 2 correct, 2 incorrect
    answers = []
    for i, q in enumerate(db_questions):
        if i < 2:
            ans = q.correct_answer
        else:
            ans = "Wrong Answer Text"
        answers.append(SubmittedAnswer(question_id=q.question_id, selected_answer=ans, time_taken=10.0))

    result = quiz_service.submit_quiz(
        db=db_session,
        user_id=user_id,
        quiz_id=quiz_res.quiz_id,
        answers=answers,
    )

    assert result.score == 2
    assert result.total == 4
    assert result.percentage == 50.0


def test_duplicate_submission_prevention(db_session: Session):
    """Test that attempting to submit an already completed quiz is rejected."""
    user_id = "user_score_003"
    quiz_res = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        difficulty="easy",
        count=2,
    )

    db_questions = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_res.quiz_id)
    ).scalars().all()

    answers = [
        SubmittedAnswer(question_id=q.question_id, selected_answer=q.correct_answer)
        for q in db_questions
    ]

    # First submission succeeds
    quiz_service.submit_quiz(
        db=db_session,
        user_id=user_id,
        quiz_id=quiz_res.quiz_id,
        answers=answers,
    )

    # Second submission fails with QuizAlreadySubmittedError
    with pytest.raises(QuizAlreadySubmittedError):
        quiz_service.submit_quiz(
            db=db_session,
            user_id=user_id,
            quiz_id=quiz_res.quiz_id,
            answers=answers,
        )


def test_unauthorized_quiz_submission(db_session: Session):
    """Test that User B cannot submit User A's quiz."""
    user_a = "user_a"
    user_b = "user_b"

    quiz_res = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_a,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        difficulty="easy",
        count=2,
    )

    db_questions = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_res.quiz_id)
    ).scalars().all()

    answers = [
        SubmittedAnswer(question_id=q.question_id, selected_answer=q.correct_answer)
        for q in db_questions
    ]

    with pytest.raises(QuizAccessDeniedError):
        quiz_service.submit_quiz(
            db=db_session,
            user_id=user_b,
            quiz_id=quiz_res.quiz_id,
            answers=answers,
        )


def test_invalid_question_id_submission(db_session: Session):
    """Test that submitting an answer for a question not belonging to the quiz raises error."""
    user_id = "user_score_004"
    quiz_res = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        difficulty="easy",
        count=2,
    )

    answers = [
        SubmittedAnswer(question_id="invalid-uuid-1234", selected_answer="Some Answer")
    ]

    with pytest.raises(InvalidQuestionSubmissionError):
        quiz_service.submit_quiz(
            db=db_session,
            user_id=user_id,
            quiz_id=quiz_res.quiz_id,
            answers=answers,
        )
