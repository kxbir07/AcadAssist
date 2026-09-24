"""Integration tests for the FastAPI application and POST /api/chat endpoint."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.database.session import SessionLocal
from app.models.shared import User

client = TestClient(app)


@pytest.fixture
def auth_user():
    uid = "00000000-0000-0000-0000-000000000001"
    with SessionLocal() as db:
        user = db.query(User).filter(User.user_id == uid).first()
        if not user:
            user = User(user_id=uid, email="chat_test@test.local", name="Chat Test User", password_hash="dummy_hash")
            db.add(user)
            db.commit()
    token = create_access_token({"sub": uid, "email": "chat_test@test.local"})
    return {"user_id": uid, "headers": {"Authorization": f"Bearer {token}"}}


def test_health_check_endpoint():
    """Verify health probe returns status 200 and metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "AcadAssist API"
    assert "environment" in data


def test_chat_endpoint_unauthenticated():
    """Verify POST /api/chat rejects unauthenticated requests with 401."""
    payload = {"message": "What should I study today?"}
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 401


def test_chat_endpoint_valid_request(auth_user):
    """Verify POST /api/chat processes valid request and returns response schema."""
    payload = {
        "message": "What should I study today?",
    }
    response = client.post("/api/chat", json=payload, headers=auth_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "sources" in data
    assert "actions" in data
    assert "execution_mode" in data
    assert isinstance(data["sources"], list)
    assert isinstance(data["actions"], list)


def test_chat_endpoint_legacy_matching_user_id(auth_user):
    """Verify POST /api/chat allows matching legacy user_id."""
    payload = {
        "user_id": auth_user["user_id"],
        "message": "What should I study today?",
    }
    response = client.post("/api/chat", json=payload, headers=auth_user["headers"])
    assert response.status_code == 200


def test_chat_endpoint_legacy_user_id_mismatch(auth_user):
    """Verify POST /api/chat rejects mismatched user_id with 403 Forbidden."""
    payload = {
        "user_id": "different-user-9999",
        "message": "What should I study today?",
    }
    response = client.post("/api/chat", json=payload, headers=auth_user["headers"])
    assert response.status_code == 403


def test_chat_endpoint_empty_message_validation(auth_user):
    """Verify POST /api/chat rejects empty message string with 400."""
    payload = {
        "message": "   ",
    }
    response = client.post("/api/chat", json=payload, headers=auth_user["headers"])
    assert response.status_code == 400
    assert "message" in response.json()["detail"].lower()


def test_chat_endpoint_empty_user_id_validation(auth_user):
    """Verify POST /api/chat rejects empty user_id string with 400 when provided."""
    payload = {
        "user_id": "",
        "message": "Explain paging.",
    }
    response = client.post("/api/chat", json=payload, headers=auth_user["headers"])
    assert response.status_code == 400
    assert "user_id" in response.json()["detail"].lower()


def test_chat_endpoint_missing_fields_validation(auth_user):
    """Verify POST /api/chat rejects missing body fields with 422."""
    response = client.post("/api/chat", json={}, headers=auth_user["headers"])
    assert response.status_code == 422
