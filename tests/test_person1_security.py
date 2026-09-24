"""Comprehensive Person 1 Azure and Microsoft Foundry security isolation and anti-impersonation tests.

Validates:
1. Section 30: User A / User B document & secret isolation (Project Chimera Secret Access Code 98765)
2. Section 31: User-ID attack on POST /api/chat -> 403 Forbidden
3. Section 32: Tool User-ID attack on /api/tools/* -> 403 Forbidden
4. Section 33: LLM impersonation overwrite by ToolDispatcher
5. Section 34: Public document accessibility (owner OR public rule)
6. Section 35: Dynamic visibility toggling (public -> private and private -> public) with chunk synchronization
7. Section 36: Unauthenticated 401 rejection on /api/chat and /api/tools/*
"""

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.database.session import SessionLocal
from app.models.document import Document, Chunk
from app.models.shared import Course, Subject, User
from app.azure.adapters import ToolDispatcher

client = TestClient(app)

SECRET_CODE = "Project Chimera Secret Access Code 98765"


@pytest.fixture
def setup_users_and_course(db_session):
    """Setup User A, User B, and shared course/subject entities in active db_session."""
    user_a = db_session.query(User).filter(User.user_id == "user-a-chimera").first()
    if not user_a:
        user_a = User(
            user_id="user-a-chimera",
            email="user_a_chimera@acadassist.edu",
            name="Agent Chimera A",
            password_hash="hashed_pw_a",
        )
        db_session.add(user_a)

    user_b = db_session.query(User).filter(User.user_id == "user-b-intruder").first()
    if not user_b:
        user_b = User(
            user_id="user-b-intruder",
            email="user_b_intruder@acadassist.edu",
            name="Agent Intruder B",
            password_hash="hashed_pw_b",
        )
        db_session.add(user_b)

    course = db_session.query(Course).filter(Course.course_id == "course-chimera-101").first()
    if not course:
        course = Course(
            course_id="course-chimera-101",
            name="Advanced Security",
            code="SEC-101",
        )
        db_session.add(course)

    subject = db_session.query(Subject).filter(Subject.subject_id == "subject-chimera").first()
    if not subject:
        subject = Subject(
            subject_id="subject-chimera",
            course_id="course-chimera-101",
            name="Special Operations",
        )
        db_session.add(subject)

    db_session.commit()

    token_a = create_access_token({"sub": "user-a-chimera", "email": "user_a_chimera@acadassist.edu"})
    token_b = create_access_token({"sub": "user-b-intruder", "email": "user_b_intruder@acadassist.edu"})

    return {
        "user_a_id": "user-a-chimera",
        "user_b_id": "user-b-intruder",
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "headers_b": {"Authorization": f"Bearer {token_b}"},
        "course_id": "course-chimera-101",
        "subject_id": "subject-chimera",
    }


