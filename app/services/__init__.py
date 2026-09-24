"""Services package exports."""

from app.services.person3_client import person3_consumer
from app.services.planner import create_study_plan, get_today_plan, update_task_status
from app.services.progress import get_progress
from app.services.recommendations import get_recommendations
from app.services.reports import generate_weekly_report, get_weekly_reports

__all__ = [
    "get_progress",
    "create_study_plan",
    "get_today_plan",
    "update_task_status",
    "get_recommendations",
    "generate_weekly_report",
    "get_weekly_reports",
    "person3_consumer",
]
