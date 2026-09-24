"""Centralized configuration for AcadAssist integrated backend.

Supports Person 2 (Knowledge Base & RAG), Person 3 (Assessment Subsystem),
and Person 4 (Study Intelligence & Planning) with unified settings.
"""

from os import getenv
from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class AssessmentSettings(BaseModel):
    """Configurable settings and thresholds for Person 3 Assessment Subsystem."""

    # Adaptive Difficulty Thresholds (percentages 0 - 100)
    adaptive_easy_threshold: float = Field(
        default=float(getenv("ADAPTIVE_EASY_THRESHOLD", "50.0")),
        description="Percentage below which difficulty adapts to easy / revision",
    )
    adaptive_hard_threshold: float = Field(
        default=float(getenv("ADAPTIVE_HARD_THRESHOLD", "75.0")),
        description="Percentage above which difficulty adapts to hard",
    )
    default_difficulty: str = Field(
        default=getenv("DEFAULT_DIFFICULTY", "medium"),
        description="Default quiz difficulty if no performance history exists",
    )

    # Mastery / Weak Topic Thresholds (ratios 0.0 - 1.0)
    weak_topic_threshold: float = Field(
        default=float(getenv("WEAK_TOPIC_THRESHOLD", "0.60")),
        description="Mastery ratio below which a topic is classified as weak",
    )
    strong_topic_threshold: float = Field(
        default=float(getenv("STRONG_TOPIC_THRESHOLD", "0.75")),
        description="Mastery ratio at or above which a topic is classified as strong",
    )

    # Exam Proximity Windows (in days)
    exam_normal_days: int = Field(
        default=int(getenv("EXAM_NORMAL_DAYS", "14")),
        description="Days threshold beyond which normal assessment is applied",
    )
    exam_increased_days: int = Field(
        default=int(getenv("EXAM_INCREASED_DAYS", "7")),
        description="Days threshold (7-14d) for increased assessment focus",
    )
    exam_weak_topic_days: int = Field(
        default=int(getenv("EXAM_WEAK_TOPIC_DAYS", "3")),
        description="Days threshold (3-7d) for targeted weak-topic assessment",
    )
    exam_revision_days: int = Field(
        default=int(getenv("EXAM_REVISION_DAYS", "2")),
        description="Days threshold (<=2d) for revision + targeted assessment",
    )


