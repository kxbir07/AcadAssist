"""Comprehensive test suite for Person 4 Study Intelligence v2.

Covers:
1. Test 1 — Main planner scenario (Operating Systems exam 3 days away, Paging at 48% mastery, 120 min/day).
2. Test 2 — Deterministic progress calculations.
3. Test 3 — Exam-aware priority threshold rules.
4. Test 4 — Deterministic recommendations generation.
5. Test 5 — Task status updates, rescheduling, and user isolation.
6. Test 6 — Full API integration with FastAPI TestClient.
"""

from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models.shared import Course, Exam, QuizAttempt, Subject, Topic, TopicMastery, User
from app.models.study_plan import StudyPlan, StudyTask
from app.models.weekly_report import WeeklyReport
from app.services.person3_client import person3_consumer
from app.services.planner import create_study_plan, get_today_plan, update_task_status
from app.services.progress import get_progress
from app.services.recommendations import get_recommendations
from app.services.reports import generate_weekly_report, get_weekly_reports


def _seed_os_academic_data(db: Session, user_id: str, exam_days_away: int = 3) -> dict:
    """Seed sample data for Operating Systems scenario."""
    # User
    user = User(user_id=user_id, name="Test Student", email=f"{user_id}@acadassist.edu")
    db.add(user)

    # Course & Subject
    course = Course(course_id="CS301", name="Operating Systems", code="OS-CS301")
    subject = Subject(subject_id="SUB_MEM", course_id="CS301", name="Memory Management")
    db.add_all([course, subject])

    # Topics: Paging, Page Tables, TLB, Virtual Memory, Page Replacement
    topics = [
        Topic(topic_id="TOP_PAGING", subject_id="SUB_MEM", course_id="CS301", name="Paging", difficulty="medium", estimated_minutes=45),
        Topic(topic_id="TOP_PAGETABLES", subject_id="SUB_MEM", course_id="CS301", name="Page Tables", difficulty="hard", estimated_minutes=45),
        Topic(topic_id="TOP_TLB", subject_id="SUB_MEM", course_id="CS301", name="TLB", difficulty="medium", estimated_minutes=45),
        Topic(topic_id="TOP_VM", subject_id="SUB_MEM", course_id="CS301", name="Virtual Memory", difficulty="hard", estimated_minutes=45),
        Topic(topic_id="TOP_PAGEREPL", subject_id="SUB_MEM", course_id="CS301", name="Page Replacement", difficulty="medium", estimated_minutes=45),
    ]
    db.add_all(topics)

    # Exam
    today = date.today()
    exam_date = today + timedelta(days=exam_days_away)
    exam = Exam(
        exam_id="EXAM_OS",
        user_id=user_id,
        course_id="CS301",
        subject_id="SUB_MEM",
        title="Operating Systems Midterm",
        exam_date=exam_date,
        target_score=85.0,
    )
    db.add(exam)

    # Person 3 assessment data: Paging mastery = 48% (weak), others
    masteries = [
        TopicMastery(user_id=user_id, topic_id="TOP_PAGING", mastery_percentage=48.0, quizzes_attempted=3, quizzes_passed=1, is_weak=True, is_completed=False),
        TopicMastery(user_id=user_id, topic_id="TOP_PAGETABLES", mastery_percentage=65.0, quizzes_attempted=2, quizzes_passed=1, is_weak=False, is_completed=False),
        TopicMastery(user_id=user_id, topic_id="TOP_TLB", mastery_percentage=80.0, quizzes_attempted=4, quizzes_passed=4, is_weak=False, is_completed=True),
        TopicMastery(user_id=user_id, topic_id="TOP_VM", mastery_percentage=55.0, quizzes_attempted=2, quizzes_passed=1, is_weak=True, is_completed=False),
        TopicMastery(user_id=user_id, topic_id="TOP_PAGEREPL", mastery_percentage=72.0, quizzes_attempted=3, quizzes_passed=2, is_weak=False, is_completed=True),
    ]
    db.add_all(masteries)

    # Quiz attempts
    quiz_attempts = [
        QuizAttempt(user_id=user_id, topic_id="TOP_PAGING", score_percentage=40.0, total_questions=5, correct_answers=2, completed_at=datetime.now(timezone.utc) - timedelta(days=2)),
        QuizAttempt(user_id=user_id, topic_id="TOP_PAGING", score_percentage=56.0, total_questions=5, correct_answers=3, completed_at=datetime.now(timezone.utc) - timedelta(days=1)),
        QuizAttempt(user_id=user_id, topic_id="TOP_TLB", score_percentage=85.0, total_questions=5, correct_answers=4, completed_at=datetime.now(timezone.utc) - timedelta(days=1)),
    ]
    db.add_all(quiz_attempts)

    db.commit()
    return {"exam": exam, "today": today, "exam_date": exam_date}


