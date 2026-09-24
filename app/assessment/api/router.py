"""Aggregating Assessment API router."""

from fastapi import APIRouter
from app.assessment.api.quizzes import router as quizzes_router
from app.assessment.api.performance import router as performance_router
from app.assessment.api.exams import router as exams_router

assessment_router = APIRouter()
assessment_router.include_router(quizzes_router)
assessment_router.include_router(performance_router)
assessment_router.include_router(exams_router)
