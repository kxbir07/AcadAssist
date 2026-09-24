"""API router consolidating Auth, Knowledge Base, Assessment, and Study Intelligence routes."""

from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.notes import router as notes_router
from app.api.routes.plans import router as plans_router, tasks_router
from app.api.routes.progress import router as progress_router
from app.api.routes.reports import router as reports_router
from app.api.tools import router as tools_router

api_router = APIRouter(prefix="/api")

# Authentication routes
api_router.include_router(auth_router)

# Person 2 Knowledge Base & Document routes
api_router.include_router(documents_router)
api_router.include_router(knowledge_router)

# Notes and Chat routes
api_router.include_router(notes_router)
api_router.include_router(chat_router)

# Person 1 Foundry Tools routes
api_router.include_router(tools_router)

# Person 4 Study Intelligence routes
api_router.include_router(progress_router)
api_router.include_router(plans_router)
api_router.include_router(tasks_router)
api_router.include_router(reports_router)

__all__ = ["api_router"]