# ==============================================================================
# TEST 1 — Main Planner Scenario (Operating Systems Demonstration)
# ==============================================================================
def test_main_planner_scenario(db_session: Session):
    """Test 1:
    Exam in 3 days, Paging mastery = 48%, Available study time = 120 min/day,
    Existing Day 1 task = 30 minutes.
    Verify:
    - Paging receives appropriate high priority
    - Existing task remains intact
    - Daily study time limit (120 min) is respected
    - No OS preparation is scheduled after the exam date
    - Tasks & plans are persisted
    - Today's plan can be retrieved
    - Progress metrics work
    - Weekly report generation and retrieval works
    """
    user_id = "student_demo_1"
    seeded = _seed_os_academic_data(db_session, user_id=user_id, exam_days_away=3)
    today = seeded["today"]
    exam_date = seeded["exam_date"]

    # Add an existing Day 1 task of 30 minutes
    existing_task = StudyTask(
        task_id="existing_task_day1",
        user_id=user_id,
        course_id="MATH101",
        title="Calculus Quiz Preparation",
        scheduled_date=today,
        start_time="08:00",
        duration_minutes=30,
        priority="normal",
        status="pending",
    )
    db_session.add(existing_task)
    db_session.commit()

    # Generate 5-day study plan (today through today + 4 days)
    start_date = today
    end_date = today + timedelta(days=4)
    daily_limit = 120  # 2 hours per day

    plan = create_study_plan(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        available_minutes_per_day=daily_limit,
        db=db_session,
    )

    assert plan is not None
    assert plan.study_plan_id is not None
    assert plan.user_id == user_id

    # Query all tasks for user
    tasks = db_session.query(StudyTask).filter(StudyTask.user_id == user_id).all()
    assert len(tasks) > 1

    # 1. Verify existing task was preserved
    preserved = db_session.query(StudyTask).filter(StudyTask.task_id == "existing_task_day1").first()
    assert preserved is not None
    assert preserved.title == "Calculus Quiz Preparation"
    assert preserved.duration_minutes == 30

    # 2. Verify Paging receives high priority (exam in 3-7 days and weak mastery = 48%)
    paging_tasks = [t for t in tasks if t.topic_id == "TOP_PAGING"]
    assert len(paging_tasks) >= 1
    assert paging_tasks[0].priority in ("high", "critical")
    # Paging should be scheduled on Day 1 (today) due to high urgency
    assert paging_tasks[0].scheduled_date == today

    # 3. Verify daily study time limit is strictly respected on every day
    daily_minutes: dict[date, int] = {}
    for t in tasks:
        daily_minutes[t.scheduled_date] = daily_minutes.get(t.scheduled_date, 0) + t.duration_minutes

    for day, mins in daily_minutes.items():
        assert mins <= daily_limit, f"Day {day} exceeded daily limit of {daily_limit} mins with {mins} mins"

    # On Day 1: existing 30 mins + new tasks must be <= 120 mins
    assert daily_minutes[today] <= 120

    # 4. Verify no OS preparation is scheduled AFTER the exam date
    for t in tasks:
        if t.course_id == "CS301":
            assert t.scheduled_date <= exam_date, (
                f"Task '{t.title}' for OS was scheduled on {t.scheduled_date}, after exam date {exam_date}"
            )

    # 5. Verify today's plan can be retrieved
    today_plan = get_today_plan(user_id=user_id, target_date=today, db=db_session)
    assert today_plan["total_tasks"] >= 1
    assert today_plan["total_scheduled_minutes"] <= 120
    assert any(t.topic_id == "TOP_PAGING" for t in today_plan["tasks"])

    # 6. Verify progress metrics
    progress = get_progress(user_id=user_id, course_id="CS301", db=db_session)
    assert "course_completion" in progress
    assert "topic_mastery" in progress
    assert progress["topic_mastery"]["TOP_PAGING"] == 48.0
    assert "TOP_PAGING" in progress["remaining_topics"]
    assert "TOP_TLB" in progress["completed_topics"]  # mastery 80% >= 70%

    # 7. Verify weekly report generation and retrieval
    week_start = today
    week_end = today + timedelta(days=6)
    report = generate_weekly_report(user_id=user_id, week_start=week_start, week_end=week_end, db=db_session)
    assert report["report_id"] is not None
    assert report["user_id"] == user_id
    assert isinstance(report["strong_topics"], list)
    assert isinstance(report["weak_topics"], list)
    assert any(wt["topic_id"] == "TOP_PAGING" for wt in report["weak_topics"])
    assert any(st["topic_id"] == "TOP_TLB" for st in report["strong_topics"])

    saved_reports = get_weekly_reports(user_id=user_id, db=db_session)
    assert len(saved_reports) >= 1
    assert saved_reports[0]["report_id"] == report["report_id"]