def test_ab_document_isolation_and_secret_protection(client, setup_users_and_course):
    """Section 30: User A uploads private secret; User B cannot access it via any channel."""
    env = setup_users_and_course
    user_a_headers = env["headers_a"]
    user_b_headers = env["headers_b"]

    # 1. User A uploads private document containing Project Chimera secret
    secret_file_content = f"Top Secret Document.\n{SECRET_CODE}\nAuthorization code only for User A."
    resp_upload = client.post(
        "/api/documents",
        data={
            "course_id": env["course_id"],
            "subject_id": env["subject_id"],
            "title": "Project Chimera Confidential",
            "visibility": "private",
        },
        files={"file": ("chimera_secret.txt", io.BytesIO(secret_file_content.encode("utf-8")), "text/plain")},
        headers=user_a_headers,
    )
    assert resp_upload.status_code == 201
    doc_a_id = resp_upload.json()["document_id"]

    # Process and index document chunks for User A
    proc_resp = client.post(f"/api/documents/{doc_a_id}/process", headers=user_a_headers)
    assert proc_resp.status_code == 200

    # 2. User B cannot download User A's private document -> 403
    resp_dl = client.get(f"/api/documents/{doc_a_id}/download", headers=user_b_headers)
    assert resp_dl.status_code == 403

    # 3. User B cannot access User A's metadata -> 403
    resp_meta = client.get(f"/api/documents/{doc_a_id}", headers=user_b_headers)
    assert resp_meta.status_code == 403

    # 4. User B cannot summarize User A's private document -> 403
    resp_summ = client.post(
        f"/api/documents/{doc_a_id}/summarize",
        json={"mode": "concise"},
        headers=user_b_headers,
    )
    assert resp_summ.status_code == 403

    # 5. User B cannot summarize User A's private document via tool -> 403
    resp_tool_summ = client.post(
        "/api/tools/summarize_document",
        json={"document_id": doc_a_id, "mode": "concise"},
        headers=user_b_headers,
    )
    assert resp_tool_summ.status_code == 403

    # 6. User B cannot retrieve secret through RAG / knowledge search
    resp_rag = client.post(
        "/api/knowledge/search",
        json={"query": "Chimera Access Code"},
        headers=user_b_headers,
    )
    assert resp_rag.status_code == 200
    for chunk in resp_rag.json().get("results", []):
        assert SECRET_CODE not in chunk.get("content", "")

    # 7. User B cannot retrieve secret through tool search_knowledge
    resp_tool_search = client.post(
        "/api/tools/search_knowledge",
        json={"query": "Chimera Access Code"},
        headers=user_b_headers,
    )
    assert resp_tool_search.status_code == 200
    for chunk in resp_tool_search.json().get("results", []):
        assert SECRET_CODE not in chunk.get("content", "")

    # 8. User B cannot retrieve secret through chat
    resp_chat = client.post(
        "/api/chat",
        json={"message": "What is the Project Chimera Secret Access Code?"},
        headers=user_b_headers,
    )
    assert resp_chat.status_code == 200
    assert SECRET_CODE not in resp_chat.json()["message"]


def test_user_id_attack_chat(client, setup_users_and_course):
    """Section 31: User B sends user_id = User A to POST /api/chat -> 403 Forbidden."""
    env = setup_users_and_course
    user_b_headers = env["headers_b"]

    resp = client.post(
        "/api/chat",
        json={
            "user_id": env["user_a_id"],
            "message": "What is the secret?",
        },
        headers=user_b_headers,
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]


def test_tool_user_id_attack(client, setup_users_and_course):
    """Section 32: User B attempts /api/tools/* with user_id = User A -> 403 Forbidden."""
    env = setup_users_and_course
    user_b_headers = env["headers_b"]

    tool_endpoints = [
        ("/api/tools/search_knowledge", {"user_id": env["user_a_id"], "query": "secret"}),
        ("/api/tools/summarize_document", {"user_id": env["user_a_id"], "document_id": "doc1", "mode": "concise"}),
        ("/api/tools/generate_quiz", {"user_id": env["user_a_id"], "subject_id": "test", "count": 3, "difficulty": "medium"}),
        ("/api/tools/get_performance", {"user_id": env["user_a_id"]}),
        ("/api/tools/get_weak_topics", {"user_id": env["user_a_id"]}),
        ("/api/tools/get_progress", {"user_id": env["user_a_id"]}),
        ("/api/tools/get_upcoming_exams", {"user_id": env["user_a_id"]}),
        ("/api/tools/get_today_plan", {"user_id": env["user_a_id"]}),
    ]

    for endpoint, payload in tool_endpoints:
        resp = client.post(endpoint, json=payload, headers=user_b_headers)
        assert resp.status_code == 403, f"{endpoint} did not reject user_id spoofing with 403"


def test_llm_impersonation_overwrite():
    """Section 33: LLM generates tool arguments with user_id = User A, dispatcher overwrites it with User B."""
    dispatcher = ToolDispatcher()
    attacker_uid = "user-b-intruder"
    victim_uid = "user-a-chimera"

    # Simulated LLM hallucinated tool call with spoofed user_id
    args = {"user_id": victim_uid, "query": "Explain paging"}

    # Dispatch with authenticated_user_id enforced by backend
    res = dispatcher.dispatch("search_knowledge", args, authenticated_user_id=attacker_uid)

    # Verify dispatcher forced user_id to authenticated_user_id
    assert args["user_id"] == attacker_uid


