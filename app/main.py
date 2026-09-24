"""AcadAssist main application entrypoint and FastAPI router registration.

Consolidates Knowledge Base, Assessment, and Study Intelligence subsystems into the shared AcadAssist backend.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.assessment.api.router import assessment_router
from app.config import settings
from app.database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan managing production validation and database table initialization."""
    if settings.is_production():
        settings.validate_production_azure()
    init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AcadAssist API",
        description="AI-Powered Personalized Academic Study Assistant Backend",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Configure CORS for React frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API routes under /api
    app.include_router(api_router)
    app.include_router(assessment_router, prefix="/api")

    @app.get("/", tags=["Root"])
    def root():
        """Root welcome endpoint directing users to the Web UI and Swagger Docs."""
        return {
            "message": "Welcome to AcadAssist API",
            "frontend_url": "http://localhost:5173",
            "docs_url": "/docs",
            "health_url": "/health",
        }

    @app.get("/health", tags=["Health"])
    def health_check():
        """Unified health check endpoint confirming subsystem readiness and cloud/local configuration."""
        foundry_configured = settings.is_foundry_configured
        storage_configured = settings.is_storage_configured
        search_configured = settings.is_search_configured
        embedding_configured = bool(
            settings.AZURE_OPENAI_API_KEY or settings.AZURE_API_KEY or settings.OPENAI_API_KEY
        )

        return {
            "status": "healthy",
            "service": "AcadAssist API",
            "environment": settings.ENVIRONMENT,
            "app": "AcadAssist",
            "version": "2.0.0",
            "subsystems": {
                "knowledge_rag": "operational",
                "assessment": "operational",
                "study_intelligence": "operational",
            },
            "foundry": {
                "mode": "cloud_foundry" if foundry_configured else "local_orchestrator",
                "configured": foundry_configured,
            },
            "azure_storage": {
                "mode": "azure_blob" if storage_configured else "local_storage",
                "configured": storage_configured,
            },
            "azure_search": {
                "mode": "azure_ai_search" if search_configured else "local_hybrid_index",
                "configured": search_configured,
            },
            "embeddings": {
                "mode": "azure_openai" if embedding_configured else "local_deterministic",
                "configured": embedding_configured,
                "model": settings.EMBEDDING_MODEL,
                "dimensions": settings.EMBEDDING_DIMENSIONS,
            },
            "embedding_model": settings.EMBEDDING_MODEL,
            "embedding_dimensions": settings.EMBEDDING_DIMENSIONS,
        }

    return app


app = create_app()


def main() -> None:
    """Entry point to launch the development server."""
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
