"""Tests for Assessment FastAPI endpoints using HTTP TestClient."""

from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_health_check_endpoint(client: TestClient):
    """Test /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["subsystems"]["assessment"] == "operational"


def test_quizzes_api_lifecycle(client: TestClient, db_session: Session):
    """Test full HTTP API lifecycle for creating, retrieving, and submitting a quiz."""
    headers = {"X-User-ID": "http_user_001"}

    # 1. Create Quiz
    create_payload = {
        "subject_id": "operating_systems",
        "topic_ids": ["Paging"],
        "difficulty": "medium",
        "count": 3,
    }
    create_res = client.post("/api/quizzes", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    quiz_data = create_res.json()
    quiz_id = quiz_data["quiz_id"]
    assert len(quiz_data["questions"]) == 3

    # 2. Get Quiz
    get_res = client.get(f"/api/quizzes/{quiz_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["quiz_id"] == quiz_id

    # 3. Submit Quiz
    questions = quiz_data["questions"]
    submit_payload = {
        "answers": [
            {
                "question_id": q["question_id"],
                "selected_answer": q["options"][0],
                "time_taken": 15.0,
            }
            for q in questions
        ]
    }
    submit_res = client.post(f"/api/quizzes/{quiz_id}/submit", json=submit_payload, headers=headers)
    assert submit_res.status_code == 200
    submit_data = submit_res.json()
    assert "score" in submit_data
    assert submit_data["total"] == 3
    assert "percentage" in submit_data

    # 4. Check Performance Endpoint
    perf_res = client.get("/api/performance", headers=headers)
    assert perf_res.status_code == 200
    perf_data = perf_res.json()
    assert perf_data["attempt_count"] == 1
    assert perf_data["total_questions_attempted"] == 3

    # 5. Check Weak Topics Endpoint
    weak_res = client.get("/api/performance/weak-topics", headers=headers)
    assert weak_res.status_code == 200
    assert "topics" in weak_res.json()


def test_exams_api_endpoints(client: TestClient):
    """Test exam scheduling and listing endpoints."""
    headers = {"X-User-ID": "http_user_exams"}
    exam_date = (datetime.now(timezone.utc) + timedelta(days=6)).isoformat()

    create_payload = {
        "subject_id": "operating_systems",
        "title": "Operating Systems Final",
        "exam_date": exam_date,
    }

    # Create exam
    res = client.post("/api/exams", json=create_payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Operating Systems Final"
    assert data["assessment_focus"] == "targeted_weak_topic"

    # List all exams
    list_res = client.get("/api/exams", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # List upcoming exams
    up_res = client.get("/api/exams/upcoming", headers=headers)
    assert up_res.status_code == 200
    assert len(up_res.json()) == 1
