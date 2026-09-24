"""Study planner service for AcadAssist Study Intelligence (Person 4).

Generates deterministic, exam-aware daily and weekly study plans adhering to hard constraints:
1. Daily study time limit (never exceeds available_minutes_per_day, accounting for existing tasks).
2. Existing tasks are preserved (never deleted or silently replaced).
3. Exam deadlines are strictly respected (never schedule exam preparation after the exam date).
4. Deterministic slotting and non-overlapping start times.
5. Exam proximity tiers (<=2 days: revision+weak; 3-7 days: weak topic; 7-14 days: increased; >14 days: normal).
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import SessionLocal
from app.models.shared import Exam, Topic
from app.models.study_plan import StudyPlan, StudyTask
from app.services.person3_client import person3_consumer


def _format_time(hours: int, minutes: int) -> str:
    """Format hour and minute into HH:MM string."""
    return f"{hours:02d}:{minutes:02d}"


def _parse_time_to_minutes(time_str: Optional[str]) -> Optional[int]:
    """Convert 'HH:MM' string to minutes from midnight."""
    if not time_str:
        return None
    try:
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        return None


def create_study_plan(
    user_id: str,
    start_date: date,
    end_date: date,
    available_minutes_per_day: Optional[int] = None,
    db: Optional[Session] = None,
) -> StudyPlan:
    """Create a deterministic, exam-aware study plan with discrete tasks.

    Args:
        user_id: ID of the student.
        start_date: Start date of the plan period.
        end_date: End date of the plan period (inclusive).
        available_minutes_per_day: Daily study time budget (defaults to config: 120 mins).
        db: Optional database session.

    Returns:
        The persisted StudyPlan model instance populated with StudyTask items.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        daily_limit = available_minutes_per_day or settings.DEFAULT_STUDY_TIME_MINUTES

        if end_date < start_date:
            raise ValueError("end_date cannot be earlier than start_date")

        # 1. Fetch existing tasks across the date range to preserve existing commitments
        existing_tasks = (
            db.query(StudyTask)
            .filter(
                StudyTask.user_id == user_id,
                StudyTask.scheduled_date >= start_date,
                StudyTask.scheduled_date <= end_date,
            )
            .all()
        )

        # Map existing minutes and busy intervals per date
        existing_minutes_per_day: Dict[date, int] = {}
        busy_intervals_per_day: Dict[date, List[tuple[int, int]]] = {}

        current = start_date
        while current <= end_date:
            existing_minutes_per_day[current] = 0
            busy_intervals_per_day[current] = []
            current += timedelta(days=1)

        for et in existing_tasks:
            d = et.scheduled_date
            if d in existing_minutes_per_day:
                existing_minutes_per_day[d] += et.duration_minutes
                st_min = _parse_time_to_minutes(et.start_time)
                if st_min is not None:
                    busy_intervals_per_day[d].append((st_min, st_min + et.duration_minutes))

        # 2. Fetch upcoming exams
        upcoming_exams = person3_consumer.get_upcoming_exams(
            db=db,
            user_id=user_id,
            from_date=start_date,
        )
        exam_by_subject: Dict[str, Exam] = {}
        exam_by_course: Dict[str, Exam] = {}
        for ex in upcoming_exams:
            if ex.subject_id and ex.subject_id not in exam_by_subject:
                exam_by_subject[ex.subject_id] = ex
            if ex.course_id and ex.course_id not in exam_by_course:
                exam_by_course[ex.course_id] = ex

        # 3. Fetch topic mastery records
        mastery_records = person3_consumer.get_user_topic_mastery(db=db, user_id=user_id)
        mastery_map = {m.topic_id: m for m in mastery_records}

        # 4. Fetch all available topics
        all_topics = person3_consumer.get_all_topics(db=db)

        # 5. Build candidate study items with priority and deadline constraints
        candidates = []
        for topic in all_topics:
            tid = topic.topic_id
            m = mastery_map.get(tid)
            mastery_pct = float(m.mastery_percentage) if m else 0.0
            is_completed = m.is_completed if m else (mastery_pct >= settings.MASTERY_COMPLETION_THRESHOLD)

            # Look up associated exam for deadline and proximity
            exam = exam_by_subject.get(topic.subject_id) or exam_by_course.get(topic.course_id)
            exam_date_val = (
                exam.exam_date.date()
                if exam and isinstance(exam.exam_date, datetime)
                else (exam.exam_date if exam else None)
            )
            exam_deadline = exam_date_val

            # Calculate days until exam relative to start_date
            days_to_exam = (exam_date_val - start_date).days if exam_date_val else 999


            # Priority assignment based on exam proximity and mastery
            is_weak = (mastery_pct < settings.WEAK_MASTERY_THRESHOLD) or (m.is_weak if m else False)

            if days_to_exam <= settings.EXAM_PROXIMITY_URGENT_DAYS:
                priority = "critical"
                session_type = "Revision & Weak-Topic Drill" if is_weak else "Exam Revision"
                duration = 45
            elif days_to_exam <= settings.EXAM_PROXIMITY_WEAK_PRIORITY_DAYS:
                priority = "high" if is_weak else "medium"
                session_type = "Targeted Weak-Topic Practice" if is_weak else "Concept Review"
                duration = 45
            elif days_to_exam <= settings.EXAM_PROXIMITY_PREP_DAYS:
                priority = "medium" if is_weak else "normal"
                session_type = "Focused Preparation"
                duration = 45
            else:
                priority = "normal"
                session_type = "Core Study Session"
                duration = min(topic.estimated_minutes or 45, 60)

            # Weight for sorting (lower weight = scheduled first)
            # Priority rank: critical (0) < high (1) < medium (2) < normal (3)
            priority_weights = {"critical": 0, "high": 1, "medium": 2, "normal": 3}
            p_weight = priority_weights.get(priority, 4)

            # Incomplete topics come before completed ones
            comp_weight = 1 if is_completed else 0

            candidates.append({
                "topic": topic,
                "priority": priority,
                "p_weight": p_weight,
                "comp_weight": comp_weight,
                "days_to_exam": days_to_exam,
                "mastery_pct": mastery_pct,
                "is_weak": is_weak,
                "is_completed": is_completed,
                "exam_deadline": exam_deadline,
                "session_type": session_type,
                "duration": duration,
            })

        # Sort candidate topics:
        # 1. Incomplete first (comp_weight)
        # 2. Priority tier (critical, high, medium, normal)
        # 3. Days to exam (nearest first)
        # 4. Mastery percentage (lowest first)
        candidates.sort(
            key=lambda c: (
                c["comp_weight"],
                c["p_weight"],
                c["days_to_exam"],
                c["mastery_pct"],
            )
        )

        # 6. Create the StudyPlan record
        plan = StudyPlan(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            status="active",
        )
        db.add(plan)
        db.flush()  # obtain plan.study_plan_id

        # 7. Discrete scheduling algorithm
        # Iterate over days and slot candidates respecting daily limit, existing tasks, and exam deadlines
        candidate_idx = 0
        total_candidates = len(candidates)

        current_day = start_date
        while current_day <= end_date and candidate_idx < total_candidates:
            # Remaining minutes for this day
            used_minutes = existing_minutes_per_day[current_day]
            remaining_minutes = daily_limit - used_minutes

            # Default start minute of the day for study blocks (e.g., 09:00 = 540 min)
            current_minute_slot = 9 * 60

            while remaining_minutes >= 30 and candidate_idx < total_candidates:
                cand = candidates[candidate_idx]

                # Hard constraint: Exam deadline
                # Never schedule relevant preparation AFTER the associated exam date
                if cand["exam_deadline"] and current_day > cand["exam_deadline"]:
                    # Cannot schedule on or after exam date
                    candidate_idx += 1
                    continue

                task_duration = min(cand["duration"], remaining_minutes)
                if task_duration < 30:
                    break

                # Find a non-overlapping time slot for current_day
                busy = busy_intervals_per_day[current_day]
                while True:
                    conflict = False
                    for b_start, b_end in busy:
                        if not (current_minute_slot + task_duration <= b_start or current_minute_slot >= b_end):
                            # Overlap detected, advance past the busy interval
                            current_minute_slot = b_end + 15  # 15 min buffer
                            conflict = True
                            break
                    if not conflict:
                        break

                slot_start_str = _format_time(current_minute_slot // 60, current_minute_slot % 60)

                topic_obj = cand["topic"]
                task = StudyTask(
                    study_plan_id=plan.study_plan_id,
                    user_id=user_id,
                    course_id=topic_obj.course_id,
                    subject_id=topic_obj.subject_id,
                    topic_id=topic_obj.topic_id,
                    title=f"{cand['session_type']}: {topic_obj.name}",
                    description=(
                        f"Priority: {cand['priority'].upper()} | Topic Mastery: {cand['mastery_pct']:.0f}% | "
                        f"{'Weak topic drill' if cand['is_weak'] else 'Concept study'}."
                    ),
                    scheduled_date=current_day,
                    start_time=slot_start_str,
                    duration_minutes=task_duration,
                    priority=cand["priority"],
                    status="pending",
                )
                db.add(task)

                # Update day usage and busy intervals
                busy.append((current_minute_slot, current_minute_slot + task_duration))
                current_minute_slot += task_duration + 15  # 15-minute buffer between tasks
                remaining_minutes -= task_duration
                existing_minutes_per_day[current_day] += task_duration

                candidate_idx += 1

            current_day += timedelta(days=1)

        db.commit()
        db.refresh(plan)
        return plan
    except Exception:
        db.rollback()
        raise
    finally:
        if close_db:
            db.close()


def get_today_plan(
    user_id: str,
    target_date: Optional[date] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Retrieve all study tasks scheduled for today (or a specific date) for the user."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        query_date = target_date or date.today()
        tasks = (
            db.query(StudyTask)
            .filter(
                StudyTask.user_id == user_id,
                StudyTask.scheduled_date == query_date,
            )
            .order_by(StudyTask.start_time.asc())
            .all()
        )

        total_minutes = sum(t.duration_minutes for t in tasks)
        completed_minutes = sum(t.duration_minutes for t in tasks if t.status == "completed")

        return {
            "date": query_date.isoformat(),
            "user_id": user_id,
            "total_tasks": len(tasks),
            "total_scheduled_minutes": total_minutes,
            "completed_minutes": completed_minutes,
            "tasks": tasks,
        }
    finally:
        if close_db:
            db.close()


def update_task_status(
    task_id: str,
    status: str,
    user_id: Optional[str] = None,
    rescheduled_date: Optional[date] = None,
    rescheduled_time: Optional[str] = None,
    db: Optional[Session] = None,
) -> StudyTask:
    """Update task completion status or reschedule task.

    Args:
        task_id: ID of the study task.
        status: New status ("pending", "in_progress", "completed", "skipped").
        user_id: Optional user_id to enforce authorization and user isolation.
        rescheduled_date: Optional new date if rescheduling.
        rescheduled_time: Optional new start time if rescheduling.
        db: Optional database session.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        query = db.query(StudyTask).filter(StudyTask.task_id == task_id)
        if user_id:
            query = query.filter(StudyTask.user_id == user_id)
        task = query.first()

        if not task:
            raise KeyError(f"Task with id {task_id} not found or unauthorized")

        task.status = status
        task.updated_at = datetime.now(timezone.utc)

        if rescheduled_date is not None:
            task.scheduled_date = rescheduled_date
        if rescheduled_time is not None:
            task.start_time = rescheduled_time

        db.commit()
        db.refresh(task)
        return task
    except Exception:
        db.rollback()
        raise
    finally:
        if close_db:
            db.close()
