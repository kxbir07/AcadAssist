"""End-to-end cross-component integration test for AcadAssist Persons 2, 3, 4 baseline.

Validates the full workflow:
Document Ingestion & Processing (Person 2)
  -> Hybrid Knowledge Retrieval (Person 2)
  -> Exam Scheduling & Adaptive Quiz Generation (Person 3)
  -> Quiz Submission & Deterministic Scoring (Person 3)
  -> Performance Metrics & Weak-Topic Detection (Person 3)
  -> Study Intelligence & Exam-Aware Prioritization (Person 4)
  -> Daily Plan & Weekly Report Generation (Person 4)
  -> Unified Subsystem Health Check
"""

import io
from datetime import date, datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.shared import Course, Subject, Topic, TopicMastery, User


def test_full_cross_component_workflow(client: TestClient, db_session: Session, auth_headers):
    """Execute complete realistic student journey across all integrated subsystems."""
    user_id = "student_cross_e2e"

    # Step 0: Seed initial user and academic courses
    user = User(user_id=user_id, name="Cross E2E Student", email="cross_e2e@acadassist.edu")
    course = Course(course_id="CS302", name="Operating Systems", code="OS-CS302")
    subject = Subject(subject_id="SUB_OS_MEM", course_id="CS302", name="Memory Management")
    topics = [
        Topic(topic_id="Paging", subject_id="SUB_OS_MEM", course_id="CS302", name="Paging", difficulty="medium"),
        Topic(topic_id="Page_Tables", subject_id="SUB_OS_MEM", course_id="CS302", name="Page Tables", difficulty="hard"),
        Topic(topic_id="TLB", subject_id="SUB_OS_MEM", course_id="CS302", name="Translation Lookaside Buffer", difficulty="medium"),
    ]
    db_session.add(user)
    db_session.add(course)
    db_session.add(subject)
    db_session.add_all(topics)
    db_session.commit()

    headers = auth_headers(user_id)


    # =========================================================================
    # Step 1: Health Check verification (All subsystems)
    # =========================================================================
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert health_data["subsystems"]["knowledge_rag"] == "operational"
    assert health_data["subsystems"]["assessment"] == "operational"
    assert health_data["subsystems"]["study_intelligence"] == "operational"

    # =========================================================================
    # Step 2: Person 2 - Document Ingestion & Processing
    # =========================================================================
    doc_content = (
        "Operating Systems: Paging and Memory Architecture\n\n"
        "Paging is a memory management scheme that eliminates the need for contiguous allocation of physical memory.\n"
        "The physical address space is broken into fixed-sized blocks called frames.\n"
        "The logical address space is divided into blocks of the same size called pages.\n"
        "A page table translates logical addresses to physical addresses.\n"
        "The Translation Lookaside Buffer (TLB) acts as a high-speed hardware cache for page table entries."
    )
    upload_resp = client.post(
        "/api/documents",
        data={
            "user_id": user_id,
            "course_id": "CS302",
            "subject_id": "SUB_OS_MEM",
            "title": "OS Memory Management Chapter",
        },
        files={"file": ("memory_management.txt", io.BytesIO(doc_content.encode("utf-8")), "text/plain")},
        headers=headers,
    )
    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()

    doc_id = doc_data["document_id"]
    assert doc_id is not None
    assert doc_data["status"] == "uploaded"

    proc_resp = client.post(f"/api/documents/{doc_id}/process?user_id={user_id}", headers=headers)
    assert proc_resp.status_code == 200
    proc_data = proc_resp.json()
    assert proc_data["status"] == "processed"
    assert proc_data["processed_at"] is not None

    # =========================================================================
    # Step 3: Person 2 - Hybrid Knowledge Search (RAG Retrieval)
    # =========================================================================
    search_resp = client.post(
        "/api/knowledge/search",
        json={
            "user_id": user_id,
            "query": "What is the role of Translation Lookaside Buffer TLB?",
            "course_id": "CS302",
            "top_k": 3,
        },
        headers=headers,
    )
    assert search_resp.status_code == 200
    search_results = search_resp.json()["results"]
    assert len(search_results) > 0
    assert any("TLB" in r["content"] or "Translation Lookaside Buffer" in r["content"] for r in search_results)


    # =========================================================================
    # Step 4: Person 3 - Exam Scheduling (3 days away -> Targeted Weak-Topic Focus)
    # =========================================================================
    exam_target_date = datetime.now(timezone.utc) + timedelta(days=3)
    exam_resp = client.post(
        "/api/exams",
        json={
            "subject_id": "SUB_OS_MEM",
            "course_id": "CS302",
            "title": "Operating Systems Midterm",
            "exam_date": exam_target_date.isoformat(),
        },
        headers={"X-User-ID": user_id},
    )
    assert exam_resp.status_code == 201
    exam_data = exam_resp.json()
    assert exam_data["days_until_exam"] == 3
    assert exam_data["assessment_focus"] == "targeted_weak_topic"

    # =========================================================================
    # Step 5: Person 3 - Assessment Quiz Creation & Submission
    # =========================================================================
    quiz_resp = client.post(
        "/api/quizzes",
        json={
            "subject_id": "SUB_OS_MEM",
            "course_id": "CS302",
            "topic_ids": ["Paging"],
            "difficulty": "medium",
            "count": 4,
        },
        headers={"X-User-ID": user_id},
    )
    assert quiz_resp.status_code == 201
    quiz_data = quiz_resp.json()
    quiz_id = quiz_data["quiz_id"]
    questions = quiz_data["questions"]
    assert len(questions) == 4

    # Submit with 1 correct answer (25% accuracy -> Weak topic detected)
    # In Person 3, correct_answer is protected from public QuestionOut schema
    from app.assessment.models import Question
    q_db = db_session.query(Question).filter(Question.question_id == questions[0]["question_id"]).first()
    correct_answer_val = q_db.correct_answer
    submit_payload = {
        "answers": [
            {
                "question_id": questions[0]["question_id"],
                "selected_answer": correct_answer_val,
                "time_taken": 20.0,
            }
        ] + [
            {
                "question_id": q["question_id"],
                "selected_answer": "intentionally_incorrect_choice",
                "time_taken": 15.0,
            }
            for q in questions[1:]
        ]
    }
    submit_resp = client.post(f"/api/quizzes/{quiz_id}/submit", json=submit_payload, headers={"X-User-ID": user_id})
    assert submit_resp.status_code == 200
    submission = submit_resp.json()
    assert submission["score"] == 1
    assert submission["percentage"] == 25.0

    # Step 6: Person 3 - Performance & Weak Topic Retrieval
    perf_resp = client.get(f"/api/performance?subject_id=SUB_OS_MEM", headers={"X-User-ID": user_id})
    assert perf_resp.status_code == 200
    perf_data = perf_resp.json()
    assert perf_data["total_questions_attempted"] == 4
    assert len(perf_data["weak_topics"]) >= 1

    # =========================================================================
    # Step 7: Person 4 - Study Intelligence & Recommendations
    # Seed topic mastery reflecting the assessment weakness for study planner
    # =========================================================================
    mastery = TopicMastery(
        id="mast_paging_01",
        user_id=user_id,
        topic_id="Paging",
        mastery_percentage=25.0,
        quizzes_attempted=1,
        quizzes_passed=0,
        is_weak=True,
    )
    db_session.add(mastery)
    db_session.commit()

    rec_resp = client.get(f"/api/progress/recommendations?user_id={user_id}", headers=headers)
    assert rec_resp.status_code == 200
    recs = rec_resp.json()["recommendations"]
    assert len(recs) > 0
    # Paging should be recommended due to exam in 3 days and low mastery
    assert any(r["topic_id"] == "Paging" for r in recs)

    # =========================================================================
    # Step 8: Person 4 - Exam-Aware Study Plan Creation
    # =========================================================================
    today = date.today()
    plan_resp = client.post(
        "/api/plans",
        json={
            "user_id": user_id,
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=3)).isoformat(),
            "available_minutes_per_day": 120,
        },
        headers=headers,
    )
    assert plan_resp.status_code == 201
    plan = plan_resp.json()
    assert len(plan["tasks"]) > 0

    # Paging task must be scheduled with high priority
    paging_tasks = [t for t in plan["tasks"] if t["topic_id"] == "Paging"]
    assert len(paging_tasks) >= 1
    assert paging_tasks[0]["priority"] in ("high", "critical")

    # =========================================================================
    # Step 9: Person 4 - Today's Plan & Weekly Report
    # =========================================================================
    today_resp = client.get(f"/api/plans/today?user_id={user_id}&target_date={today.isoformat()}", headers=headers)
    assert today_resp.status_code == 200
    today_plan = today_resp.json()
    assert today_plan["total_scheduled_minutes"] <= 120

    report_resp = client.post(
        "/api/reports/weekly",
        json={
            "user_id": user_id,
            "week_start": today.isoformat(),
            "week_end": (today + timedelta(days=6)).isoformat(),
        },
        headers=headers,
    )
    assert report_resp.status_code == 201
    report = report_resp.json()

    assert "study_time_minutes" in report
    assert "recommendations" in report
    assert "upcoming_exams" in report
    assert len(report["upcoming_exams"]) >= 1
