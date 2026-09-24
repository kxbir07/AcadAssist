"""API dependencies and authentication/user resolution for Person 3 Assessment Subsystem."""

from app.core.auth import get_current_user, get_current_user_id

__all__ = ["get_current_user_id", "get_current_user"]
