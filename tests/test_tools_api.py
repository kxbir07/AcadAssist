"""Unit tests for the AcadAssist Tools HTTP API endpoints and OpenAPI schemas."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.database.session import SessionLocal
from app.models.shared import User

class AuthTestClient(TestClient):
    def request(self, method, url, **kwargs):
        headers = dict(kwargs.get("headers") or {})
        if "Authorization" not in headers:
            user_id = None
            json_body = kwargs.get("json")
            if isinstance(json_body, dict):
                user_id = json_body.get("user_id")
            if not user_id:
                user_id = "00000000-0000-0000-0000-000000000001"
            
            with SessionLocal() as db:
                if not db.query(User).filter(User.user_id == user_id).first():
                    db.add(User(user_id=user_id, email=f"{user_id}@test.local", name=user_id, password_hash="dummy"))
                    db.commit()
            token = create_access_token({"sub": user_id, "email": f"{user_id}@test.local"})
            headers["Authorization"] = f"Bearer {token}"
            kwargs["headers"] = headers
        return super().request(method, url, **kwargs)

client = AuthTestClient(app)

EXPECTED_TOOL_OPERATION_IDS = {
    "search_knowledge",
    "summarize_document",
    "generate_quiz",
    "submit_quiz",
    "get_performance",
    "get_weak_topics",
    "get_progress",
    "get_upcoming_exams",
    "create_study_plan",
    "get_today_plan",
    "generate_weekly_report",
}


def test_tools_openapi_operation_ids():
    """Verify all 11 tool endpoints are present in OpenAPI spec with exact operation IDs."""
    schema = app.openapi()
    paths = schema.get("paths", {})

    found_tool_operation_ids = set()
    for path, methods in paths.items():
        if path.startswith("/api/tools/"):
            for method, details in methods.items():
                if method.lower() == "post":
                    op_id = details.get("operationId")
                    if op_id:
                        found_tool_operation_ids.add(op_id)

    assert found_tool_operation_ids == EXPECTED_TOOL_OPERATION_IDS
    assert len(found_tool_operation_ids) == 11


def test_search_knowledge_endpoint():
    """Verify POST /api/tools/search_knowledge executes hybrid retrieval and validates user_id."""
    payload = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "query": "Explain paging in operating systems",
        "course_id": "course-cs-301",
        "subject_id": "subject-os",
        "top_k": 3,
    }
    response = client.post("/api/tools/search_knowledge", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) >= 1
    assert "paging" in data["results"][0]["content"].lower()

    # Empty user_id validation
    bad_payload = {**payload, "user_id": ""}
    bad_res = client.post("/api/tools/search_knowledge", json=bad_payload)
    assert bad_res.status_code == 400


def test_summarize_document_endpoint():
    """Verify POST /api/tools/summarize_document generates summary."""
    payload = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "document_id": "doc-ostep-vm",
        "mode": "concise",
    }
    response = client.post("/api/tools/summarize_document", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == "doc-ostep-vm"
    assert "summary" in data


def test_generate_and_submit_quiz_endpoints():
    """Verify quiz generation and submission endpoints."""
    # 1. generate_quiz
    gen_payload = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "subject_id": "subject-os",
        "topic_ids": ["paging", "virtual-memory"],
        "difficulty": "medium",
        "count": 5,
    }
    gen_res = client.post("/api/tools/generate_quiz", json=gen_payload)
    assert gen_res.status_code == 200
    quiz_data = gen_res.json()
    assert "quiz_id" in quiz_data
    assert len(quiz_data["questions"]) == 5

    # 2. submit_quiz
    sub_payload = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "quiz_id": quiz_data["quiz_id"],
        "answers": {"q1": "A", "q2": "B"},
    }
    sub_res = client.post("/api/tools/submit_quiz", json=sub_payload)
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["status"] == "graded"
    assert "score_percentage" in sub_data


def test_assessment_metrics_endpoints():
    """Verify get_performance and get_weak_topics endpoints."""
    uid = "00000000-0000-0000-0000-000000000001"

    # get_performance
    perf_res = client.post("/api/tools/get_performance", json={"user_id": uid, "subject_id": "subject-os"})
    assert perf_res.status_code == 200
    assert "average_quiz_score" in perf_res.json()

    # get_weak_topics
    weak_res = client.post("/api/tools/get_weak_topics", json={"user_id": uid, "subject_id": "subject-os"})
    assert weak_res.status_code == 200
    assert "weak_topics" in weak_res.json()
    assert isinstance(weak_res.json()["weak_topics"], list)


def test_study_intelligence_endpoints():
    """Verify get_progress, get_upcoming_exams, create_study_plan, get_today_plan, generate_weekly_report."""
    uid = "00000000-0000-0000-0000-000000000001"

    # get_progress
    prog_res = client.post("/api/tools/get_progress", json={"user_id": uid, "course_id": "cs-301"})
    assert prog_res.status_code == 200
    assert "completion_percentage" in prog_res.json()

    # get_upcoming_exams
    exam_res = client.post("/api/tools/get_upcoming_exams", json={"user_id": uid})
    assert exam_res.status_code == 200
    assert "exams" in exam_res.json()

    # create_study_plan
    plan_res = client.post(
        "/api/tools/create_study_plan",
        json={"user_id": uid, "start_date": "2026-10-01", "end_date": "2026-10-15"},
    )
    assert plan_res.status_code == 200
    assert "daily_schedule" in plan_res.json()

    # get_today_plan
    today_res = client.post("/api/tools/get_today_plan", json={"user_id": uid})
    assert today_res.status_code == 200
    assert "tasks" in today_res.json()

    # generate_weekly_report
    rep_res = client.post(
        "/api/tools/generate_weekly_report",
        json={"user_id": uid, "week_start": "2026-09-14", "week_end": "2026-09-20"},
    )
    assert rep_res.status_code == 200
    assert "total_study_hours" in rep_res.json()


def test_generate_quiz_binary_search_grounded():
    """Verify Foundry request for binary search quiz produces grounded questions with sources."""
    payload = {
        "user_id": "demo-user-001",
        "subject_id": None,
        "topic_ids": ["binary search"],
        "difficulty": "medium",
        "count": 3,
    }
    response = client.post("/api/tools/generate_quiz", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["quiz_id"] == "quiz-binary-01"
    assert data["subject_id"] is None
    assert data["count"] == 3
    assert len(data["questions"]) == 3

    for q in data["questions"]:
        assert "id" in q
        assert "question" in q and len(q["question"]) > 10
        assert "options" in q and len(q["options"]) == 4
        assert "correct_answer" in q and len(q["correct_answer"]) > 0
        assert "explanation" in q and len(q["explanation"]) > 10
        assert "source" in q
        assert "chunk_id" in q["source"]
        assert "document_title" in q["source"]
        assert "filename" in q["source"]
        assert "page_number" in q["source"]

    # Verify first question is about sorted array prerequisite
    first_q = data["questions"][0]
    assert "sorted" in first_q["question"].lower() or any("sorted" in opt.lower() for opt in first_q["options"])


def test_generate_quiz_insufficient_material():
    """Verify requesting an unsupported topic returns clear insufficient material response."""
    payload = {
        "user_id": "demo-user-001",
        "subject_id": None,
        "topic_ids": ["quantum teleportation"],
        "difficulty": "medium",
        "count": 3,
    }
    response = client.post("/api/tools/generate_quiz", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["quiz_id"] is None
    assert data["status"] == "insufficient_material"
    assert data["count"] == 0
    assert len(data["questions"]) == 0
    assert "insufficient study material" in data["message"].lower()


def test_submit_quiz_grading_all_correct():
    """Verify submit_quiz grades 100% when all answers are correct against stored quiz."""
    gen_payload = {
        "user_id": "demo-user-001",
        "subject_id": None,
        "topic_ids": ["binary search"],
        "difficulty": "medium",
        "count": 3,
    }
    gen_res = client.post("/api/tools/generate_quiz", json=gen_payload)
    assert gen_res.status_code == 200
    quiz_id = gen_res.json()["quiz_id"]

    sub_payload = {
        "user_id": "demo-user-001",
        "quiz_id": quiz_id,
        "answers": {"1": "A", "2": "B", "3": "B"},
    }
    sub_res = client.post("/api/tools/submit_quiz", json=sub_payload)
    assert sub_res.status_code == 200
    data = sub_res.json()
    assert data["quiz_id"] == quiz_id
    assert data["status"] == "graded"
    assert data["total_questions"] == 3
    assert data["correct_answers"] == 3
    assert data["score_percentage"] == 100


def test_submit_quiz_grading_all_wrong():
    """Verify submit_quiz grades 0% when all answers are incorrect."""
    gen_payload = {
        "user_id": "demo-user-001",
        "subject_id": None,
        "topic_ids": ["binary search"],
        "difficulty": "medium",
        "count": 3,
    }
    gen_res = client.post("/api/tools/generate_quiz", json=gen_payload)
    quiz_id = gen_res.json()["quiz_id"]

    sub_payload = {
        "user_id": "demo-user-001",
        "quiz_id": quiz_id,
        "answers": {"q1": "D", "q2": "D", "q3": "D"},
    }
    sub_res = client.post("/api/tools/submit_quiz", json=sub_payload)
    assert sub_res.status_code == 200
    data = sub_res.json()
    assert data["status"] == "graded"
    assert data["total_questions"] == 3
    assert data["correct_answers"] == 0
    assert data["score_percentage"] == 0


def test_submit_quiz_grading_mixed_answers():
    """Verify submit_quiz computes correct percentage for mixed answers."""
    gen_payload = {
        "user_id": "demo-user-001",
        "subject_id": None,
        "topic_ids": ["binary search"],
        "difficulty": "medium",
        "count": 3,
    }
    gen_res = client.post("/api/tools/generate_quiz", json=gen_payload)
    quiz_id = gen_res.json()["quiz_id"]

    # 2 correct (q1: A, q2: B), 1 wrong (q3: D) -> 2/3 = 66.7%
    sub_payload = {
        "user_id": "demo-user-001",
        "quiz_id": quiz_id,
        "answers": ["A", "B", "D"],
    }
    sub_res = client.post("/api/tools/submit_quiz", json=sub_payload)
    assert sub_res.status_code == 200
    data = sub_res.json()
    assert data["status"] == "graded"
    assert data["total_questions"] == 3
    assert data["correct_answers"] == 2
    assert data["score_percentage"] == 66.7


def test_submit_quiz_unknown_quiz_id():
    """Verify submit_quiz returns 404 for unknown quiz_id."""
    sub_payload = {
        "user_id": "demo-user-001",
        "quiz_id": "non-existent-quiz-999",
        "answers": {"1": "A"},
    }
    sub_res = client.post("/api/tools/submit_quiz", json=sub_payload)
    assert sub_res.status_code == 404
    assert "not found" in sub_res.json()["detail"].lower()


def test_submit_quiz_user_access_control():
    """Verify submit_quiz enforces user ownership on stored quizzes."""
    gen_payload = {
        "user_id": "demo-user-001",
        "subject_id": None,
        "topic_ids": ["binary search"],
        "difficulty": "medium",
        "count": 3,
    }
    gen_res = client.post("/api/tools/generate_quiz", json=gen_payload)
    quiz_id = gen_res.json()["quiz_id"]

    # Attempt submission with different user_id
    sub_payload = {
        "user_id": "intruder-user-999",
        "quiz_id": quiz_id,
        "answers": {"1": "A", "2": "B", "3": "B"},
    }
    sub_res = client.post("/api/tools/submit_quiz", json=sub_payload)
    assert sub_res.status_code == 403
    assert "permission" in sub_res.json()["detail"].lower()


def test_multiple_fresh_binary_search_quizzes_no_duplicate_wording():
    """Verify consecutive 3-question requests produce distinct grounded quizzes without duplicate wording."""
    payload = {
        "user_id": "fresh-user-001",
        "subject_id": None,
        "topic_ids": ["binary search"],
        "difficulty": "medium",
        "count": 3,
    }

    # Request Quiz 1
    res1 = client.post("/api/tools/generate_quiz", json=payload)
    assert res1.status_code == 200
    quiz1 = res1.json()
    assert quiz1["count"] == 3
    assert len(quiz1["questions"]) == 3
    assert quiz1["quiz_id"] is not None

    # Request Quiz 2 (fresh quiz request)
    res2 = client.post("/api/tools/generate_quiz", json=payload)
    assert res2.status_code == 200
    quiz2 = res2.json()
    assert quiz2["count"] == 3
    assert len(quiz2["questions"]) == 3
    assert quiz2["quiz_id"] is not None
    assert quiz1["quiz_id"] != quiz2["quiz_id"]

    # Check question texts have NO exact duplicates across Quiz 1 and Quiz 2
    q_texts_1 = {q["question"].strip() for q in quiz1["questions"]}
    q_texts_2 = {q["question"].strip() for q in quiz2["questions"]}
    overlap = q_texts_1.intersection(q_texts_2)
    assert len(overlap) == 0, f"Found duplicate question wording across quizzes: {overlap}"

    # Verify all questions in both quizzes remain grounded with valid sources and 4 options
    for q in quiz1["questions"] + quiz2["questions"]:
        assert len(q["options"]) == 4
        assert q["correct_answer"].startswith(("A)", "B)", "C)", "D)"))
        assert len(q["explanation"]) > 10
        assert "chunk-dsa-bs" in q["source"]["chunk_id"]
        assert q["source"]["filename"] == "dsa_searching_binary_search.pdf"

    # Submit all correct answers for Quiz 2 and verify 100% grade
    correct_answers_quiz2 = {q["id"]: q["correct_answer"] for q in quiz2["questions"]}
    sub_res = client.post(
        "/api/tools/submit_quiz",
        json={
            "user_id": "fresh-user-001",
            "quiz_id": quiz2["quiz_id"],
            "answers": correct_answers_quiz2,
        },
    )
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["status"] == "graded"
    assert sub_data["total_questions"] == 3
    assert sub_data["correct_answers"] == 3
    assert sub_data["score_percentage"] == 100


def test_generate_quiz_topic_variation_supported():
    """Verify hyphenated or mixed case binary search topic queries are supported."""
    payload = {
        "user_id": "demo-user-001",
        "subject_id": None,
        "topic_ids": ["binary-search"],
        "difficulty": "medium",
        "count": 3,
    }
    response = client.post("/api/tools/generate_quiz", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] != "insufficient_material" if "status" in data else True
    assert len(data["questions"]) == 3
    for q in data["questions"]:
        assert "chunk-dsa-bs" in q["source"]["chunk_id"]


def test_generate_quiz_unsupported_topic_insufficient_material():
    """Verify truly unsupported topics return status=insufficient_material."""
    payload = {
        "user_id": "demo-user-001",
        "subject_id": None,
        "topic_ids": ["quantum cryptography protocols"],
        "difficulty": "hard",
        "count": 3,
    }
    response = client.post("/api/tools/generate_quiz", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["quiz_id"] is None
    assert data["status"] == "insufficient_material"
    assert data["count"] == 0
    assert len(data["questions"]) == 0
    assert "insufficient study material" in data["message"].lower()


def test_summarize_document_grounded_content_and_sources():
    """Verify summarize_document retrieves actual document chunks and returns grounded content with sources."""
    # 1. Test Operating Systems document in concise mode
    res_os = client.post(
        "/api/tools/summarize_document",
        json={"user_id": "demo-user-001", "document_id": "doc-ostep-vm", "mode": "concise"},
    )
    assert res_os.status_code == 200
    data_os = res_os.json()
    assert data_os["status"] == "success"
    assert data_os["document_id"] == "doc-ostep-vm"
    assert data_os["document_title"] == "Operating Systems Concepts: Virtual Memory"
    assert data_os["filename"] == "os_concepts_ch8_paging.pdf"
    assert len(data_os["summary"]) > 50
    # Must NOT be the old placeholder
    assert "Key concepts and study highlights." not in data_os["summary"]
    # Verify grounded content
    assert "paging" in data_os["summary"].lower()
    assert "fragmentation" in data_os["summary"].lower()
    # Verify sources
    assert len(data_os["sources"]) >= 2
    assert data_os["sources"][0]["chunk_id"] == "chunk-os-18-01"
    assert data_os["sources"][0]["page_number"] == 324

    # 2. Test DSA Binary Search document in detailed and bullet_points modes
    res_dsa = client.post(
        "/api/tools/summarize_document",
        json={"user_id": "demo-user-001", "document_id": "doc-dsa-search", "mode": "detailed"},
    )
    assert res_dsa.status_code == 200
    data_dsa = res_dsa.json()
    assert data_dsa["status"] == "success"
    assert "binary search" in data_dsa["summary"].lower()
    assert "o(log n)" in data_dsa["summary"].lower() or "logarithmic" in data_dsa["summary"].lower()
    assert "overflow" in data_dsa["summary"].lower()
    assert len(data_dsa["sources"]) == 3
    assert data_dsa["sources"][0]["filename"] == "dsa_searching_binary_search.pdf"

    # 3. Test bullet_points mode
    res_bullets = client.post(
        "/api/tools/summarize_document",
        json={"user_id": "demo-user-001", "document_id": "doc-dsa-search", "mode": "bullet_points"},
    )
    assert res_bullets.status_code == 200
    assert "•" in res_bullets.json()["summary"]


def test_summarize_document_not_found_response():
    """Verify summarize_document returns clear not_found response instead of inventing a summary."""
    res = client.post(
        "/api/tools/summarize_document",
        json={"user_id": "demo-user-001", "document_id": "non-existent-doc-999", "mode": "concise"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "not_found"
    assert data["summary"] is None
    assert "not found" in data["message"].lower()
    assert len(data["sources"]) == 0


def test_create_study_plan_explicit_dates():
    """Verify create_study_plan uses explicit dates provided by student and builds day-by-day schedule."""
    payload = {
        "user_id": "demo-user-001",
        "start_date": "2026-09-22",
        "end_date": "2026-09-28",
    }
    res = client.post("/api/tools/create_study_plan", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "created"
    assert data["start_date"] == "2026-09-22"
    assert data["end_date"] == "2026-09-28"
    assert data["duration_days"] == 7
    assert len(data["daily_schedule"]) == 7
    assert data["daily_schedule"][0]["day"] == "2026-09-22"
    assert data["daily_schedule"][-1]["day"] == "2026-09-28"
    assert "focus" in data["daily_schedule"][0]
    assert data["daily_schedule"][0]["hours"] > 0


def test_create_study_plan_duration_deterministic_from_current_date():
    """Verify 7-day study plan request with duration calculates date range deterministically from current date."""
    import datetime

    today = datetime.date.today()
    expected_start = today.isoformat()
    expected_end = (today + datetime.timedelta(days=6)).isoformat()

    payload = {
        "user_id": "demo-user-001",
        "duration_days": 7,
    }
    res = client.post("/api/tools/create_study_plan", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "created"
    assert data["start_date"] == expected_start
    assert data["end_date"] == expected_end
    assert data["duration_days"] == 7
    assert len(data["daily_schedule"]) == 7
    # Verify no stale June 2026 date was used
    assert not data["start_date"].startswith("2026-06")


def test_create_study_plan_custom_reference_date():
    """Verify deterministic calculation when reference current_date is provided."""
    payload = {
        "user_id": "demo-user-001",
        "current_date": "2026-09-22",
        "duration_days": 7,
    }
    res = client.post("/api/tools/create_study_plan", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "created"
    assert data["start_date"] == "2026-09-22"
    assert data["end_date"] == "2026-09-28"
    assert data["duration_days"] == 7
    assert len(data["daily_schedule"]) == 7


def test_create_study_plan_missing_dates_asks_for_them():
    """Verify that if dates cannot be determined safely, tool asks for them instead of inventing dates."""
    payload = {
        "user_id": "demo-user-001",
    }
    res = client.post("/api/tools/create_study_plan", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "needs_dates"
    assert data["plan_id"] is None
    assert data["start_date"] is None
    assert data["end_date"] is None
    assert len(data["daily_schedule"]) == 0
    assert "specify the start date or duration" in data["message"].lower()


def test_search_and_summarize_syllabus_consistency():
    """Verify search for syllabus.pdf returns doc-gen-course and summarize_document successfully grounds it."""
    # 1. Search for syllabus.pdf and get doc-gen-course
    search_res = client.post(
        "/api/tools/search_knowledge",
        json={"user_id": "demo-user-001", "query": "syllabus.pdf"},
    )
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert "results" in search_data and len(search_data["results"]) > 0
    matched_doc = search_data["results"][0]
    assert matched_doc["document_id"] == "doc-gen-course"
    assert matched_doc["filename"] == "syllabus.pdf"

    # 2. Call summarize_document with doc-gen-course
    sum_res = client.post(
        "/api/tools/summarize_document",
        json={
            "user_id": "demo-user-001",
            "document_id": matched_doc["document_id"],
            "mode": "concise",
        },
    )
    assert sum_res.status_code == 200
    sum_data = sum_res.json()

    # 3. Verify that the document is found and the returned summary contains actual grounded content/source information
    assert sum_data["status"] == "success"
    assert sum_data["document_id"] == "doc-gen-course"
    assert sum_data["filename"] == "syllabus.pdf"
    assert sum_data["summary"] is not None
    assert len(sum_data["summary"]) > 50
    # Must contain actual grounded content from syllabus.pdf
    assert "syllabus" in sum_data["summary"].lower() or "schedule" in sum_data["summary"].lower() or "grading" in sum_data["summary"].lower()
    # Must contain source information
    assert len(sum_data["sources"]) > 0
    assert sum_data["sources"][0]["chunk_id"] == "chunk-gen-001"
    assert sum_data["sources"][0]["filename"] == "syllabus.pdf"
    assert sum_data["sources"][0]["section_title"] == "Course Overview & Schedule"







def test_tools_unauthenticated_rejection():
    """Verify all tools reject unauthenticated requests with 401."""
    unauth_client = TestClient(app)
    tools = [
        ("/api/tools/search_knowledge", {"query": "test"}),
        ("/api/tools/generate_quiz", {"subject_id": "test", "difficulty": "medium", "count": 3}),
        ("/api/tools/get_performance", {}),
        ("/api/tools/get_weak_topics", {}),
        ("/api/tools/get_progress", {}),
        ("/api/tools/get_upcoming_exams", {}),
        ("/api/tools/get_today_plan", {}),
    ]
    for path, payload in tools:
        res = unauth_client.post(path, json=payload)
        assert res.status_code == 401, f"{path} did not reject unauthenticated with 401"


def test_tools_user_id_mismatch_rejection():
    """Verify tools reject requests with mismatched user_id with 403 Forbidden."""
    token = create_access_token({"sub": "user-legit", "email": "legit@test.local"})
    headers = {"Authorization": f"Bearer {token}"}
    with SessionLocal() as db:
        if not db.query(User).filter(User.user_id == "user-legit").first():
            db.add(User(user_id="user-legit", email="legit@test.local", name="Legit", password_hash="dummy"))
            db.commit()
    res = client.post("/api/tools/search_knowledge", json={
        "user_id": "different-user-9999",
        "query": "Explain paging",
    }, headers=headers)
    assert res.status_code == 403
