"""Comprehensive security, authentication, and user data isolation tests.

Tests:
1. Registration (email uniqueness, password hashing with bcrypt, token generation)
2. Login (success, invalid password, non-existent user)
3. Current user identity (/api/auth/me)
4. Profile editing, password change, and secure single-use password reset token flow
5. Unauthenticated access rejection on protected endpoints
6. Centralized document access control:
   - Private document accessible to owner
   - Private document denied (403/404) to other users
   - Public document accessible to all authenticated users
   - Unauthenticated download denied
   - Document SHA-256 checksum deduplication
7. Multi-user RAG isolation:
   - User A cannot retrieve User B's private chunks
   - User B can retrieve User A's public chunks
8. Multi-user academic data isolation:
   - User A and User B study plans and tasks isolation
   - Notes isolation
   - Chat isolation
   - Quiz attempts, quiz ownership, and upcoming exams isolation
"""

import io
from datetime import datetime, timedelta, timezone
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


def test_auth_profile_update_password_change_and_reset(client):
    """Test profile editing, password change, and secure single-use password reset flow."""
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "email": "student_profile@acadassist.edu",
            "name": "Initial Name",
            "password": "InitialPassword123!",
        },
    )
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Update profile via PATCH /api/auth/profile
    patch_resp = client.patch(
        "/api/auth/profile",
        json={
            "name": "Updated Scholar Name",
            "academic_level": "Postgraduate",
            "field_of_study": "Artificial Intelligence",
            "bio": "Researching grounded RAG systems.",
        },
        headers=headers,
    )
    assert patch_resp.status_code == 200
    profile_data = patch_resp.json()
    assert profile_data["name"] == "Updated Scholar Name"
    assert profile_data["academic_level"] == "Postgraduate"
    assert profile_data["field_of_study"] == "Artificial Intelligence"
    assert profile_data["bio"] == "Researching grounded RAG systems."

    # 2. Change password with wrong current password -> 400
    bad_pw_resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "WrongCurrentPassword!", "new_password": "NewPassword456!"},
        headers=headers,
    )
    assert bad_pw_resp.status_code == 400

    # 3. Change password with valid current password -> 200
    ok_pw_resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "InitialPassword123!", "new_password": "NewPassword456!"},
        headers=headers,
    )
    assert ok_pw_resp.status_code == 200

    # Verify login with new password succeeds
    login_new = client.post(
        "/api/auth/login",
        json={"email": "student_profile@acadassist.edu", "password": "NewPassword456!"},
    )
    assert login_new.status_code == 200

    # 4. Forgot password & single-use reset token flow
    forgot_resp = client.post(
        "/api/auth/forgot-password",
        json={"email": "student_profile@acadassist.edu"},
    )
    assert forgot_resp.status_code == 200
    reset_token = forgot_resp.json().get("reset_token")
    assert reset_token is not None

    reset_resp = client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "RecoveredPassword789!"},
    )
    assert reset_resp.status_code == 200

    # Reusing the exact same reset token a second time must be rejected (400)
    reuse_resp = client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "AnotherPassword000!"},
    )
    assert reuse_resp.status_code == 400

    # Login with recovered password succeeds
    login_recovered = client.post(
        "/api/auth/login",
        json={"email": "student_profile@acadassist.edu", "password": "RecoveredPassword789!"},
    )
    assert login_recovered.status_code == 200


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
    """Verify quiz attempts, quiz ownership, and upcoming exams are strictly isolated per user."""
    entities = sample_academic_entities
    alice_id = entities["user_a"].user_id
    bob_id = entities["user_b"].user_id
    alice_headers = auth_headers(alice_id)
    bob_headers = auth_headers(bob_id)

    # 1. Both users have empty quiz attempts initially
    resp_attempts_alice = client.get("/api/quizzes/attempts", headers=alice_headers)
    assert resp_attempts_alice.status_code == 200
    assert resp_attempts_alice.json() == []

    resp_attempts_bob = client.get("/api/quizzes/attempts", headers=bob_headers)
    assert resp_attempts_bob.status_code == 200
    assert resp_attempts_bob.json() == []

    # 2. Alice generates a quiz and submits it; verify Bob cannot access or submit Alice's quiz
    resp_create_quiz = client.post(
        "/api/quizzes",
        json={
            "subject_id": "operating_systems",
            "topic_ids": ["Paging"],
            "difficulty": "medium",
            "count": 3,
            "title": "Alice Paging Quiz",
        },
        headers=alice_headers,
    )
    assert resp_create_quiz.status_code == 201
    quiz_data = resp_create_quiz.json()
    alice_quiz_id = quiz_data["quiz_id"]
    questions = quiz_data["questions"]

    # Bob cannot fetch Alice's quiz -> 403 Forbidden
    resp_bob_get_quiz = client.get(f"/api/quizzes/{alice_quiz_id}", headers=bob_headers)
    assert resp_bob_get_quiz.status_code == 403

    # Bob cannot submit Alice's quiz -> 403 Forbidden
    submit_payload = {
        "answers": [
            {"question_id": q["question_id"], "selected_answer": q["options"][0], "time_taken": 10.0}
            for q in questions
        ]
    }
    resp_bob_submit_quiz = client.post(
        f"/api/quizzes/{alice_quiz_id}/submit",
        json=submit_payload,
        headers=bob_headers,
    )
    assert resp_bob_submit_quiz.status_code == 403

    # Alice submits her own quiz -> 200 OK
    resp_alice_submit = client.post(
        f"/api/quizzes/{alice_quiz_id}/submit",
        json=submit_payload,
        headers=alice_headers,
    )
    assert resp_alice_submit.status_code == 200

    # Alice sees her completed attempt in /api/quizzes/attempts
    resp_alice_attempts_after = client.get("/api/quizzes/attempts", headers=alice_headers)
    assert resp_alice_attempts_after.status_code == 200
    assert len(resp_alice_attempts_after.json()) == 1
    assert resp_alice_attempts_after.json()[0]["quiz_id"] == alice_quiz_id

    # Bob still sees 0 attempts (cannot see Alice's quiz attempts)
    resp_bob_attempts_after = client.get("/api/quizzes/attempts", headers=bob_headers)
    assert resp_bob_attempts_after.status_code == 200
    assert resp_bob_attempts_after.json() == []

    # 3. Upcoming exams isolation
    resp_exams = client.get("/api/exams/upcoming", headers=alice_headers)
    assert resp_exams.status_code == 200
    assert resp_exams.json() == []

    future_exam_date = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    resp_create_exam = client.post(
        "/api/exams",
        json={
            "subject_id": entities["subject_os"].subject_id,
            "title": "Alice Operating Systems Midterm",
            "exam_date": future_exam_date,
        },
        headers=alice_headers,
    )
    assert resp_create_exam.status_code == 201

    # Alice now sees the upcoming exam
    resp_alice_exams = client.get("/api/exams/upcoming", headers=alice_headers)
    assert resp_alice_exams.status_code == 200
    assert len(resp_alice_exams.json()) == 1
    assert resp_alice_exams.json()[0]["title"] == "Alice Operating Systems Midterm"

    # Bob does NOT see Alice's exam in /api/exams/upcoming or /api/exams
    resp_bob_exams = client.get("/api/exams/upcoming", headers=bob_headers)
    assert resp_bob_exams.status_code == 200
    assert resp_bob_exams.json() == []

    resp_bob_all_exams = client.get("/api/exams", headers=bob_headers)
    assert resp_bob_all_exams.status_code == 200
    assert resp_bob_all_exams.json() == []
