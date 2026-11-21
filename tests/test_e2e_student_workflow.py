"""
Part 16 — Full End-to-End Student Workflow Verification Suite.
Validates the complete 24-step student lifecycle across authentication,
workspace state persistence, document upload & RAG processing, hybrid search,
document summarization, grounded AI assistant chat with citations, quiz generation,
examination submission & scoring, analytics & weak topics, study planner & tasks,
profile editing, password change, password reset, and user isolation.
"""

from datetime import datetime, timedelta, timezone
import io


def test_complete_24_step_student_workflow(client):
    # 1. Register a new account
    reg_res = client.post(
        "/api/auth/register",
        json={
            "email": "kabir.e2e@acadassist.edu",
            "name": "Kabir E2E Student",
            "password": "InitialPassword123!",
            "academic_level": "B.E. CSE AI & ML",
            "field_of_study": "Computer Science",
        },
    )
    assert reg_res.status_code == 201, reg_res.text
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    user_id = reg_data["user"]["id"]

    # 2. Log in with the registered credentials
    login_res = client.post(
        "/api/auth/login",
        json={
            "email": "kabir.e2e@acadassist.edu",
            "password": "InitialPassword123!",
        },
    )
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Refresh page / verify session via /api/auth/me
    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "kabir.e2e@acadassist.edu"
    assert me_res.json()["id"] == user_id

    # 4. View dashboard & progress baseline
    prog_res = client.get("/api/progress", headers=headers)
    assert prog_res.status_code == 200
    perf_res = client.get("/api/performance", headers=headers)
    assert perf_res.status_code == 200

    # 5-6. Enroll in courses, complete lessons, and persist workspace state
    ws_payload = {
        "enrolled_courses": ["cs-101", "ai-201"],
        "course_progress": {
            "cs-101": {
                "completedLessons": ["cs-101-m1-l1", "cs-101-m1-l2"],
                "lastLessonId": "cs-101-m1-l2",
                "quizResults": {
                    "module-1": {
                        "score": 10,
                        "total": 12,
                        "percentage": 83,
                        "completedAt": datetime.now(timezone.utc).isoformat(),
                    }
                },
            }
        },
        "course_preferences": ["Computer Science", "Artificial Intelligence"],
        "events": [
            {
                "id": "ev-1",
                "title": "Binary Trees Deep Dive",
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "time": "10:00",
                "type": "Study Session",
                "subject": "Data Structures",
                "completed": True,
            }
        ],
        "study_goals": [
            {"id": "g-1", "text": "Complete Module 1 of Data Structures", "completed": True}
        ],
        "profile_extra": {"location": "Patiala, Punjab", "cgpa": "9.2"},
    }
    ws_put = client.put("/api/auth/workspace-state", json=ws_payload, headers=headers)
    assert ws_put.status_code == 200
    assert ws_put.json()["enrolled_courses"] == ["cs-101", "ai-201"]
    assert "cs-101-m1-l1" in ws_put.json()["course_progress"]["cs-101"]["completedLessons"]

    # 7-8. Upload a study document and process it through the RAG pipeline
    study_text = (
        "Operating Systems Lecture Notes: Virtual Memory and Paging.\n\n"
        "Virtual memory is a memory management technique that provides an idealized abstraction "
        "of the storage resources that are actually available on a given machine. "
        "Paging divides virtual memory into fixed-size blocks called pages and physical memory "
        "into blocks of the same size called frames. The page table translates virtual page numbers "
        "to physical frame numbers. A Translation Lookaside Buffer (TLB) is a hardware cache that "
        "stores recent virtual-to-physical address translations to accelerate memory access.\n\n"
        "A page fault occurs when a running program accesses a memory page that is mapped into the "
        "virtual address space but not currently loaded into physical RAM. Common page replacement "
        "algorithms include Least Recently Used (LRU), First-In-First-Out (FIFO), and Optimal replacement."
    )
    file_bytes = io.BytesIO(study_text.encode("utf-8"))
    up_res = client.post(
        "/api/documents",
        files={"file": ("os_virtual_memory.txt", file_bytes, "text/plain")},
        data={
            "course_id": "cs-os",
            "subject_id": "operating_systems",
            "title": "OS Virtual Memory & Paging Notes",
            "visibility": "private",
        },
        headers=headers,
    )
    assert up_res.status_code in (200, 201), up_res.text
    doc_id = up_res.json()["document_id"]

    proc_res = client.post(f"/api/documents/{doc_id}/process", headers=headers)
    assert proc_res.status_code == 200, proc_res.text
    assert proc_res.json()["status"] == "processed"
    assert proc_res.json().get("chunks_created", proc_res.json().get("chunk_count", 1)) >= 1

    # 9. Search knowledge base & generate grounded document summary
    search_res = client.post(
        "/api/knowledge/search",
        json={"query": "Translation Lookaside Buffer page table", "top_k": 5},
        headers=headers,
    )
    assert search_res.status_code == 200, search_res.text
    search_results = search_res.json()["results"]
    assert len(search_results) >= 1
    assert any(r["document_id"] == doc_id for r in search_results)

    sum_res = client.post(
        f"/api/documents/{doc_id}/summarize",
        json={"mode": "exam"},
        headers=headers,
    )
    assert sum_res.status_code == 200, sum_res.text
    assert sum_res.json()["document_id"] == doc_id
    assert len(sum_res.json()["summary"]) > 20

    # 10-11. Ask AI Assistant about the uploaded document and verify grounded response + citations
    chat_res = client.post(
        "/api/chat",
        json={
            "message": "What is a Translation Lookaside Buffer and how does paging work?",
            "document_id": doc_id,
            "subject_id": "operating_systems",
        },
        headers=headers,
    )
    assert chat_res.status_code == 200, chat_res.text
    chat_data = chat_res.json()
    assert len(chat_data["message"]) > 20
    assert isinstance(chat_data.get("sources"), list)

    # Verify chat history does not duplicate messages
    hist_res = client.get("/api/chat/history", headers=headers)
    assert hist_res.status_code == 200
    assert len(hist_res.json()) == 2  # 1 user message + 1 assistant message

    # 12-15. Generate a document-grounded quiz, answer questions, submit, and review results
    quiz_res = client.post(
        "/api/quizzes",
        json={
            "subject_id": "operating_systems",
            "document_id": doc_id,
            "topic_ids": ["Virtual Memory"],
            "difficulty": "medium",
            "count": 4,
            "title": "Virtual Memory Diagnostic Exam",
        },
        headers=headers,
    )
    assert quiz_res.status_code in (200, 201), quiz_res.text
    quiz_data = quiz_res.json()
    quiz_id = quiz_data["quiz_id"]
    questions = quiz_data["questions"]
    assert len(questions) == 4

    # Prepare answers (answer 2 correctly and 2 incorrectly to trigger topic mastery & weak topic tracking)
    answers_payload = []
    for idx, q in enumerate(questions):
        correct_ans = q["correct_answer"]
        wrong_ans = next((opt for opt in q["options"] if opt != correct_ans), q["options"][0])
        selected = correct_ans if idx < 2 else wrong_ans
        answers_payload.append(
            {
                "question_id": q["question_id"],
                "selected_answer": selected,
                "time_taken": 14.5,
            }
        )

    sub_res = client.post(
        f"/api/quizzes/{quiz_id}/submit",
        json={"answers": answers_payload},
        headers=headers,
    )
    assert sub_res.status_code == 200, sub_res.text
    sub_data = sub_res.json()
    assert sub_data["quiz_id"] == quiz_id
    assert sub_data["total"] == 4
    assert sub_data["score"] == 2
    assert sub_data["percentage"] == 50.0

    # 16. Check performance analytics, weak topics, and quiz attempt history
    attempts_res = client.get("/api/quizzes/attempts", headers=headers)
    assert attempts_res.status_code == 200
    assert any(a["quiz_id"] == quiz_id for a in attempts_res.json())

    perf_after = client.get("/api/performance", headers=headers)
    assert perf_after.status_code == 200
    assert perf_after.json()["total_questions_attempted"] == 4

    weak_res = client.get("/api/performance/weak-topics", headers=headers)
    assert weak_res.status_code == 200
    assert len(weak_res.json()["topics"]) >= 1

    # 17-18. Schedule an upcoming exam, create a study plan, and complete/reschedule a study task
    exam_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    exam_res = client.post(
        "/api/exams",
        json={
            "subject_id": "operating_systems",
            "title": "Operating Systems Mid-Semester Exam",
            "exam_date": exam_date,
        },
        headers=headers,
    )
    assert exam_res.status_code in (200, 201), exam_res.text

    upcoming_res = client.get("/api/exams/upcoming", headers=headers)
    assert upcoming_res.status_code == 200
    assert any(e["title"] == "Operating Systems Mid-Semester Exam" for e in upcoming_res.json())

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end_str = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
    plan_res = client.post(
        "/api/plans",
        json={
            "user_id": user_id,
            "start_date": today_str,
            "end_date": end_str,
            "available_minutes_per_day": 120,
        },
        headers=headers,
    )
    assert plan_res.status_code in (200, 201), plan_res.text
    plan_tasks = plan_res.json().get("tasks", [])
    assert len(plan_tasks) >= 1

    first_task_id = plan_tasks[0]["task_id"]
    task_patch = client.patch(
        f"/api/tasks/{first_task_id}",
        json={"status": "completed"},
        headers=headers,
    )
    assert task_patch.status_code == 200
    assert task_patch.json()["status"] == "completed"

    # 19. Update user profile and change password
    prof_res = client.patch(
        "/api/auth/profile",
        json={
            "name": "Kabir Sharma Updated",
            "academic_level": "3rd Year B.E. CSE (AI & ML)",
            "bio": "Building intelligent RAG and full-stack systems.",
        },
        headers=headers,
    )
    assert prof_res.status_code == 200
    assert prof_res.json()["name"] == "Kabir Sharma Updated"

    pwd_res = client.post(
        "/api/auth/change-password",
        json={
            "current_password": "InitialPassword123!",
            "new_password": "UpdatedSecurePass456!",
        },
        headers=headers,
    )
    assert pwd_res.status_code == 200

    # Verify forgot-password + reset-password token flow
    forgot_res = client.post(
        "/api/auth/forgot-password",
        json={"email": "kabir.e2e@acadassist.edu"},
    )
    assert forgot_res.status_code == 200
    reset_token = forgot_res.json()["reset_token"]
    assert reset_token

    reset_res = client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "FinalResetPassword789!"},
    )
    assert reset_res.status_code == 200

    # Single-use reset token cannot be reused
    reuse_res = client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "AnotherPassword000!"},
    )
    assert reuse_res.status_code == 400

    # 20-23. Log out, log back in with the new password, and verify all progress persisted
    logout_res = client.post("/api/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    relogin_res = client.post(
        "/api/auth/login",
        json={
            "email": "kabir.e2e@acadassist.edu",
            "password": "FinalResetPassword789!",
        },
    )
    assert relogin_res.status_code == 200, relogin_res.text
    new_headers = {"Authorization": f"Bearer {relogin_res.json()['access_token']}"}

    ws_get = client.get("/api/auth/workspace-state", headers=new_headers)
    assert ws_get.status_code == 200
    assert ws_get.json()["enrolled_courses"] == ["cs-101", "ai-201"]
    assert ws_get.json()["profile_extra"]["location"] == "Patiala, Punjab"

    docs_list = client.get("/api/documents", headers=new_headers)
    assert docs_list.status_code == 200
    assert any(d["document_id"] == doc_id for d in docs_list.json()["documents"])

    # 24. Verify strict cross-user isolation against another registered user
    other_reg = client.post(
        "/api/auth/register",
        json={
            "email": "intruder.e2e@acadassist.edu",
            "name": "Intruder User",
            "password": "IntruderPassword123!",
        },
    )
    assert other_reg.status_code == 201
    other_headers = {"Authorization": f"Bearer {other_reg.json()['access_token']}"}

    # Intruder cannot read, summarize, or delete Kabir's private document
    assert client.get(f"/api/documents/{doc_id}", headers=other_headers).status_code == 403
    assert client.post(f"/api/documents/{doc_id}/summarize", json={"mode": "quick"}, headers=other_headers).status_code == 403
    assert client.delete(f"/api/documents/{doc_id}", headers=other_headers).status_code == 403

    # Intruder cannot view or submit Kabir's quiz
    assert client.get(f"/api/quizzes/{quiz_id}", headers=other_headers).status_code == 403
    assert client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": []}, headers=other_headers).status_code == 403
