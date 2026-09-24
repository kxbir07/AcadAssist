"""Shared application database configuration and session management.

Provides SQLAlchemy declarative base, session factories, and database initializers
for the single shared AcadAssist application database.
Re-exports unified engine, session, and Base from app.database.
"""

from typing import Generator
from sqlalchemy.orm import Session

from app.database.base import Base
from app.database.session import engine, SessionLocal, get_db


def init_db(target_engine=None) -> None:
    """Initialize all registered SQLAlchemy database tables."""
    import app.assessment.models  # noqa: F401

    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)


__all__ = ["Base", "engine", "SessionLocal", "get_db", "init_db"]
