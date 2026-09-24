"""AcadAssist core configuration.

Centralizes all settings, database URLs, and configurable business rule thresholds
for adaptive difficulty, weak-topic detection, and exam-aware assessment.
Re-exports unified settings from app.config.
"""

from app.config import settings, Settings, AssessmentSettings

__all__ = ["settings", "Settings", "AssessmentSettings"]
