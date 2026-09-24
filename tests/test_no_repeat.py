"""Tests for deterministic per-user no-repeat question filtering and pool exhaustion."""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.assessment.services.quiz_service import QuizService
from app.assessment.services.question_generator import DeterministicQuestionGenerator
from app.assessment.models import Question
from app.assessment.schemas import SubmittedAnswer
from app.assessment.exceptions import InsufficientQuestionsError


def test_no_repeat_after_quiz_submission(db_session: Session):
    """Test that submitted questions are not repeated in subsequent quizzes for the same user."""
    user_id = "user_norepeat_001"
    service = QuizService()

    # Generate Quiz 1 (5 questions on Paging)
    quiz_1 = service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        count=5,
    )

    q_ids_1 = {q.question_id for q in quiz_1.questions}
    q_texts_1 = {q.question_text.strip().lower() for q in quiz_1.questions}

    # Submit Quiz 1 to record QuestionAttempts
    db_questions_1 = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_1.quiz_id)
    ).scalars().all()

    answers_1 = [
        SubmittedAnswer(question_id=q.question_id, selected_answer=q.correct_answer)
        for q in db_questions_1
    ]
    service.submit_quiz(db=db_session, user_id=user_id, quiz_id=quiz_1.quiz_id, answers=answers_1)

    # Generate Quiz 2 for the same user (5 questions on Paging)
    quiz_2 = service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        count=5,
    )

    q_ids_2 = {q.question_id for q in quiz_2.questions}
    q_texts_2 = {q.question_text.strip().lower() for q in quiz_2.questions}

    # Ensure zero overlap between Quiz 1 and Quiz 2
    assert len(q_ids_1.intersection(q_ids_2)) == 0
    assert len(q_texts_1.intersection(q_texts_2)) == 0


def test_no_repeat_is_per_user_not_global(db_session: Session):
    """Verify that User A attempting questions does not lock out User B from receiving those questions."""
    user_a = "user_norepeat_a"
    user_b = "user_norepeat_b"
    service = QuizService()

    # User A generates and completes Quiz
    quiz_a = service.generate_quiz(
        db=db_session,
        user_id=user_a,
        subject_id="operating_systems",
        topic_ids=["TLB"],
        count=3,
    )
    db_q_a = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_a.quiz_id)
    ).scalars().all()
    answers_a = [SubmittedAnswer(question_id=q.question_id, selected_answer=q.correct_answer) for q in db_q_a]
    service.submit_quiz(db=db_session, user_id=user_a, quiz_id=quiz_a.quiz_id, answers=answers_a)

    # User B generates Quiz on same topic
    quiz_b = service.generate_quiz(
        db=db_session,
        user_id=user_b,
        subject_id="operating_systems",
        topic_ids=["TLB"],
        count=3,
    )

    # User B should receive valid questions
    assert len(quiz_b.questions) == 3


def test_question_pool_exhaustion_handling(db_session: Session):
    """Test that when a fixed question bank is completely exhausted, InsufficientQuestionsError is raised."""
    small_bank = [
        {
            "question_id": f"q_fixed_{i}",
            "subject_id": "math",
            "topic_id": "Algebra",
            "difficulty": "easy",
            "question_text": f"What is 2 + {i}?",
            "question_type": "multiple_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "B",
        }
        for i in range(3)
    ]

    class StaticGenerator(DeterministicQuestionGenerator):
        def generate_candidate_questions(self, subject_id, topic_ids=None, difficulty="medium", count=10):
            return [dict(q) for q in small_bank]

    custom_service = QuizService(question_generator=StaticGenerator())
    user_id = "user_exhaustion_001"

    # User generates and completes all 3 questions
    quiz_1 = custom_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="math",
        topic_ids=["Algebra"],
        count=3,
    )

    db_q = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_1.quiz_id)
    ).scalars().all()
    answers = [SubmittedAnswer(question_id=q.question_id, selected_answer=q.correct_answer) for q in db_q]
    custom_service.submit_quiz(db=db_session, user_id=user_id, quiz_id=quiz_1.quiz_id, answers=answers)

    # Attempting to generate another quiz of 2 questions from exhausted pool raises InsufficientQuestionsError
    with pytest.raises(InsufficientQuestionsError):
        custom_service.generate_quiz(
            db=db_session,
            user_id=user_id,
            subject_id="math",
            topic_ids=["Algebra"],
            count=2,
        )
