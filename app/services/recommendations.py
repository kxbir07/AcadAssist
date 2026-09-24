"""Recommendation service for AcadAssist Study Intelligence (Person 4).

Generates deterministic, actionable study recommendations based on real exam dates,
topic mastery, weak topics, and remaining course topics.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import SessionLocal
from app.models.shared import Exam, Topic
from app.services.person3_client import person3_consumer


def get_recommendations(
    user_id: str,
    db: Optional[Session] = None,
) -> List[Dict[str, Any]]:
    """Generate deterministic, ranked study recommendations for the user.

    Returns a list of structured recommendation objects:
        topic_id: str
        topic_name: str
        urgency: str ("critical", "high", "medium", "normal")
        action: str
        reason: str
        exam_id: Optional[str]
        days_until_exam: Optional[int]
        mastery_percentage: float
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        today = date.today()
        recommendations: List[Dict[str, Any]] = []

        # 1. Fetch upcoming exams
        upcoming_exams = person3_consumer.get_upcoming_exams(db=db, user_id=user_id, from_date=today)

        # 2. Fetch weak topics (mastery < 60%)
        weak_topics = person3_consumer.get_weak_topics(db=db, user_id=user_id)
        weak_topic_map = {wt["topic_id"]: wt for wt in weak_topics}

        # 3. Fetch all topic masteries for user
        all_masteries = person3_consumer.get_user_topic_mastery(db=db, user_id=user_id)
        mastery_by_topic = {m.topic_id: float(m.mastery_percentage) for m in all_masteries}

        # 4. Correlate upcoming exams with weak topics and remaining topics
        processed_topic_ids = set()

        for exam in upcoming_exams:
            exam_d = exam.exam_date.date() if isinstance(exam.exam_date, datetime) else exam.exam_date
            days_left = (exam_d - today).days


            # Get topics for this exam's course/subject
            exam_topics = person3_consumer.get_all_topics(
                db=db,
                course_id=exam.course_id,
                subject_id=exam.subject_id,
            )

            # Sort exam topics: weak topics first, then lowest mastery
            exam_topics_sorted = sorted(
                exam_topics,
                key=lambda t: (
                    0 if t.topic_id in weak_topic_map else 1,
                    mastery_by_topic.get(t.topic_id, 0.0),
                ),
            )

            for topic in exam_topics_sorted:
                topic_id = topic.topic_id
                if topic_id in processed_topic_ids:
                    continue

                mastery = mastery_by_topic.get(topic_id, 0.0)
                is_weak = topic_id in weak_topic_map or mastery < settings.WEAK_MASTERY_THRESHOLD

                # Determine exam urgency tier
                if days_left <= settings.EXAM_PROXIMITY_URGENT_DAYS:
                    urgency = "critical"
                    if is_weak:
                        action = f"Targeted weak-topic drill: review core formulas and attempt practice questions for {topic.name}."
                        reason = (
                            f"{topic.name} has only {mastery:.0f}% mastery and the {exam.title} exam is in "
                            f"{days_left} day{'s' if days_left != 1 else ''}. Immediate revision required."
                        )
                    else:
                        action = f"High-yield revision session for {topic.name}."
                        reason = f"{exam.title} exam is in {days_left} day{'s' if days_left != 1 else ''}."

                elif days_left <= settings.EXAM_PROXIMITY_WEAK_PRIORITY_DAYS:
                    if is_weak:
                        urgency = "high"
                        action = (
                            f"Prioritize a 45-minute {topic.name} revision session today followed by targeted practice."
                        )
                        reason = (
                            f"{topic.name} has {mastery:.0f}% mastery and the {exam.title} exam is in {days_left} days."
                        )
                    else:
                        urgency = "medium"
                        action = f"Scheduled study session on {topic.name}."
                        reason = f"Prepare ahead for {exam.title} in {days_left} days."

                elif days_left <= settings.EXAM_PROXIMITY_PREP_DAYS:
                    urgency = "medium" if is_weak else "normal"
                    action = f"Increased preparation: focus on understanding key concepts of {topic.name}."
                    reason = f"{exam.title} is in {days_left} days ({mastery:.0f}% mastery)."

                else:
                    urgency = "normal"
                    action = f"Steady-paced study block on {topic.name}."
                    reason = f"Regular syllabus progression for {exam.title} ({days_left} days remaining)."

                recommendations.append({
                    "topic_id": topic_id,
                    "topic_name": topic.name,
                    "urgency": urgency,
                    "action": action,
                    "reason": reason,
                    "exam_id": exam.exam_id,
                    "days_until_exam": days_left,
                    "mastery_percentage": round(mastery, 1),
                })
                processed_topic_ids.add(topic_id)

        # 5. Add any remaining weak topics not tied to an immediate exam
        for wt in weak_topics:
            topic_id = wt["topic_id"]
            if topic_id not in processed_topic_ids:
                mastery = wt["mastery_percentage"]
                recommendations.append({
                    "topic_id": topic_id,
                    "topic_name": wt["topic_name"],
                    "urgency": "high",
                    "action": f"Address weak topic: dedicated review on {wt['topic_name']} ({mastery:.0f}% mastery).",
                    "reason": f"Topic mastery is below {settings.WEAK_MASTERY_THRESHOLD}%. Practice foundational concepts.",
                    "exam_id": None,
                    "days_until_exam": None,
                    "mastery_percentage": round(mastery, 1),
                })
                processed_topic_ids.add(topic_id)

        # 6. Sort recommendations deterministically by urgency and days left
        urgency_rank = {"critical": 0, "high": 1, "medium": 2, "normal": 3}
        recommendations.sort(
            key=lambda r: (
                urgency_rank.get(r["urgency"], 4),
                r["days_until_exam"] if r["days_until_exam"] is not None else 999,
                r["mastery_percentage"],
            )
        )

        return recommendations
    finally:
        if close_db:
            db.close()