# ==============================================================================
# TEST 2 — Deterministic Progress Calculations
# ==============================================================================
def test_deterministic_progress_calculations(db_session: Session):
    """Test 2: Verify all 9 progress metrics are calculated deterministically without LLM."""
    user_id = "student_prog_test"
    _seed_os_academic_data(db_session, user_id=user_id, exam_days_away=5)

    # Seed 2 completed study tasks
    today = date.today()
    t1 = StudyTask(
        task_id="comp_task_1",
        user_id=user_id,
        course_id="CS301",
        subject_id="SUB_MEM",
        topic_id="TOP_TLB",
        title="TLB Drill",
        scheduled_date=today,
        duration_minutes=45,
        priority="normal",
        status="completed",
    )
    t2 = StudyTask(
        task_id="comp_task_2",
        user_id=user_id,
        course_id="CS301",
        subject_id="SUB_MEM",
        topic_id="TOP_PAGEREPL",
        title="Page Replacement Drill",
        scheduled_date=today - timedelta(days=1),
        duration_minutes=45,
        priority="normal",
        status="completed",
    )
    t3 = StudyTask(
        task_id="pend_task_3",
        user_id=user_id,
        course_id="CS301",
        subject_id="SUB_MEM",
        topic_id="TOP_PAGING",
        title="Paging Review",
        scheduled_date=today,
        duration_minutes=30,
        priority="high",
        status="pending",
    )
    db_session.add_all([t1, t2, t3])
    db_session.commit()

    prog = get_progress(user_id=user_id, course_id="CS301", subject_id="SUB_MEM", db=db_session)

    # Total topics = 5. Completed: TOP_TLB (80%), TOP_PAGEREPL (72%). Incomplete: Paging (48%), Page Tables (65%), VM (55%)
    # Course completion: 2 / 5 = 40.0%
    assert prog["course_completion"] == 40.0
    assert prog["subject_completion"] == 40.0

    # Topic mastery map
    assert prog["topic_mastery"]["TOP_PAGING"] == 48.0
    assert prog["topic_mastery"]["TOP_TLB"] == 80.0

    # Quiz accuracy: attempts were 40.0, 56.0, 85.0 -> avg = 60.33
    assert round(prog["quiz_accuracy"], 1) == 60.3

    # Planner completion: 2 completed / 3 total = 66.67%
    assert prog["planner_completion"] == 66.67

    # Total study time: 45 + 45 = 90 mins
    assert prog["study_time"] == 90

    # Study consistency: 2 active days out of 14 = 2 / 14 * 100 = 14.29%
    assert prog["study_consistency"] == 14.29

    # Completed & Remaining lists
    assert set(prog["completed_topics"]) == {"TOP_TLB", "TOP_PAGEREPL"}
    assert set(prog["remaining_topics"]) == {"TOP_PAGING", "TOP_PAGETABLES", "TOP_VM"}