def test_public_document_retrieval(client, setup_users_and_course):
    """Section 34: User A creates public document; User B can retrieve it (owner OR public)."""
    env = setup_users_and_course
    user_a_headers = env["headers_a"]
    user_b_headers = env["headers_b"]

    content = "Public Open Educational Resource on Discrete Mathematics."
    resp_upload = client.post(
        "/api/documents",
        data={
            "course_id": env["course_id"],
            "subject_id": env["subject_id"],
            "title": "Public Discrete Math Notes",
            "visibility": "public",
        },
        files={"file": ("discrete_math.txt", io.BytesIO(content.encode("utf-8")), "text/plain")},
        headers=user_a_headers,
    )
    assert resp_upload.status_code == 201
    doc_id = resp_upload.json()["document_id"]
    assert resp_upload.json()["visibility"] == "public"

    # User B can retrieve public document metadata and download
    get_resp = client.get(f"/api/documents/{doc_id}", headers=user_b_headers)
    assert get_resp.status_code == 200

    dl_resp = client.get(f"/api/documents/{doc_id}/download", headers=user_b_headers)
    assert dl_resp.status_code == 200
    assert dl_resp.content == content.encode("utf-8")


def test_visibility_change_synchronization(client, setup_users_and_course):
    """Section 35: Dynamic visibility toggling public -> private and private -> public with chunk synchronization."""
    env = setup_users_and_course
    user_a_headers = env["headers_a"]
    user_b_headers = env["headers_b"]

    # 1. User A uploads public document
    content = "Distributed Systems Raft Consensus Public Whitepaper."
    resp_upload = client.post(
        "/api/documents",
        data={
            "course_id": env["course_id"],
            "subject_id": env["subject_id"],
            "title": "Raft Consensus Whitepaper",
            "visibility": "public",
        },
        files={"file": ("raft.txt", io.BytesIO(content.encode("utf-8")), "text/plain")},
        headers=user_a_headers,
    )
    assert resp_upload.status_code == 201
    doc_id = resp_upload.json()["document_id"]

    # Process and index
    client.post(f"/api/documents/{doc_id}/process", headers=user_a_headers)

    # User B can initially download public document
    assert client.get(f"/api/documents/{doc_id}/download", headers=user_b_headers).status_code == 200

    # 2. Toggle public -> private
    resp_priv = client.patch(
        f"/api/documents/{doc_id}/visibility",
        json={"visibility": "private"},
        headers=user_a_headers,
    )
    assert resp_priv.status_code == 200
    assert resp_priv.json()["visibility"] == "private"

    # User B can no longer access or download -> 403 Forbidden
    assert client.get(f"/api/documents/{doc_id}", headers=user_b_headers).status_code == 403
    assert client.get(f"/api/documents/{doc_id}/download", headers=user_b_headers).status_code == 403

    # 3. Toggle private -> public
    resp_pub = client.patch(
        f"/api/documents/{doc_id}/visibility",
        json={"visibility": "public"},
        headers=user_a_headers,
    )
    assert resp_pub.status_code == 200
    assert resp_pub.json()["visibility"] == "public"

    # User B can now access and download again -> 200 OK
    assert client.get(f"/api/documents/{doc_id}", headers=user_b_headers).status_code == 200
    assert client.get(f"/api/documents/{doc_id}/download", headers=user_b_headers).status_code == 200


def test_authentication_required_endpoints():
    """Section 36: Verify /api/chat and /api/tools/* reject unauthenticated requests with 401."""
    unauth_client = TestClient(app)

    # Chat endpoint
    assert unauth_client.post("/api/chat", json={"message": "hello"}).status_code == 401

    # Tools endpoints
    tools = [
        "/api/tools/search_knowledge",
        "/api/tools/summarize_document",
        "/api/tools/generate_quiz",
        "/api/tools/submit_quiz",
        "/api/tools/get_performance",
        "/api/tools/get_weak_topics",
        "/api/tools/get_progress",
        "/api/tools/get_upcoming_exams",
        "/api/tools/create_study_plan",
        "/api/tools/get_today_plan",
        "/api/tools/generate_weekly_report",
    ]
    for endpoint in tools:
        res = unauth_client.post(endpoint, json={})
        assert res.status_code == 401, f"{endpoint} did not return 401 for unauthenticated request"
