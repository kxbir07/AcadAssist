"""Mandatory User Security and Isolation tests.

Guarantees that User A can NEVER retrieve or manipulate User B's private documents or chunks.
"""

from datetime import datetime, timezone
import pytest
from app.models.document import Chunk, Document
from app.services.rag.embedding import EmbeddingService
from app.services.rag.knowledge import search_knowledge


def test_mandatory_user_search_isolation(search_service):
    """MANDATORY SECURITY TEST:

    User A has OS.pdf
    User B has DBMS.pdf (containing normalization content)
    User A searches 'normalization'
    User A must NEVER receive User B's chunks!
    """
    embedding_service = EmbeddingService()

    chunk_user_a = Chunk(
        chunk_id="chunk-user-a-os",
        document_id="doc-a-os",
        user_id="user_alice",
        course_id="cs-101",
        subject_id="os-subj",
        content="Operating Systems concepts: Process Scheduling, Deadlocks, Paging.",
        document_title="Operating Systems",
        filename="OS.pdf",
        page_number=1,
        chunk_index=0,
        total_chunks=1,
        created_at=datetime.now(timezone.utc),
    )

    chunk_user_b = Chunk(
        chunk_id="chunk-user-b-dbms",
        document_id="doc-b-dbms",
        user_id="user_bob",
        course_id="cs-101",
        subject_id="dbms-subj",
        content="Database Normalization: 1NF, 2NF, 3NF, BCNF eliminate functional redundancy.",
        document_title="Database Management Systems",
        filename="DBMS.pdf",
        page_number=14,
        chunk_index=0,
        total_chunks=1,
        created_at=datetime.now(timezone.utc),
    )

    chunks = [chunk_user_a, chunk_user_b]
    vectors = embedding_service.embed_texts([c.content for c in chunks])
    search_service.index_chunks(chunks, vectors)

    # 1. User A searches for "normalization"
    search_user_a = search_knowledge(
        user_id="user_alice",
        query="database normalization 1NF 2NF 3NF",
        top_k=5,
    )

    # User A MUST NOT receive User B's DBMS chunks!
    results_a = search_user_a["results"]
    for r in results_a:
        assert r["chunk_id"] != "chunk-user-b-dbms"
        assert r["document_id"] != "doc-b-dbms"
        assert "Normalization" not in r["content"]

    # 2. User B searches for "normalization" -> receives their own chunk
    search_user_b = search_knowledge(
        user_id="user_bob",
        query="database normalization",
        top_k=5,
    )
    results_b = search_user_b["results"]
    assert len(results_b) >= 1
    assert results_b[0]["chunk_id"] == "chunk-user-b-dbms"
    assert results_b[0]["page_number"] == 14


def test_unauthorized_document_operations(client, db_session, sample_academic_entities, auth_headers):
    """Verify unauthorized GET, DELETE, PROCESS, and SUMMARIZE are strictly forbidden."""
    entities = sample_academic_entities

    # Create a document owned by User B (Bob)
    doc_bob = Document(
        document_id="doc-bob-private-001",
        user_id=entities["user_b"].user_id,
        course_id=entities["course"].course_id,
        subject_id=entities["subject_db"].subject_id,
        filename="dbms_private.pdf",
        file_type="pdf",
        title="Bob's Private DBMS Notes",
        storage_path="/tmp/fake/dbms_private.pdf",
        status="uploaded",
    )
    db_session.add(doc_bob)
    db_session.commit()

    alice_id = entities["user_a"].user_id
    alice_headers = auth_headers(alice_id)

    # 1. User A tries to GET User B's document -> 403 Forbidden
    resp_get = client.get(f"/api/documents/{doc_bob.document_id}?user_id={alice_id}", headers=alice_headers)
    assert resp_get.status_code == 403
    assert "Forbidden" in resp_get.json()["detail"] or "Access denied" in resp_get.json()["detail"]

    # 2. User A tries to DELETE User B's document -> 403 Forbidden
    resp_del = client.delete(f"/api/documents/{doc_bob.document_id}?user_id={alice_id}", headers=alice_headers)
    assert resp_del.status_code == 403
    assert "Forbidden" in resp_del.json()["detail"] or "Access denied" in resp_del.json()["detail"]

    # 3. User A tries to PROCESS User B's document -> 403 Forbidden
    resp_proc = client.post(f"/api/documents/{doc_bob.document_id}/process?user_id={alice_id}", headers=alice_headers)
    assert resp_proc.status_code == 403
    assert "Forbidden" in resp_proc.json()["detail"] or "Access denied" in resp_proc.json()["detail"]

    # 4. User A tries to SUMMARIZE User B's document -> 403 Forbidden
    resp_sum = client.post(
        f"/api/documents/{doc_bob.document_id}/summarize?user_id={alice_id}",
        json={"mode": "quick"},
        headers=alice_headers,
    )
    assert resp_sum.status_code == 403
    assert "Forbidden" in resp_sum.json()["detail"] or "Access denied" in resp_sum.json()["detail"]

