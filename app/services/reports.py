"""Weekly report service for AcadAssist Study Intelligence (Person 4).

Generates deterministic, reproducible weekly summaries of study time, topics completed,
quiz performance, strong/weak topics, planner completion, upcoming exams, and recommendations.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.models.study_plan import StudyTask
from app.models.weekly_report import WeeklyReport
from app.services.person3_client import person3_consumer
from app.services.recommendations import get_recommendations


def generate_weekly_report(
    user_id: str,
    week_start: date,
    week_end: date,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Generate and persist a weekly study report for the specified user and date range.

    Returns dictionary matching the required schema:
        study_time_minutes: int
        topics_completed: int
        quiz_accuracy: float
        strong_topics: List[Dict[str, Any]]
        weak_topics: List[Dict[str, Any]]
        planner_completion: float
        upcoming_exams: List[Dict[str, Any]]
        recommendations: List[Dict[str, Any]]
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        start_dt = datetime.combine(week_start, time.min).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(week_end, time.max).replace(tzinfo=timezone.utc)

        # 1. Study tasks in this week
        weekly_tasks = (
            db.query(StudyTask)
            .filter(
                StudyTask.user_id == user_id,
                StudyTask.scheduled_date >= week_start,
                StudyTask.scheduled_date <= week_end,
            )
            .all()
        )

        total_scheduled = len(weekly_tasks)
        completed_tasks = [t for t in weekly_tasks if t.status == "completed"]
        completed_count = len(completed_tasks)

        study_time_minutes = sum(t.duration_minutes for t in completed_tasks)

        planner_completion = 0.0
        if total_scheduled > 0:
            planner_completion = round((completed_count / total_scheduled) * 100.0, 2)

        # Topics completed in this period (unique topic_ids in completed tasks)
        topics_completed = len({t.topic_id for t in completed_tasks if t.topic_id})

        # 2. Quiz performance from Person 3
        quiz_accuracy = person3_consumer.get_quiz_accuracy(
            db=db,
            user_id=user_id,
            since=start_dt,
            until=end_dt,
        )

        # 3. Strong and weak topics
        strong_topics = person3_consumer.get_strong_topics(db=db, user_id=user_id)
        weak_topics = person3_consumer.get_weak_topics(db=db, user_id=user_id)

        # 4. Upcoming exams within next 14 days from week_end
        upcoming_exams_objs = person3_consumer.get_upcoming_exams(
            db=db,
            user_id=user_id,
            from_date=week_start,
            to_date=week_end + timedelta(days=14),
        )
        upcoming_exams = [
            {
                "exam_id": ex.exam_id,
                "title": ex.title,
                "course_id": ex.course_id,
                "subject_id": ex.subject_id,
                "exam_date": ex.exam_date.isoformat(),
                "days_until": (
                    (ex.exam_date.date() if isinstance(ex.exam_date, datetime) else ex.exam_date)
                    - week_end
                ).days,
            }
            for ex in upcoming_exams_objs
        ]

        # 5. Deterministic recommendations
        recommendations = get_recommendations(user_id=user_id, db=db)

        # 6. Persist to WeeklyReport table
        report_record = WeeklyReport(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            study_time_minutes=study_time_minutes,
            topics_completed=topics_completed,
            quiz_accuracy=quiz_accuracy,
            strong_topics=strong_topics,
            weak_topics=weak_topics,
            planner_completion=planner_completion,
            upcoming_exams=upcoming_exams,
            recommendations=recommendations,
            generated_at=datetime.now(timezone.utc),
        )
        db.add(report_record)
        db.commit()
        db.refresh(report_record)

        return {
            "report_id": report_record.report_id,
            "user_id": user_id,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "study_time_minutes": study_time_minutes,
            "topics_completed": topics_completed,
            "quiz_accuracy": quiz_accuracy,
            "strong_topics": strong_topics,
            "weak_topics": weak_topics,
            "planner_completion": planner_completion,
            "upcoming_exams": upcoming_exams,
            "recommendations": recommendations,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        if close_db:
            db.close()


def get_weekly_reports(
    user_id: str,
    week_start: Optional[date] = None,
    db: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Retrieve saved weekly reports for the user."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        query = db.query(WeeklyReport).filter(WeeklyReport.user_id == user_id)
        if week_start:
            query = query.filter(WeeklyReport.week_start == week_start)
        reports = query.order_by(WeeklyReport.week_start.desc()).all()

        return [
            {
                "report_id": r.report_id,
                "user_id": r.user_id,
                "week_start": r.week_start.isoformat(),
                "week_end": r.week_end.isoformat(),
                "study_time_minutes": r.study_time_minutes,
                "topics_completed": r.topics_completed,
                "quiz_accuracy": r.quiz_accuracy,
                "strong_topics": r.strong_topics or [],
                "weak_topics": r.weak_topics or [],
                "planner_completion": r.planner_completion,
                "upcoming_exams": r.upcoming_exams or [],
                "recommendations": r.recommendations or [],
                "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            }
            for r in reports
        ]
    finally:
        if close_db:
            db.close()
