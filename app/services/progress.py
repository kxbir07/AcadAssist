"""Progress tracking service for AcadAssist Study Intelligence (Person 4).

All progress and mastery calculations are strictly deterministic. No LLM estimation.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import SessionLocal
from app.models.shared import Course, Subject, Topic, TopicMastery
from app.models.study_plan import StudyTask
from app.services.person3_client import person3_consumer


def get_progress(
    user_id: str,
    course_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Calculate deterministic progress metrics for a user.

    Returns:
        course_completion: float (0.0 - 100.0)
        subject_completion: float (0.0 - 100.0)
        topic_mastery: Dict[str, float]
        quiz_accuracy: float (0.0 - 100.0)
        study_consistency: float (0.0 - 100.0)
        planner_completion: float (0.0 - 100.0)
        study_time: int (total completed minutes)
        completed_topics: List[str] (topic IDs)
        remaining_topics: List[str] (topic IDs)
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # 1. Fetch scoped topics
        topics_query = db.query(Topic)
        if course_id:
            topics_query = topics_query.filter(Topic.course_id == course_id)
        if subject_id:
            topics_query = topics_query.filter(Topic.subject_id == subject_id)
        all_topics = topics_query.all()
        all_topic_ids = {t.topic_id for t in all_topics}

        # 2. Fetch authoritative mastery records from Person 3
        mastery_records = person3_consumer.get_user_topic_mastery(
            db=db,
            user_id=user_id,
            course_id=course_id,
            subject_id=subject_id,
        )
        mastery_map: Dict[str, float] = {}
        completed_topic_ids: set[str] = set()

        completion_threshold = settings.MASTERY_COMPLETION_THRESHOLD

        for m in mastery_records:
            mastery_map[m.topic_id] = round(float(m.mastery_percentage), 2)
            if m.mastery_percentage >= completion_threshold or m.is_completed:
                completed_topic_ids.add(m.topic_id)

        # For topics without a mastery record yet, default mastery is 0.0
        for t in all_topics:
            if t.topic_id not in mastery_map:
                mastery_map[t.topic_id] = 0.0

        # Completed vs Remaining
        completed_topics = [t.topic_id for t in all_topics if t.topic_id in completed_topic_ids]
        remaining_topics = [t.topic_id for t in all_topics if t.topic_id not in completed_topic_ids]

        total_topics_count = len(all_topics)

        # Course completion percentage
        course_completion = 0.0
        if total_topics_count > 0:
            course_completion = round((len(completed_topics) / total_topics_count) * 100.0, 2)

        # Subject completion percentage
        subject_completion = 0.0
        if subject_id:
            subject_topics = [t for t in all_topics if t.subject_id == subject_id]
            if subject_topics:
                sub_completed = [t.topic_id for t in subject_topics if t.topic_id in completed_topic_ids]
                subject_completion = round((len(sub_completed) / len(subject_topics)) * 100.0, 2)
        else:
            subject_completion = course_completion

        # 3. Quiz accuracy from Person 3
        quiz_accuracy = person3_consumer.get_quiz_accuracy(
            db=db,
            user_id=user_id,
            course_id=course_id,
            subject_id=subject_id,
        )

        # 4. Study tasks statistics (Planner completion & study time)
        tasks_query = db.query(StudyTask).filter(StudyTask.user_id == user_id)
        if course_id:
            tasks_query = tasks_query.filter(StudyTask.course_id == course_id)
        if subject_id:
            tasks_query = tasks_query.filter(StudyTask.subject_id == subject_id)
        user_tasks = tasks_query.all()

        total_tasks = len(user_tasks)
        completed_tasks = [t for t in user_tasks if t.status == "completed"]
        completed_count = len(completed_tasks)

        planner_completion = 0.0
        if total_tasks > 0:
            planner_completion = round((completed_count / total_tasks) * 100.0, 2)

        study_time = sum(t.duration_minutes for t in completed_tasks)

        # 5. Study consistency: active days with completed tasks in last 14 days
        # Expressed as a percentage of 14-day study target
        today = date.today()
        fourteen_days_ago = today - timedelta(days=13)
        recent_completed_tasks = [
            t for t in completed_tasks
            if t.scheduled_date and fourteen_days_ago <= t.scheduled_date <= today
        ]
        active_days = len({t.scheduled_date for t in recent_completed_tasks})
        # If user has been studying, consistency is active_days / 14 * 100, or 100% if active >= 10
        # A standard deterministic metric: active_days / 14 * 100
        study_consistency = round((active_days / 14.0) * 100.0, 2)

        return {
            "course_completion": course_completion,
            "subject_completion": subject_completion,
            "topic_mastery": mastery_map,
            "quiz_accuracy": quiz_accuracy,
            "study_consistency": study_consistency,
            "planner_completion": planner_completion,
            "study_time": study_time,
            "completed_topics": completed_topics,
            "remaining_topics": remaining_topics,
        }
    finally:
        if close_db:
            db.close()