class Settings(BaseSettings):
    """Application settings with environment override support."""

    app_name: str = "AcadAssist"
    app_version: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Comma-separated frontend origins. Never use wildcard origins with credentials in production.
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    # Database: single shared database for AcadAssist
    DATABASE_URL: str = "sqlite:///./data/acadassist.db"

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def environment(self) -> str:
        return self.ENVIRONMENT

    @property
    def is_development(self) -> bool:
        return not self.is_production()

    @property
    def azure_storage_account(self) -> str | None:
        return self.AZURE_STORAGE_ACCOUNT

    @property
    def azure_storage_container(self) -> str:
        return self.AZURE_STORAGE_CONTAINER

    @property
    def azure_storage_endpoint(self) -> str | None:
        if not self.AZURE_STORAGE_ACCOUNT:
            return None
        if self.AZURE_STORAGE_ACCOUNT.startswith("http"):
            return self.AZURE_STORAGE_ACCOUNT
        return f"https://{self.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net"

    @property
    def azure_search_endpoint(self) -> str | None:
        return self.AZURE_SEARCH_ENDPOINT

    @property
    def azure_search_index(self) -> str:
        return self.AZURE_SEARCH_INDEX or self.AZURE_SEARCH_INDEX_NAME

    @property
    def foundry_project_endpoint(self) -> str | None:
        return self.FOUNDRY_PROJECT_ENDPOINT

    @property
    def foundry_project(self) -> str:
        return self.FOUNDRY_PROJECT

    @property
    def foundry_model_deployment(self) -> str:
        return self.FOUNDRY_MODEL_DEPLOYMENT

    @property
    def foundry_embedding_deployment(self) -> str:
        return self.FOUNDRY_EMBEDDING_DEPLOYMENT

    @property
    def foundry_agent_name(self) -> str:
        return self.FOUNDRY_AGENT_NAME

    @property
    def is_foundry_configured(self) -> bool:
        """True if LLM generation (quizzes, summaries, chat) can actually run.

        Mirrors FoundryProjectManager.is_configured: a Foundry Project endpoint
        is only one of three valid ways to authenticate. A direct Azure OpenAI
        key/endpoint pair or a plain OpenAI API key are equally sufficient and
        must be reflected here, or this health flag misleadingly reports
        "not configured" for deployments that are actually working.
        """
        has_azure_key_pair = bool(
            (self.AZURE_OPENAI_API_KEY or self.AZURE_API_KEY)
            and (self.AZURE_OPENAI_ENDPOINT or self.AZURE_ENDPOINT)
        )
        return bool(self.FOUNDRY_PROJECT_ENDPOINT) or has_azure_key_pair or bool(self.OPENAI_API_KEY)

    @property
    def is_search_configured(self) -> bool:
        return bool(self.AZURE_SEARCH_ENDPOINT)

    @property
    def is_storage_configured(self) -> bool:
        return bool(self.AZURE_STORAGE_ACCOUNT or self.AZURE_STORAGE_CONNECTION_STRING)

    # Assessment Specific Settings (Person 3)
    assessment: AssessmentSettings = Field(default_factory=AssessmentSettings)

    # Authentication & Security
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # General Azure credentials (from .env.example)
    AZURE_ENDPOINT: str | None = None
    AZURE_API_KEY: str | None = None

    # Azure Blob Storage Configuration (Person 1 & Person 2)
    AZURE_STORAGE_ACCOUNT: str | None = None
    AZURE_STORAGE_CONNECTION_STRING: str | None = None
    AZURE_STORAGE_CONTAINER: str = "acadassist-documents"
    STORAGE_LOCAL_DIR: str = "./data/storage"

    # Azure AI Search Configuration (Person 1 & Person 2)
    AZURE_SEARCH_ENDPOINT: str | None = None
    AZURE_SEARCH_KEY: str | None = None
    AZURE_SEARCH_INDEX_NAME: str = "acadassist-knowledge-index"
    AZURE_SEARCH_INDEX: str = "acadassist-index"

    # Microsoft Foundry & Agent Configuration (Person 1)
    FOUNDRY_PROJECT_ENDPOINT: str | None = None
    FOUNDRY_PROJECT: str = "acadassist-foundry"
    FOUNDRY_MODEL_DEPLOYMENT: str = "gpt-4.1-mini"
    FOUNDRY_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-small"
    FOUNDRY_AGENT_NAME: str = "AcadAssist"

    # Embedding Service Configuration (Person 2)
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536

    # Document Chunking Configuration (Person 2)
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: list[str] = Field(
        default_factory=lambda: [".pdf", ".ppt", ".pptx", ".docx", ".txt"]
    )

    # Study Intelligence & Planning Configuration (Person 4)
    DEFAULT_STUDY_TIME_MINUTES: int = 120
    STRONG_MASTERY_THRESHOLD: float = 75.0
    WEAK_MASTERY_THRESHOLD: float = 60.0
    MASTERY_COMPLETION_THRESHOLD: float = 70.0

    # Exam proximity rules for Study Intelligence (days before exam)
    EXAM_PROXIMITY_URGENT_DAYS: int = 2
    EXAM_PROXIMITY_WEAK_PRIORITY_DAYS: int = 7
    EXAM_PROXIMITY_PREP_DAYS: int = 14

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def is_production(self) -> bool:
        """Check if currently running in production environment."""
        return self.ENVIRONMENT.lower() in ("production", "prod")

    def get_jwt_secret_key(self) -> str:
        """Get the JWT secret key, strictly requiring an environment-configured key in production."""
        if self.JWT_SECRET_KEY:
            return self.JWT_SECRET_KEY
        if self.is_production():
            raise ValueError("JWT_SECRET_KEY must be provided via environment configuration in production.")
        import secrets
        if not hasattr(Settings, "_ephemeral_jwt_secret"):
            Settings._ephemeral_jwt_secret = secrets.token_urlsafe(32)
        return Settings._ephemeral_jwt_secret

    def validate_production_azure(self) -> None:
        """Ensure all required Azure credentials and security secrets are provided when running in production."""
        if not self.is_production():
            return
        missing = []
        if not self.JWT_SECRET_KEY:
            missing.append("JWT_SECRET_KEY")
        if not self.AZURE_STORAGE_CONNECTION_STRING:
            missing.append("AZURE_STORAGE_CONNECTION_STRING")
        if not self.AZURE_SEARCH_ENDPOINT:
            missing.append("AZURE_SEARCH_ENDPOINT")
        if not self.AZURE_SEARCH_KEY:
            missing.append("AZURE_SEARCH_KEY")
        if not (self.AZURE_OPENAI_API_KEY or self.OPENAI_API_KEY):
            missing.append("AZURE_OPENAI_API_KEY / OPENAI_API_KEY")
        if "*" in self.cors_allowed_origins:
            missing.append("CORS_ALLOWED_ORIGINS (wildcard is not allowed in production)")

        if missing:
            raise ValueError(
                f"Production environment requires security credentials. Missing: {', '.join(missing)}"
            )


settings = Settings()

# Ensure local directories exist if running locally
if settings.DATABASE_URL.startswith("sqlite:///"):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    if db_path and not db_path.startswith(":memory:"):
        db_dir = Path(db_path).parent
        if db_dir and not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)

local_storage_path = Path(settings.STORAGE_LOCAL_DIR)
if not local_storage_path.exists():
    local_storage_path.mkdir(parents=True, exist_ok=True)
