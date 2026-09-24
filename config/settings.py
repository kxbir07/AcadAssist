"""Configuration shim mapping to app.config for Person 1 compatibility."""

from functools import lru_cache
from app.config import Settings, settings


@lru_cache()
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return settings


__all__ = ["Settings", "get_settings", "settings"]
