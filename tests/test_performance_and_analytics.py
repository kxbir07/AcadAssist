"""Tests for performance metrics, topic accuracy, mastery, and weak/strong topic detection."""

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.assessment.services.quiz_service import quiz_service
from app.assessment.models import Question
from app.assessment.schemas import SubmittedAnswer
from app.core.config import settings


def test_performance_metrics_and_topic_mastery(db_session: Session):
    """Test performance analytics across multiple topics and difficulties."""
    user_id = "user_perf_001"

    # Quiz 1: Paging (4 questions, 1 correct -> 25% mastery)
    quiz_1 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Paging"],
        difficulty="easy",
        count=4,
    )
    db_q1 = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_1.quiz_id)
    ).scalars().all()
    ans_1 = [
        SubmittedAnswer(question_id=db_q1[0].question_id, selected_answer=db_q1[0].correct_answer),
        SubmittedAnswer(question_id=db_q1[1].question_id, selected_answer="Wrong"),
        SubmittedAnswer(question_id=db_q1[2].question_id, selected_answer="Wrong"),
        SubmittedAnswer(question_id=db_q1[3].question_id, selected_answer="Wrong"),
    ]
    quiz_service.submit_quiz(db=db_session, user_id=user_id, quiz_id=quiz_1.quiz_id, answers=ans_1)

    # Quiz 2: CPU Scheduling (4 questions, 4 correct -> 100% mastery)
    quiz_2 = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["CPU Scheduling"],
        difficulty="medium",
        count=4,
    )
    db_q2 = db_session.execute(
        select(Question).where(Question.quiz_id == quiz_2.quiz_id)
    ).scalars().all()
    ans_2 = [
        SubmittedAnswer(question_id=q.question_id, selected_answer=q.correct_answer)
        for q in db_q2
    ]
    quiz_service.submit_quiz(db=db_session, user_id=user_id, quiz_id=quiz_2.quiz_id, answers=ans_2)

    # Evaluate performance
    perf = quiz_service.get_performance(db=db_session, user_id=user_id)

    assert perf.attempt_count == 2
    assert perf.total_questions_attempted == 8
    assert perf.total_correct == 5
    assert perf.total_incorrect == 3
    assert perf.overall_accuracy == 62.5

    # Difficulty accuracy checks
    assert "easy" in perf.difficulty_accuracy
    assert perf.difficulty_accuracy["easy"] >= 0.0

    # Recent accuracy checks
    assert perf.recent_accuracy == 62.5

    # Topic accuracy checks
    assert perf.topic_accuracy["Paging"] == 25.0
    assert perf.topic_accuracy["CPU Scheduling"] == 100.0

    # Topic mastery checks
    assert perf.topic_mastery["Paging"] == 0.25
    assert perf.topic_mastery["CPU Scheduling"] == 1.0

    # Weak & Strong topic detection
    weak_topic_names = [wt.topic for wt in perf.weak_topics]
    strong_topic_names = [st.topic for st in perf.strong_topics]

    assert "Paging" in weak_topic_names
    assert "CPU Scheduling" in strong_topic_names


def test_weak_topics_api_service(db_session: Session):
    """Test dedicated get_weak_topics query."""
    user_id = "user_perf_weak"

    quiz = quiz_service.generate_quiz(
        db=db_session,
        user_id=user_id,
        subject_id="operating_systems",
        topic_ids=["Deadlocks"],
        count=3,
    )
    db_q = db_session.execute(
        select(Question).where(Question.quiz_id == quiz.quiz_id)
    ).scalars().all()
    # All wrong answers
    ans = [SubmittedAnswer(question_id=q.question_id, selected_answer="Wrong") for q in db_q]
    quiz_service.submit_quiz(db=db_session, user_id=user_id, quiz_id=quiz.quiz_id, answers=ans)

    weak_res = quiz_service.get_weak_topics(db=db_session, user_id=user_id)
    assert len(weak_res.topics) == 1
    assert weak_res.topics[0].topic == "Deadlocks"
    assert weak_res.topics[0].mastery == 0.0


def test_empty_performance_state(db_session: Session):
    """Test that querying performance for a user with no attempts returns clean empty state."""
    user_id = "user_newbie"
    perf = quiz_service.get_performance(db=db_session, user_id=user_id)

    assert perf.attempt_count == 0
    assert perf.overall_accuracy == 0.0
    assert perf.total_questions_attempted == 0
    assert perf.topic_accuracy == {}
    assert perf.weak_topics == []
    assert perf.strong_topics == []
