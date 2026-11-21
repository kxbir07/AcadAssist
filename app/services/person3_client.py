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
from app.assessment.models import Question, QuestionAttempt


class Person3AssessmentConsumer:
    """Interface consuming Person 3's authoritative assessment and academic performance data."""

    @staticmethod
    def _synthesize_question_attempt_masteries(
        db: Session,
        user_id: str,
        existing_topic_ids: set[str],
        topic_id: Optional[str] = None,
        course_id: Optional[str] = None,
        subject_id: Optional[str] = None,
    ) -> List[TopicMastery]:
        """Synthesize TopicMastery objects from QuestionAttempt records for topics not already in TopicMastery."""
        try:
            q = (
                db.query(QuestionAttempt, Question)
                .join(Question, QuestionAttempt.question_id == Question.question_id)
                .filter(QuestionAttempt.user_id == user_id)
            )
            rows = q.all()
        except Exception:
            return []

        stats: Dict[str, Dict[str, Any]] = {}
        for qa, quest in rows:
            tid = quest.topic_id
            if not tid or tid in existing_topic_ids:
                continue
            if topic_id and tid != topic_id:
                continue
            if subject_id and quest.subject_id != subject_id:
                continue
            if tid not in stats:
                stats[tid] = {"total": 0, "correct": 0, "subject_id": quest.subject_id, "last_at": qa.attempted_at}
            stats[tid]["total"] += 1
            if qa.is_correct:
                stats[tid]["correct"] += 1
            if qa.attempted_at and (stats[tid]["last_at"] is None or qa.attempted_at > stats[tid]["last_at"]):
                stats[tid]["last_at"] = qa.attempted_at

        synthesized: List[TopicMastery] = []
        for tid, st in stats.items():
            pct = round((st["correct"] / st["total"]) * 100.0, 2) if st["total"] > 0 else 0.0
            synthesized.append(
                TopicMastery(
                    id=f"synth-{user_id}-{tid}",
                    user_id=user_id,
                    topic_id=tid,
                    mastery_percentage=pct,
                    quizzes_attempted=1,
                    quizzes_passed=1 if pct >= settings.MASTERY_COMPLETION_THRESHOLD else 0,
                    is_weak=pct < settings.WEAK_MASTERY_THRESHOLD,
                    is_completed=pct >= settings.MASTERY_COMPLETION_THRESHOLD,
                    last_assessed_at=st["last_at"],
                )
            )
        return synthesized

    @classmethod
    def get_user_topic_mastery(
        cls,
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
        explicit = list(query.all())
        existing_ids = {m.topic_id for m in explicit}
        synth = cls._synthesize_question_attempt_masteries(
            db, user_id, existing_ids, topic_id=topic_id, course_id=course_id, subject_id=subject_id
        )
        return explicit + synth

    @classmethod
    def get_weak_topics(
        cls,
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
        seen_topic_ids = set()
        for mastery, topic in query.all():
            seen_topic_ids.add(topic.topic_id)
            results.append({
                "topic_id": topic.topic_id,
                "topic_name": topic.name,
                "course_id": topic.course_id,
                "subject_id": topic.subject_id,
                "mastery_percentage": mastery.mastery_percentage,
                "is_weak": True,
                "quizzes_attempted": mastery.quizzes_attempted,
            })

        # Also include any weak topics from QuestionAttempt records
        synth = cls._synthesize_question_attempt_masteries(
            db, user_id, seen_topic_ids, course_id=course_id, subject_id=subject_id
        )
        for sm in synth:
            if sm.mastery_percentage < threshold or sm.is_weak:
                results.append({
                    "topic_id": sm.topic_id,
                    "topic_name": sm.topic_id,
                    "course_id": course_id or "cs",
                    "subject_id": subject_id or "operating_systems",
                    "mastery_percentage": sm.mastery_percentage,
                    "is_weak": True,
                    "quizzes_attempted": sm.quizzes_attempted,
                })
        return results

    @classmethod
    def get_strong_topics(
        cls,
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
        seen_topic_ids = set()
        for mastery, topic in query.all():
            seen_topic_ids.add(topic.topic_id)
            results.append({
                "topic_id": topic.topic_id,
                "topic_name": topic.name,
                "course_id": topic.course_id,
                "subject_id": topic.subject_id,
                "mastery_percentage": mastery.mastery_percentage,
                "is_strong": True,
            })

        synth = cls._synthesize_question_attempt_masteries(
            db, user_id, seen_topic_ids, course_id=course_id, subject_id=subject_id
        )
        for sm in synth:
            if sm.mastery_percentage >= threshold:
                results.append({
                    "topic_id": sm.topic_id,
                    "topic_name": sm.topic_id,
                    "course_id": course_id or "cs",
                    "subject_id": subject_id or "operating_systems",
                    "mastery_percentage": sm.mastery_percentage,
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
