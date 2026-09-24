"""Unit tests for configuration system."""

import os
import pytest
from config.settings import Settings, get_settings


def test_settings_defaults():
    """Verify default values for development settings."""
    settings = Settings()
    assert settings.foundry_agent_name == "AcadAssist"
    assert settings.foundry_model_deployment in ("gpt-4o", "gpt-4.1-mini")
    assert settings.foundry_embedding_deployment == "text-embedding-3-small"
    assert settings.azure_search_index in ("acadassist-index", "acadassist-knowledge-index")
    assert settings.azure_storage_container in ("acadassist-documents", "study-materials")
    assert settings.environment == "development"
    assert settings.is_development is True


def test_settings_custom_env(monkeypatch):
    """Verify environment variables override defaults properly."""
    monkeypatch.setenv("FOUNDRY_PROJECT_ENDPOINT", "https://custom.services.ai.azure.com/api/projects/p123")
    monkeypatch.setenv("FOUNDRY_MODEL_DEPLOYMENT", "gpt-4o-mini")
    monkeypatch.setenv("AZURE_SEARCH_ENDPOINT", "https://mysearch.search.windows.net")
    monkeypatch.setenv("AZURE_STORAGE_ACCOUNT", "mystorageacct")

    settings = Settings()
    assert settings.foundry_project_endpoint == "https://custom.services.ai.azure.com/api/projects/p123"
    assert settings.foundry_model_deployment == "gpt-4o-mini"
    assert settings.azure_search_endpoint == "https://mysearch.search.windows.net"
    assert settings.azure_storage_account == "mystorageacct"
    assert settings.azure_storage_endpoint == "https://mystorageacct.blob.core.windows.net"
    assert settings.is_foundry_configured is True
    assert settings.is_search_configured is True
    assert settings.is_storage_configured is True
