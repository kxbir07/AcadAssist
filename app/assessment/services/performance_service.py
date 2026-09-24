"""Performance analytics and topic mastery service for Person 3 Assessment Subsystem.

Calculates deterministic assessment metrics, overall/topic/difficulty accuracies,
recent performance trends, and weak/strong topic classifications.
"""

from typing import Optional, List, Dict, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.assessment.models import QuizAttempt, QuestionAttempt, Question, Quiz
from app.assessment.schemas import (
    PerformanceMetricsResponse,
    WeakTopicItem,
    StrongTopicItem,
    WeakTopicsResponse,
)
from app.core.config import settings


class PerformanceService:
    """Deterministic assessment performance analytics service."""

    @classmethod
    def get_performance_metrics(
        cls,
        db: Session,
        user_id: str,
        subject_id: Optional[str] = None,
        recent_limit: int = 20,
    ) -> PerformanceMetricsResponse:
        """Calculate comprehensive performance metrics for a user."""
        # 1. Total quiz attempts count
        attempt_query = select(func.count(QuizAttempt.attempt_id)).where(
            QuizAttempt.user_id == user_id
        )
        if subject_id:
            attempt_query = attempt_query.join(Quiz, QuizAttempt.quiz_id == Quiz.quiz_id).where(
                Quiz.subject_id == subject_id
            )
        attempt_count = db.execute(attempt_query).scalar() or 0

        # 2. Base question attempt query with joined Question for metadata
        stmt = (
            select(
                QuestionAttempt.is_correct,
                Question.topic_id,
                Question.difficulty,
                QuestionAttempt.attempted_at,
            )
            .join(Question, QuestionAttempt.question_id == Question.question_id)
            .where(QuestionAttempt.user_id == user_id)
        )
        if subject_id:
            stmt = stmt.where(Question.subject_id == subject_id)

        rows = db.execute(stmt).all()

        total_questions = len(rows)
        if total_questions == 0:
            return PerformanceMetricsResponse(
                user_id=user_id,
                subject_id=subject_id,
                overall_accuracy=0.0,
                topic_accuracy={},
                difficulty_accuracy={},
                recent_accuracy=0.0,
                attempt_count=attempt_count,
                total_questions_attempted=0,
                total_correct=0,
                total_incorrect=0,
                topic_mastery={},
                weak_topics=[],
                strong_topics=[],
            )

        total_correct = sum(1 for r in rows if r[0])
        total_incorrect = total_questions - total_correct
        overall_accuracy = round((total_correct / total_questions) * 100.0, 2)

        # 3. Topic breakdown
        topic_totals: Dict[str, int] = {}
        topic_corrects: Dict[str, int] = {}

        for is_corr, topic_id, _, _ in rows:
            topic_totals[topic_id] = topic_totals.get(topic_id, 0) + 1
            if is_corr:
                topic_corrects[topic_id] = topic_corrects.get(topic_id, 0) + 1

        topic_accuracy: Dict[str, float] = {}
        topic_mastery: Dict[str, float] = {}
        weak_topics: List[WeakTopicItem] = []
        strong_topics: List[StrongTopicItem] = []

        for topic_id, total in topic_totals.items():
            corr = topic_corrects.get(topic_id, 0)
            acc = round((corr / total) * 100.0, 2)
            mastery = round(corr / total, 2)

            topic_accuracy[topic_id] = acc
            topic_mastery[topic_id] = mastery

            if mastery < settings.assessment.weak_topic_threshold:
                weak_topics.append(
                    WeakTopicItem(topic_id=topic_id, topic=topic_id, mastery=mastery)
                )
            if mastery >= settings.assessment.strong_topic_threshold:
                strong_topics.append(
                    StrongTopicItem(topic_id=topic_id, topic=topic_id, mastery=mastery)
                )

        # Sort weak topics ascending by mastery (weakest first)
        weak_topics.sort(key=lambda item: item.mastery)
        # Sort strong topics descending by mastery (strongest first)
        strong_topics.sort(key=lambda item: item.mastery, reverse=True)

        # 4. Difficulty breakdown
        diff_totals: Dict[str, int] = {}
        diff_corrects: Dict[str, int] = {}

        for is_corr, _, difficulty, _ in rows:
            diff_totals[difficulty] = diff_totals.get(difficulty, 0) + 1
            if is_corr:
                diff_corrects[difficulty] = diff_corrects.get(difficulty, 0) + 1

        difficulty_accuracy: Dict[str, float] = {}
        for diff, total in diff_totals.items():
            corr = diff_corrects.get(diff, 0)
            difficulty_accuracy[diff] = round((corr / total) * 100.0, 2)

        # 5. Recent accuracy (last N questions)
        recent_rows = sorted(rows, key=lambda r: r[3], reverse=True)[:recent_limit]
        recent_correct = sum(1 for r in recent_rows if r[0])
        recent_accuracy = (
            round((recent_correct / len(recent_rows)) * 100.0, 2) if recent_rows else 0.0
        )

        return PerformanceMetricsResponse(
            user_id=user_id,
            subject_id=subject_id,
            overall_accuracy=overall_accuracy,
            topic_accuracy=topic_accuracy,
            difficulty_accuracy=difficulty_accuracy,
            recent_accuracy=recent_accuracy,
            attempt_count=attempt_count,
            total_questions_attempted=total_questions,
            total_correct=total_correct,
            total_incorrect=total_incorrect,
            topic_mastery=topic_mastery,
            weak_topics=weak_topics,
            strong_topics=strong_topics,
        )

    @classmethod
    def get_weak_topics(
        cls,
        db: Session,
        user_id: str,
        subject_id: Optional[str] = None,
    ) -> WeakTopicsResponse:
        """Retrieve detected weak topics for a student."""
        metrics = cls.get_performance_metrics(db, user_id=user_id, subject_id=subject_id)
        return WeakTopicsResponse(topics=metrics.weak_topics)
