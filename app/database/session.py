"""Database engine and session management for AcadAssist."""

from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.base import Base

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(target_engine=None) -> None:
    """Initialize database tables idempotently and ensure newly added columns exist."""
    from sqlalchemy import text, inspect
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

    # For SQLite databases, synchronize columns on existing tables
    try:
        inspector = inspect(eng)
        existing_tables = inspector.get_table_names()

        with eng.begin() as conn:
            if "users" in existing_tables:
                user_cols = {c["name"] for c in inspector.get_columns("users")}
                if "password_hash" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
                if "role" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'student'"))
                if "academic_level" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN academic_level VARCHAR(100) DEFAULT 'Undergraduate'"))
                if "field_of_study" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN field_of_study VARCHAR(255) DEFAULT 'Computer Science'"))
                if "bio" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN bio TEXT"))
                if "updated_at" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN updated_at DATETIME"))

            if "documents" in existing_tables:
                doc_cols = {c["name"] for c in inspector.get_columns("documents")}
                if "visibility" not in doc_cols:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN visibility VARCHAR(20) DEFAULT 'private'"))
                if "checksum" not in doc_cols:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN checksum VARCHAR(64)"))
                if "size_bytes" not in doc_cols:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN size_bytes INTEGER DEFAULT 0"))
                if "processing_error" not in doc_cols:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN processing_error TEXT"))
                if "updated_at" not in doc_cols:
                    conn.execute(text("ALTER TABLE documents ADD COLUMN updated_at DATETIME"))

            if "chunks" in existing_tables:
                chunk_cols = {c["name"] for c in inspector.get_columns("chunks")}
                if "visibility" not in chunk_cols:
                    conn.execute(text("ALTER TABLE chunks ADD COLUMN visibility VARCHAR(20) DEFAULT 'private'"))
    except Exception as e:
        # If running on in-memory or already migrated table, ignore alter errors
        pass



def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