# ==============================================================================
# TEST 3 — Exam Priority Threshold Rules
# ==============================================================================
def test_exam_priority_threshold_rules(db_session: Session):
    """Test 3: Verify all exam proximity rules:
    - > 14 days -> normal
    - 7–14 days -> increased preparation (medium)
    - 3–7 days -> targeted weak-topic preparation (high)
    - <= 2 days -> revision + targeted weak-topic preparation (critical)
    """
    user_id = "student_exam_thresh"
    user = User(user_id=user_id, name="Threshold User", email="thresh@acadassist.edu")
    course = Course(course_id="PHYS101", name="Physics")
    subject = Subject(subject_id="SUB_MECH", course_id="PHYS101", name="Mechanics")
    topic = Topic(topic_id="TOP_KINEMATICS", subject_id="SUB_MECH", course_id="PHYS101", name="Kinematics", estimated_minutes=45)
    db_session.add_all([user, course, subject, topic])

    # Weak mastery
    mastery = TopicMastery(
        user_id=user_id,
        topic_id="TOP_KINEMATICS",
        mastery_percentage=40.0,
        quizzes_attempted=1,
        quizzes_passed=0,
        is_weak=True,
        is_completed=False,
    )
    db_session.add(mastery)
    db_session.commit()

    today = date.today()

    # Test > 14 days (e.g. 20 days)
    recs_20d = get_recommendations(user_id=user_id, db=db_session)
    # With no exam yet, recommendation is for standalone weak topic
    assert any(r["topic_id"] == "TOP_KINEMATICS" for r in recs_20d)

    # 1. Exam in 20 days (>14 days)
    exam_20d = Exam(exam_id="EX_20D", user_id=user_id, course_id="PHYS101", subject_id="SUB_MECH", title="Final", exam_date=today + timedelta(days=20))
    db_session.add(exam_20d)
    db_session.commit()
    recs = get_recommendations(user_id=user_id, db=db_session)
    kin_rec = next(r for r in recs if r["topic_id"] == "TOP_KINEMATICS")
    assert kin_rec["urgency"] == "normal"
    db_session.delete(exam_20d)
    db_session.commit()

    # 2. Exam in 10 days (7-14 days) -> increased preparation (medium)
    exam_10d = Exam(exam_id="EX_10D", user_id=user_id, course_id="PHYS101", subject_id="SUB_MECH", title="Midterm 2", exam_date=today + timedelta(days=10))
    db_session.add(exam_10d)
    db_session.commit()
    recs = get_recommendations(user_id=user_id, db=db_session)
    kin_rec = next(r for r in recs if r["topic_id"] == "TOP_KINEMATICS")
    assert kin_rec["urgency"] == "medium"
    db_session.delete(exam_10d)
    db_session.commit()

    # 3. Exam in 5 days (3-7 days) -> targeted weak-topic preparation (high)
    exam_5d = Exam(exam_id="EX_5D", user_id=user_id, course_id="PHYS101", subject_id="SUB_MECH", title="Midterm 1", exam_date=today + timedelta(days=5))
    db_session.add(exam_5d)
    db_session.commit()
    recs = get_recommendations(user_id=user_id, db=db_session)
    kin_rec = next(r for r in recs if r["topic_id"] == "TOP_KINEMATICS")
    assert kin_rec["urgency"] == "high"
    db_session.delete(exam_5d)
    db_session.commit()

    # 4. Exam in 1 day (<= 2 days) -> revision + weak-topic focus (critical)
    exam_1d = Exam(exam_id="EX_1D", user_id=user_id, course_id="PHYS101", subject_id="SUB_MECH", title="Quiz Tomorrow", exam_date=today + timedelta(days=1))
    db_session.add(exam_1d)
    db_session.commit()
    recs = get_recommendations(user_id=user_id, db=db_session)
    kin_rec = next(r for r in recs if r["topic_id"] == "TOP_KINEMATICS")
    assert kin_rec["urgency"] == "critical"


# ==============================================================================
# TEST 4 — Deterministic Study Recommendations
# ==============================================================================
def test_deterministic_recommendations(db_session: Session):
    """Test 4: Verify recommendation engine handles weak topics, strong topics,
    upcoming exams, and produces deterministic sorted recommendations.
    """
    user_id = "student_recs_det"
    _seed_os_academic_data(db_session, user_id=user_id, exam_days_away=4)

    recs_first_call = get_recommendations(user_id=user_id, db=db_session)
    recs_second_call = get_recommendations(user_id=user_id, db=db_session)

    # Determinism: both calls must yield identical sequence
    assert len(recs_first_call) == len(recs_second_call)
    for r1, r2 in zip(recs_first_call, recs_second_call):
        assert r1["topic_id"] == r2["topic_id"]
        assert r1["urgency"] == r2["urgency"]
        assert r1["action"] == r2["action"]

    # Critical or High urgency items must appear first
    assert recs_first_call[0]["urgency"] in ("critical", "high")
    assert recs_first_call[0]["topic_id"] == "TOP_PAGING"


