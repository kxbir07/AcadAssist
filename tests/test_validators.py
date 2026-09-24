"""Tests for upload file validation."""

import io
import pytest
from app.config import settings


def test_upload_valid_file(client, sample_academic_entities, auth_headers):
    entities = sample_academic_entities
    fake_txt = io.BytesIO(b"Valid lecture notes content for operating systems.")

    response = client.post(
        "/api/documents",
        data={
            "user_id": entities["user_a"].user_id,
            "course_id": entities["course"].course_id,
            "subject_id": entities["subject_os"].subject_id,
            "title": "OS Lecture 1",
        },
        files={"file": ("lecture1.txt", fake_txt, "text/plain")},
        headers=auth_headers(entities["user_a"].user_id),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "OS Lecture 1"
    assert data["status"] == "uploaded"
    assert data["file_type"] == "txt"


def test_upload_unsupported_extension(client, sample_academic_entities, auth_headers):
    entities = sample_academic_entities
    fake_exe = io.BytesIO(b"malicious binary payload")

    response = client.post(
        "/api/documents",
        data={
            "user_id": entities["user_a"].user_id,
            "course_id": entities["course"].course_id,
            "subject_id": entities["subject_os"].subject_id,
        },
        files={"file": ("malware.exe", fake_exe, "application/octet-stream")},
        headers=auth_headers(entities["user_a"].user_id),
    )

    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_upload_empty_file(client, sample_academic_entities, auth_headers):
    entities = sample_academic_entities
    empty_file = io.BytesIO(b"")

    response = client.post(
        "/api/documents",
        data={
            "user_id": entities["user_a"].user_id,
            "course_id": entities["course"].course_id,
            "subject_id": entities["subject_os"].subject_id,
        },
        files={"file": ("empty.pdf", empty_file, "application/pdf")},
        headers=auth_headers(entities["user_a"].user_id),
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

