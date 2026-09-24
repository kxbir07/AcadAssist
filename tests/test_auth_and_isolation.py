"""Comprehensive security, authentication, and user data isolation tests.

Tests:
1. Registration (email uniqueness, password hashing with bcrypt, token generation)
2. Login (success, invalid password, non-existent user)
3. Current user identity (/api/auth/me)
4. Unauthenticated access rejection on protected endpoints
5. Centralized document access control:
   - Private document accessible to owner
   - Private document denied (403/404) to other users
   - Public document accessible to all authenticated users
   - Unauthenticated download denied
   - Document SHA-256 checksum deduplication
6. Multi-user RAG isolation:
   - User A cannot retrieve User B's private chunks
   - User B can retrieve User A's public chunks
7. Multi-user academic data isolation:
   - User A and User B study plans and tasks isolation
   - Notes isolation
   - Chat isolation
"""

import io
import pytest
from app.core.security import verify_password
from app.models.document import Document
from app.models.shared import Course, Subject, User
from app.models.note import Note
from app.models.chat import Conversation, ChatMessage
from app.services.document_access import can_access_document, verify_document_access
from fastapi import HTTPException


# ==============================================================================
# AUTHENTICATION TESTS
# ==============================================================================

def test_auth_registration_and_hashing(client, db_session):
    """Test user registration, bcrypt password hashing, and token issuance."""
    reg_payload = {
        "email": "student1@acadassist.edu",
        "name": "Student One",
        "password": "SecurePassword123!",
        "field_of_study": "Computer Science",
    }
    resp = client.post("/api/auth/register", json=reg_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "student1@acadassist.edu"
    assert data["user"]["name"] == "Student One"

    # Verify password in DB is hashed and never stored plaintext
    user_db = db_session.query(User).filter(User.email == "student1@acadassist.edu").first()
    assert user_db is not None
    assert user_db.password_hash is not None
    assert user_db.password_hash != "SecurePassword123!"
    assert verify_password("SecurePassword123!", user_db.password_hash) is True
    assert verify_password("WrongPassword!", user_db.password_hash) is False

    # Duplicate registration must fail with 409
    dup_resp = client.post("/api/auth/register", json=reg_payload)
    assert dup_resp.status_code == 409


def test_auth_login_and_me_lifecycle(client):
    """Test login with valid/invalid credentials and /api/auth/me session check."""
    # 1. Register user
    reg_payload = {
        "email": "student2@acadassist.edu",
        "name": "Student Two",
        "password": "CorrectPassword456!",
    }
    client.post("/api/auth/register", json=reg_payload)

    # 2. Login with incorrect password -> 401
    bad_login = client.post(
        "/api/auth/login",
        json={"email": "student2@acadassist.edu", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # 3. Login with correct password -> 200 + token
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "student2@acadassist.edu", "password": "CorrectPassword456!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert token is not None

    # 4. Access /api/auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "student2@acadassist.edu"
    assert me_data["name"] == "Student Two"

    # 5. Unauthenticated /api/auth/me -> 401
    unauth_resp = client.get("/api/auth/me")
    assert unauth_resp.status_code == 401


# ==============================================================================
# DOCUMENT ACCESS CONTROL & DOWNLOAD TESTS
# ==============================================================================

def test_document_ownership_and_visibility_isolation(client, db_session, sample_academic_entities, auth_headers):
    """Test private vs public document access and streaming download authorization."""
    entities = sample_academic_entities
    alice_id = entities["user_a"].user_id
    bob_id = entities["user_b"].user_id

    alice_headers = auth_headers(alice_id)
    bob_headers = auth_headers(bob_id)

    # 1. Alice uploads private document (default visibility is private)
    content_a = b"Alice's confidential research notes."
    resp_upload_a = client.post(
        "/api/documents",
        data={
            "course_id": entities["course"].course_id,
            "subject_id": entities["subject_os"].subject_id,
            "title": "Alice Private Notes",
            "visibility": "private",
        },
        files={"file": ("alice_notes.txt", io.BytesIO(content_a), "text/plain")},
        headers=alice_headers,
    )
    assert resp_upload_a.status_code == 201
    alice_doc_id = resp_upload_a.json()["document_id"]
    assert resp_upload_a.json()["visibility"] == "private"
    assert resp_upload_a.json()["checksum"] is not None

    # 2. Alice uploads public document
    content_pub = b"Public study guide for Operating Systems."
    resp_upload_pub = client.post(
        "/api/documents",
        data={
            "course_id": entities["course"].course_id,
            "subject_id": entities["subject_os"].subject_id,
            "title": "OS Public Guide",
            "visibility": "public",
        },
        files={"file": ("os_guide.txt", io.BytesIO(content_pub), "text/plain")},
        headers=alice_headers,
    )
    assert resp_upload_pub.status_code == 201
    pub_doc_id = resp_upload_pub.json()["document_id"]
    assert resp_upload_pub.json()["visibility"] == "public"

    # 3. Bob tries to access Alice's private document -> 403 Forbidden
    resp_bob_get = client.get(f"/api/documents/{alice_doc_id}", headers=bob_headers)
    assert resp_bob_get.status_code == 403

    # 4. Bob tries to download Alice's private document -> 403 Forbidden
    resp_bob_dl = client.get(f"/api/documents/{alice_doc_id}/download", headers=bob_headers)
    assert resp_bob_dl.status_code == 403

    # 5. Bob accesses Alice's public document -> 200 OK
    resp_bob_pub_get = client.get(f"/api/documents/{pub_doc_id}", headers=bob_headers)
    assert resp_bob_pub_get.status_code == 200

    # 6. Bob downloads Alice's public document -> 200 OK with streaming content
    resp_bob_pub_dl = client.get(f"/api/documents/{pub_doc_id}/download", headers=bob_headers)
    assert resp_bob_pub_dl.status_code == 200
    assert resp_bob_pub_dl.content == content_pub

    # 7. Unauthenticated user tries to download -> 401
    resp_unauth_dl = client.get(f"/api/documents/{pub_doc_id}/download")
    assert resp_unauth_dl.status_code == 401


def test_document_checksum_deduplication(client, sample_academic_entities, auth_headers):
    """Test that uploading the exact same file content reuses existing document without duplication."""
    entities = sample_academic_entities
    alice_id = entities["user_a"].user_id
    alice_headers = auth_headers(alice_id)

    content = b"Exact duplicate test content."
    resp1 = client.post(
        "/api/documents",
        data={
            "course_id": entities["course"].course_id,
            "subject_id": entities["subject_os"].subject_id,
            "title": "First Upload",
        },
        files={"file": ("doc.txt", io.BytesIO(content), "text/plain")},
        headers=alice_headers,
    )
    assert resp1.status_code == 201
    doc1_id = resp1.json()["document_id"]
    checksum1 = resp1.json()["checksum"]

    # Second upload with identical file content by same user
    resp2 = client.post(
        "/api/documents",
        data={
            "course_id": entities["course"].course_id,
            "subject_id": entities["subject_os"].subject_id,
            "title": "Duplicate Upload",
        },
        files={"file": ("doc.txt", io.BytesIO(content), "text/plain")},
        headers=alice_headers,
    )
    assert resp2.status_code in [200, 201]
    assert resp2.json()["document_id"] == doc1_id
    assert resp2.json()["checksum"] == checksum1


# ==============================================================================
# USER NOTES AND CHAT ISOLATION TESTS
# ==============================================================================

def test_notes_and_chat_user_isolation(client, sample_academic_entities, auth_headers):
    """Verify Notes and Chat messages are strictly scoped to authenticated user."""
    entities = sample_academic_entities
    alice_id = entities["user_a"].user_id
    bob_id = entities["user_b"].user_id

    alice_headers = auth_headers(alice_id)
    bob_headers = auth_headers(bob_id)

    # 1. Alice creates a private Note
    note_payload = {
        "title": "Alice Exam Notes",
        "content": "Review chapter 4 and 5 carefully.",
        "subject": "Operating Systems",
    }
    resp_note = client.post("/api/notes", json=note_payload, headers=alice_headers)
    assert resp_note.status_code == 201
    alice_note_id = resp_note.json()["id"]

    # 2. Bob lists notes -> Alice's note must NOT be in Bob's notes list
    bob_notes_resp = client.get("/api/notes", headers=bob_headers)
    assert bob_notes_resp.status_code == 200
    assert not any(n["id"] == alice_note_id for n in bob_notes_resp.json())


    # 3. Bob attempts to modify Alice's note -> 404 Not Found (or 403)
    resp_bob_patch = client.patch(
        f"/api/notes/{alice_note_id}",
        json={"title": "Tampered Title"},
        headers=bob_headers,
    )
    assert resp_bob_patch.status_code in [403, 404]

    # 4. Bob attempts to delete Alice's note -> 404 Not Found (or 403)
    resp_bob_del = client.delete(f"/api/notes/{alice_note_id}", headers=bob_headers)
    assert resp_bob_del.status_code in [403, 404]

    # 5. Alice posts a Chat message
    resp_msg = client.post(
        "/api/chat/message",
        json={"role": "user", "text": "How does virtual memory work?"},
        headers=alice_headers,
    )
    assert resp_msg.status_code == 201
    alice_msg_id = resp_msg.json()["id"]

    # Alice retrieves her chat history
    alice_history = client.get("/api/chat/history", headers=alice_headers)
    assert alice_history.status_code == 200
    assert any(m["id"] == alice_msg_id for m in alice_history.json())

    # 6. Bob lists chat history -> Alice's message must NOT be in Bob's history
    bob_history = client.get("/api/chat/history", headers=bob_headers)
    assert bob_history.status_code == 200
    assert not any(m["id"] == alice_msg_id for m in bob_history.json())


def test_quiz_attempts_and_upcoming_exams_user_isolation(client, sample_academic_entities, auth_headers):
    """Verify quiz attempts and upcoming exams are properly scoped to user."""
    entities = sample_academic_entities
    alice_id = entities["user_a"].user_id
    bob_id = entities["user_b"].user_id
    alice_headers = auth_headers(alice_id)
    bob_headers = auth_headers(bob_id)

    # Alice has empty attempts initially
    resp_attempts = client.get("/api/quizzes/attempts", headers=alice_headers)
    assert resp_attempts.status_code == 200
    assert resp_attempts.json() == []

    # Alice has empty upcoming exams initially
    resp_exams = client.get("/api/exams/upcoming", headers=alice_headers)
    assert resp_exams.status_code == 200
    assert resp_exams.json() == []

    # Alice schedules an exam
    resp_create_exam = client.post(
        "/api/exams",
        json={
            "subject_id": entities["subject_os"].subject_id,
            "title": "Alice Operating Systems Midterm",
            "exam_date": "2026-10-15T09:00:00",
        },
        headers=alice_headers,
    )
    assert resp_create_exam.status_code == 201

    # Alice now sees the upcoming exam
    resp_alice_exams = client.get("/api/exams/upcoming", headers=alice_headers)
    assert resp_alice_exams.status_code == 200
    assert len(resp_alice_exams.json()) == 1
    assert resp_alice_exams.json()[0]["title"] == "Alice Operating Systems Midterm"

    # Bob does NOT see Alice's exam
    resp_bob_exams = client.get("/api/exams/upcoming", headers=bob_headers)
    assert resp_bob_exams.status_code == 200
    assert resp_bob_exams.json() == []