# ==============================================================================
# TEST 5 — Task Management, Updates, and User Data Isolation
# ==============================================================================
def test_task_management_and_isolation(db_session: Session):
    """Test 5: Task completion, rescheduling, invalid task ID, and user isolation."""
    user1 = "user_alpha"
    user2 = "user_beta"

    user_obj1 = User(user_id=user1, name="Alpha", email="alpha@acadassist.edu")
    user_obj2 = User(user_id=user2, name="Beta", email="beta@acadassist.edu")
    db_session.add_all([user_obj1, user_obj2])

    task = StudyTask(
        task_id="task_alpha_1",
        user_id=user1,
        title="Alpha Task",
        scheduled_date=date.today(),
        duration_minutes=45,
        priority="normal",
        status="pending",
    )
    db_session.add(task)
    db_session.commit()

    # 1. Update task to completed
    updated = update_task_status(task_id="task_alpha_1", status="completed", user_id=user1, db=db_session)
    assert updated.status == "completed"

    # 2. Reschedule task
    tomorrow = date.today() + timedelta(days=1)
    rescheduled = update_task_status(
        task_id="task_alpha_1",
        status="pending",
        user_id=user1,
        rescheduled_date=tomorrow,
        rescheduled_time="14:00",
        db=db_session,
    )
    assert rescheduled.scheduled_date == tomorrow
    assert rescheduled.start_time == "14:00"

    # 3. User isolation: user2 cannot modify user1's task
    with pytest.raises(KeyError):
        update_task_status(task_id="task_alpha_1", status="completed", user_id=user2, db=db_session)

    # 4. Invalid task ID
    with pytest.raises(KeyError):
        update_task_status(task_id="non_existent_task", status="completed", user_id=user1, db=db_session)


# ==============================================================================
# TEST 6 — Full API Integration via TestClient
# ==============================================================================
def test_api_integration_endpoints(client: TestClient, db_session: Session, auth_headers):
    """Test 6: Verify all Person 4 REST endpoints via FastAPI TestClient."""
    user_id = "student_api_client"
    seeded = _seed_os_academic_data(db_session, user_id=user_id, exam_days_away=3)
    today = seeded["today"]
    headers = auth_headers(user_id)

    # 1. GET /api/progress
    resp = client.get(f"/api/progress?user_id={user_id}&course_id=CS301", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "course_completion" in data
    assert data["topic_mastery"]["TOP_PAGING"] == 48.0

    # 2. GET /api/progress/recommendations
    resp = client.get(f"/api/progress/recommendations?user_id={user_id}", headers=headers)
    assert resp.status_code == 200
    rec_data = resp.json()
    assert "recommendations" in rec_data
    assert len(rec_data["recommendations"]) > 0

    # 3. POST /api/plans
    plan_payload = {
        "user_id": user_id,
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=3)).isoformat(),
        "available_minutes_per_day": 120,
    }
    resp = client.post("/api/plans", json=plan_payload, headers=headers)
    assert resp.status_code == 201
    plan_resp = resp.json()
    plan_id = plan_resp["study_plan_id"]
    assert plan_id is not None
    assert len(plan_resp["tasks"]) > 0

    # 4. GET /api/plans
    resp = client.get(f"/api/plans?user_id={user_id}", headers=headers)
    assert resp.status_code == 200
    plans_list = resp.json()
    assert len(plans_list) >= 1

    # 5. GET /api/plans/today
    resp = client.get(f"/api/plans/today?user_id={user_id}", headers=headers)
    assert resp.status_code == 200
    today_data = resp.json()
    assert today_data["user_id"] == user_id
    assert today_data["total_tasks"] >= 1

    # 6. GET /api/plans/{plan_id} (and user isolation)
    resp = client.get(f"/api/plans/{plan_id}?user_id={user_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["study_plan_id"] == plan_id

    # Verify user isolation: another user cannot access this plan
    intruder_headers = auth_headers("intruder_user")
    resp_unauthorized = client.get(f"/api/plans/{plan_id}?user_id=intruder_user", headers=intruder_headers)
    assert resp_unauthorized.status_code == 404

    # 7. PATCH /api/tasks/{task_id} (and user isolation)
    first_task = plan_resp["tasks"][0]
    task_id = first_task["task_id"]
    patch_payload = {"status": "completed"}

    # Another user cannot modify this task
    resp_unauth_patch = client.patch(f"/api/tasks/{task_id}?user_id=intruder_user", json=patch_payload, headers=intruder_headers)
    assert resp_unauth_patch.status_code in [403, 404]

    # Authorized user updates task
    resp = client.patch(f"/api/tasks/{task_id}?user_id={user_id}", json=patch_payload, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # 8. POST /api/reports/weekly
    report_payload = {
        "user_id": user_id,
        "week_start": today.isoformat(),
        "week_end": (today + timedelta(days=6)).isoformat(),
    }
    resp = client.post("/api/reports/weekly", json=report_payload, headers=headers)
    assert resp.status_code == 201
    rep_data = resp.json()
    assert rep_data["study_time_minutes"] >= 0
    assert "topics_completed" in rep_data
    assert "quiz_accuracy" in rep_data

    # 9. GET /api/reports/weekly
    resp = client.get(f"/api/reports/weekly?user_id={user_id}", headers=headers)
    assert resp.status_code == 200
    saved_reps = resp.json()
    assert len(saved_reps) >= 1
    assert saved_reps[0]["report_id"] == rep_data["report_id"]

