"""Person 3 assessment data consumer boundary.

Person 3 owns assessment, quizzes, question attempts, exams, scoring, and weak-topic detection.
Person 4 does NOT calculate quiz scores, generate questions, or evaluate quiz logic.
This module cleanly queries Person 3's authoritative records from the shared database.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.shared import Course, Exam, QuizAttempt, Subject, Topic, TopicMastery


class Person3AssessmentConsumer:
    """Interface consuming Person 3's authoritative assessment and academic performance data."""

    @staticmethod
    def get_user_topic_mastery(
        db: Session,
        user_id: str,
        topic_id: Optional[str] = None,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
    ) -> List[TopicMastery]:
        """Fetch authoritative topic mastery records produced by Person 3."""
        query = db.query(TopicMastery).filter(TopicMastery.user_id == user_id)
        if topic_id:
            query = query.filter(TopicMastery.topic_id == topic_id)
        if course_id or subject_id:
            query = query.join(Topic, TopicMastery.topic_id == Topic.topic_id)
            if course_id:
                query = query.filter(Topic.course_id == course_id)
            if subject_id:
                query = query.filter(Topic.subject_id == subject_id)
        return query.all()

    @staticmethod
    def get_weak_topics(
        db: Session,
        user_id: str,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch weak topics identified by Person 3 (mastery < weak threshold or marked weak)."""
        threshold = settings.WEAK_MASTERY_THRESHOLD
        query = (
            db.query(TopicMastery, Topic)
            .join(Topic, TopicMastery.topic_id == Topic.topic_id)
            .filter(TopicMastery.user_id == user_id)
            .filter((TopicMastery.mastery_percentage < threshold) | (TopicMastery.is_weak.is_(True)))
        )
        if course_id:
            query = query.filter(Topic.course_id == course_id)
        if subject_id:
            query = query.filter(Topic.subject_id == subject_id)

        results = []
        for mastery, topic in query.all():
            results.append({
                "topic_id": topic.topic_id,
                "topic_name": topic.name,
                "course_id": topic.course_id,
                "subject_id": topic.subject_id,
                "mastery_percentage": mastery.mastery_percentage,
                "is_weak": True,
                "quizzes_attempted": mastery.quizzes_attempted,
            })
        return results

    @staticmethod
    def get_strong_topics(
        db: Session,
        user_id: str,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch strong topics (mastery >= strong threshold)."""
        threshold = settings.STRONG_MASTERY_THRESHOLD
        query = (
            db.query(TopicMastery, Topic)
            .join(Topic, TopicMastery.topic_id == Topic.topic_id)
            .filter(TopicMastery.user_id == user_id)
            .filter(TopicMastery.mastery_percentage >= threshold)
        )
        if course_id:
            query = query.filter(Topic.course_id == course_id)
        if subject_id:
            query = query.filter(Topic.subject_id == subject_id)

        results = []
        for mastery, topic in query.all():
            results.append({
                "topic_id": topic.topic_id,
                "topic_name": topic.name,
                "course_id": topic.course_id,
                "subject_id": topic.subject_id,
                "mastery_percentage": mastery.mastery_percentage,
                "is_strong": True,
            })
        return results

    @staticmethod
    def get_quiz_accuracy(
        db: Session,
        user_id: str,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> float:
        """Calculate average quiz score for the user from Person 3's QuizAttempt table."""
        query = db.query(func.avg(QuizAttempt.score_percentage)).filter(QuizAttempt.user_id == user_id)
        if since:
            query = query.filter(QuizAttempt.completed_at >= since)
        if until:
            query = query.filter(QuizAttempt.completed_at <= until)
        if course_id or subject_id:
            query = query.join(Topic, QuizAttempt.topic_id == Topic.topic_id)
            if course_id:
                query = query.filter(Topic.course_id == course_id)
            if subject_id:
                query = query.filter(Topic.subject_id == subject_id)

        result = query.scalar()
        return round(float(result), 2) if result is not None else 0.0

    @staticmethod
    def get_upcoming_exams(
        db: Session,
        user_id: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
    ) -> List[Exam]:
        """Query real upcoming exams from the shared database."""
        today = from_date or date.today()
        query = db.query(Exam).filter(Exam.user_id == user_id, Exam.exam_date >= today)
        if to_date:
            query = query.filter(Exam.exam_date <= to_date)
        if course_id:
            query = query.filter(Exam.course_id == course_id)
        if subject_id:
            query = query.filter(Exam.subject_id == subject_id)
        return query.order_by(Exam.exam_date.asc()).all()

    @staticmethod
    def get_all_topics(
        db: Session,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
    ) -> List[Topic]:
        """Fetch topics for course/subject scope."""
        query = db.query(Topic)
        if course_id:
            query = query.filter(Topic.course_id == course_id)
        if subject_id:
            query = query.filter(Topic.subject_id == subject_id)
        return query.all()


person3_consumer = Person3AssessmentConsumer()
