"""Integration tests for Document API endpoints."""

import io
from app.models.document import Document


def test_document_lifecycle(client, db_session, sample_academic_entities, auth_headers):
    entities = sample_academic_entities
    user_id = entities["user_a"].user_id
    course_id = entities["course"].course_id
    subject_id = entities["subject_os"].subject_id
    headers = auth_headers(user_id)

    # 1. Upload TXT document
    text_content = (
        "Operating Systems Unit 3\n\n"
        "Deadlock Prevention\n"
        "Deadlock prevention ensures that at least one of the necessary conditions cannot hold.\n\n"
        "Banker's Algorithm\n"
        "The Banker's algorithm tests for safety by simulating the allocation of predetermined maximum possible amounts."
    )
    file_bytes = io.BytesIO(text_content.encode("utf-8"))

    upload_resp = client.post(
        "/api/documents",
        data={
            "user_id": user_id,
            "course_id": course_id,
            "subject_id": subject_id,
            "title": "OS Unit 3",
            "description": "Operating Systems Deadlocks and Safety",
        },
        files={"file": ("OS_Unit_3.txt", file_bytes, "text/plain")},
        headers=headers,
    )

    assert upload_resp.status_code == 201
    doc_data = upload_resp.json()
    doc_id = doc_data["document_id"]
    assert doc_data["title"] == "OS Unit 3"
    assert doc_data["status"] == "uploaded"
    assert doc_data["processed_at"] is None

    # 2. List documents
    list_resp = client.get(f"/api/documents?user_id={user_id}", headers=headers)

    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total"] >= 1
    assert any(d["document_id"] == doc_id for d in list_data["documents"])

    # 3. Get document details
    get_resp = client.get(f"/api/documents/{doc_id}?user_id={user_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["document_id"] == doc_id

    # 4. Process document
    proc_resp = client.post(f"/api/documents/{doc_id}/process?user_id={user_id}", headers=headers)
    assert proc_resp.status_code == 200
    proc_data = proc_resp.json()
    assert proc_data["status"] == "processed"
    assert proc_data["processed_at"] is not None

    # Verify DB status
    db_doc = db_session.query(Document).filter(Document.document_id == doc_id).first()
    assert db_doc.status == "processed"
    assert db_doc.processed_at is not None

    # 5. Summarize document (all modes)
    for mode in ["quick", "detailed", "exam", "revision"]:
        sum_resp = client.post(
            f"/api/documents/{doc_id}/summarize?user_id={user_id}",
            json={"mode": mode},
            headers=headers,
        )
        assert sum_resp.status_code == 200
        sum_data = sum_resp.json()
        assert sum_data["mode"] == mode
        assert sum_data["status"] == "processed"
        assert len(sum_data["summary"]) > 0

    # 6. Delete document
    del_resp = client.delete(f"/api/documents/{doc_id}?user_id={user_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # Verify deleted
    get_after_del = client.get(f"/api/documents/{doc_id}?user_id={user_id}", headers=headers)
    assert get_after_del.status_code == 404

