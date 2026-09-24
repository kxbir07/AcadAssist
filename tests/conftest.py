"""Pytest configuration, shared fixtures, and database setup for testing."""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure root directory is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.deps import get_db, set_search_service, set_storage_service
from app.core.database import get_db as core_get_db
from app.config import settings
from app.database.base import Base
from app.models.document import Chunk, Document
from app.models.shared import Course, Exam, QuizAttempt, Subject, Topic, TopicMastery, User
from app.models.study_plan import StudyPlan, StudyTask
from app.models.weekly_report import WeeklyReport
from app.services.rag.knowledge import set_search_service as set_rag_search_service
from app.services.rag.search import AzureSearchService, LocalHybridSearchIndex
from app.services.storage.azure_storage import AzureStorageService
from app.services.storage.local_storage import LocalStorageService

# Ensure all subsystem models are registered on Base.metadata
import app.models  # noqa: F401
try:
    import app.assessment.models  # noqa: F401
except ImportError:
    pass

from app.main import app


@pytest.fixture(scope="session", autouse=True)
def test_environment():
    """Ensure tests run with test environment variables."""
    settings.ENVIRONMENT = "test"
    temp_dir = tempfile.mkdtemp(prefix="acadassist_test_storage_")
    settings.STORAGE_LOCAL_DIR = temp_dir
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create fresh database tables for each test function and teardown afterwards."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def local_storage(test_environment):
    """Local storage service fixture."""
    storage = LocalStorageService(base_dir=test_environment)
    return storage


@pytest.fixture
def search_service():
    """Clean hybrid search service with isolated local in-memory index."""
    service = AzureSearchService()
    service.local_index = LocalHybridSearchIndex()
    set_search_service(service)
    set_rag_search_service(service)
    return service


@pytest.fixture(scope="function")
def client(db_session: Session, test_environment) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden dependencies for all subsystems."""
    local_storage = LocalStorageService(base_dir=test_environment)
    azure_storage = AzureStorageService()
    azure_storage.fallback_storage = local_storage
    set_storage_service(azure_storage)

    service = AzureSearchService()
    service.local_index = LocalHybridSearchIndex()
    set_search_service(service)
    set_rag_search_service(service)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[core_get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_academic_entities(db_session):
    """Seed sample User, Course, and Subject records for testing."""
    user_a = User(user_id="user-alice-001", name="Alice Student", email="alice@test.edu")
    user_b = User(user_id="user-bob-002", name="Bob Student", email="bob@test.edu")
    course = Course(course_id="course-cs-101", name="Computer Science", code="CS101")
    subject_os = Subject(subject_id="subj-os-201", course_id="course-cs-101", name="Operating Systems")
    subject_db = Subject(subject_id="subj-db-202", course_id="course-cs-101", name="Database Systems")

    db_session.add_all([user_a, user_b, course, subject_os, subject_db])
    db_session.commit()

    return {
        "user_a": user_a,
        "user_b": user_b,
        "course": course,
        "subject_os": subject_os,
        "subject_db": subject_db,
    }


@pytest.fixture
def auth_headers(db_session):
    """Generate authorization headers for a given user_id, ensuring user exists in test DB."""
    def _make(user_id: str = "user-alice-001") -> dict[str, str]:
        user = db_session.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(
                user_id=user_id,
                name=user_id.replace("_", " ").replace("-", " ").title(),
                email=f"{user_id}@test.local",
            )
            db_session.add(user)
            db_session.commit()
        from app.core.security import create_access_token
        token = create_access_token({"sub": user_id})
        return {"Authorization": f"Bearer {token}"}
    return _make


