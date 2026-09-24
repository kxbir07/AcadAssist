"""End-to-End integration test for the AcadAssist Operating Systems demo scenario.

Validates the full pipeline flow with Zero Trust authentication:
React Client (authenticated)
    ↓
POST /api/chat (Bearer Token)
    ↓
FastAPI Router
    ↓
AcadAssist Agent Service
    ↓
search_knowledge tool
    ↓
Knowledge Base / AI Search chunks
    ↓
Grounded Answer & Citation Construction
    ↓
FastAPI
    ↓
React Client
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.database.session import SessionLocal
from app.models.shared import User

client = TestClient(app)


def test_e2e_explain_paging_demo():
    """Verify complete end-to-end OS demo scenario for 'Explain paging.'"""
    uid = "00000000-0000-0000-0000-000000000001"

    # Ensure authenticated test user exists in DB
    with SessionLocal() as db:
        if not db.query(User).filter(User.user_id == uid).first():
            db.add(User(user_id=uid, email="student1@test.local", name="Student One", password_hash="dummy_hash"))
            db.commit()

    token = create_access_token({"sub": uid, "email": "student1@test.local"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "message": "Explain paging.",
    }

    # 1. React sends POST request to FastAPI with bearer token
    response = client.post("/api/chat", json=payload, headers=headers)

    # 2. FastAPI returns 200 OK
    assert response.status_code == 200
    data = response.json()

    # 3. Verify grounded message content
    message = data.get("message", "")
    assert len(message) > 0
    assert "paging" in message.lower()
    assert "memory" in message.lower()
    assert "frame" in message.lower() or "page" in message.lower()

    # 4. Verify source citation preservation
    sources = data.get("sources", [])
    if data.get("execution_mode") == "local_orchestrator":
        assert len(sources) >= 1

        primary_source = sources[0]
        assert primary_source["document_title"] == "Operating Systems Concepts: Virtual Memory"
        assert primary_source["filename"] == "os_concepts_ch8_paging.pdf"
        assert primary_source["page_number"] == 324
        assert primary_source["score"] >= 0.8
        assert "paging" in primary_source["content_snippet"].lower()

    # 5. Verify action items and execution mode
    assert isinstance(data.get("actions"), list)
    assert data.get("execution_mode") in ("local_orchestrator", "cloud_foundry")
