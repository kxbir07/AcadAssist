"""End-to-End Test: Operating Systems PDF Document Processing and RAG Retrieval.

Verifies complete pipeline:
Upload -> Store -> DB Record -> Process -> Extract -> Normalize -> Metadata -> Chunk -> Embed -> Index -> Search.
"""

import io
from reportlab.pdfgen import canvas
from app.models.document import Document
from app.services.rag.knowledge import search_knowledge


def _generate_os_textbook_pdf() -> bytes:
    """Generate a realistic 3-page Operating Systems textbook chapter in PDF format."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)

    # Page 1: Introduction and CPU Scheduling
    c.drawString(72, 750, "Chapter 1: Operating Systems Architecture and Scheduling")
    c.drawString(72, 730, "An operating system acts as an intermediary between user and hardware.")
    c.drawString(72, 710, "CPU scheduling algorithms include First-Come-First-Served and Round Robin.")
    c.drawString(72, 690, "Context switching saves state of the currently executing process.")
    c.showPage()

    # Page 2: Deadlocks and Deadlock Prevention (TARGET PAGE)
    c.drawString(72, 750, "Chapter 2: Deadlock Prevention and Banker's Algorithm")
    c.drawString(72, 730, "Deadlock occurs when processes hold resources and wait for each other in cycles.")
    c.drawString(72, 710, "Deadlock prevention eliminates at least one Coffman condition:")
    c.drawString(72, 690, "1. Mutual Exclusion  2. Hold and Wait  3. No Preemption  4. Circular Wait.")
    c.drawString(72, 670, "Banker's algorithm dynamically tracks safe states to ensure deadlock avoidance.")
    c.showPage()

    # Page 3: Virtual Memory Management
    c.drawString(72, 750, "Chapter 3: Virtual Memory and Paging Systems")
    c.drawString(72, 730, "Virtual memory creates an illusion of large contiguous memory.")
    c.drawString(72, 710, "Translation Lookaside Buffers (TLB) accelerate page table address lookups.")
    c.drawString(72, 690, "Page faults trigger retrieval of required frames from secondary storage.")
    c.showPage()

    c.save()
    return buffer.getvalue()


def _generate_dbms_textbook_pdf() -> bytes:
    """Generate a 2-page Database Systems textbook chapter in PDF format."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)

    c.drawString(72, 750, "Chapter 1: Relational Database Design and Normalization")
    c.drawString(72, 730, "Database normalization minimizes redundancy using 1NF, 2NF, 3NF, and BCNF.")
    c.showPage()

    c.drawString(72, 750, "Chapter 2: Indexing and B+ Trees")
    c.drawString(72, 730, "B+ Tree indexes optimize range queries and random disk reads in RDBMS.")
    c.showPage()

    c.save()
    return buffer.getvalue()


def test_e2e_operating_systems_pdf_pipeline(client, db_session, sample_academic_entities, auth_headers):
    entities = sample_academic_entities
    alice_id = entities["user_a"].user_id
    bob_id = entities["user_b"].user_id
    course_id = entities["course"].course_id
    subject_os = entities["subject_os"].subject_id
    subject_db = entities["subject_db"].subject_id

    alice_headers = auth_headers(alice_id)
    bob_headers = auth_headers(bob_id)

    # 1. Alice uploads OS Textbook PDF
    os_pdf_bytes = _generate_os_textbook_pdf()
    upload_os_resp = client.post(
        "/api/documents",
        data={
            "user_id": alice_id,
            "course_id": course_id,
            "subject_id": subject_os,
            "title": "Operating Systems Unit 3",
            "description": "Operating Systems Textbook - Scheduling, Deadlocks, Memory",
        },
        files={"file": ("OS_Unit_3.pdf", io.BytesIO(os_pdf_bytes), "application/pdf")},
        headers=alice_headers,
    )
    assert upload_os_resp.status_code == 201
    os_doc_data = upload_os_resp.json()
    os_doc_id = os_doc_data["document_id"]
    assert os_doc_data["status"] == "uploaded"

    # 2. Bob uploads DBMS Textbook PDF
    dbms_pdf_bytes = _generate_dbms_textbook_pdf()
    upload_dbms_resp = client.post(
        "/api/documents",
        data={
            "user_id": bob_id,
            "course_id": course_id,
            "subject_id": subject_db,
            "title": "DBMS Unit 1",
            "description": "Database Normalization and Indexing",
        },
        files={"file": ("DBMS_Unit_1.pdf", io.BytesIO(dbms_pdf_bytes), "application/pdf")},
        headers=bob_headers,
    )
    assert upload_dbms_resp.status_code == 201
    dbms_doc_id = upload_dbms_resp.json()["document_id"]

    # 3. Process Alice's OS PDF through full pipeline
    proc_resp = client.post(f"/api/documents/{os_doc_id}/process?user_id={alice_id}", headers=alice_headers)
    assert proc_resp.status_code == 200
    assert proc_resp.json()["status"] == "processed"
    assert proc_resp.json()["processed_at"] is not None

    # Also process Bob's document
    client.post(f"/api/documents/{dbms_doc_id}/process?user_id={bob_id}", headers=bob_headers)


    # 4. Alice executes Knowledge Search: 'Explain deadlock prevention'
    search_result = search_knowledge(
        user_id=alice_id,
        query="Explain deadlock prevention",
        course_id=course_id,
        subject_id=subject_os,
        top_k=3,
    )

    results = search_result["results"]
    assert len(results) > 0, "Expected search results for Alice's query"

    # 5. Verify top chunk details: page metadata, content relevance
    top_chunk = results[0]
    assert top_chunk["document_id"] == os_doc_id
    assert top_chunk["filename"] == "OS_Unit_3.pdf"
    assert top_chunk["document_title"] == "Operating Systems Unit 3"

    # CRITICAL: Verify Page Metadata is page 2 (where Deadlock chapter is located)
    assert top_chunk["page_number"] == 2
    assert "Deadlock" in top_chunk["content"]
    assert "Coffman" in top_chunk["content"] or "Banker" in top_chunk["content"]

    # 6. Verify User Security: Alice NEVER receives Bob's DBMS chunks
    for chunk in results:
        assert chunk["document_id"] != dbms_doc_id
        assert "DBMS" not in chunk.get("filename", "")

    # 7. Bob searches for deadlock prevention -> Bob has NO OS document -> returns 0 results
    bob_search = search_knowledge(
        user_id=bob_id,
        query="Explain deadlock prevention",
        top_k=3,
    )
    assert len(bob_search["results"]) == 0
