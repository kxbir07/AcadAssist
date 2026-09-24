"""Unit tests for Microsoft Foundry Project integration."""

import pytest
from unittest.mock import MagicMock, patch
from app.azure.foundry import FoundryProjectManager


def test_foundry_manager_initialization():
    """Verify initialization and deployment bindings."""
    manager = FoundryProjectManager(
        endpoint="https://test.services.ai.azure.com/api/projects/p123",
        model_deployment="gpt-4o",
        embedding_deployment="text-embedding-3-small",
    )
    assert manager.is_configured is True
    assert manager.model_deployment == "gpt-4o"
    assert manager.embedding_deployment == "text-embedding-3-small"


def test_foundry_manager_missing_endpoint_error():
    """Verify error when accessing client without configured endpoint."""
    with patch("app.azure.foundry.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_settings.foundry_project_endpoint = None
        mock_settings.AZURE_OPENAI_API_KEY = None
        mock_settings.AZURE_API_KEY = None
        mock_settings.AZURE_OPENAI_ENDPOINT = None
        mock_settings.AZURE_ENDPOINT = None
        mock_settings.OPENAI_API_KEY = None
        mock_get_settings.return_value = mock_settings

        manager = FoundryProjectManager(endpoint=None)
        assert manager.is_configured is False
        with pytest.raises(ValueError, match="Foundry Project endpoint is not configured"):
            manager.get_project_client()


@patch("app.azure.foundry.AIProjectClient")
def test_foundry_manager_client_creation(mock_client_cls):
    """Verify AIProjectClient instantiation."""
    mock_instance = MagicMock()
    mock_client_cls.return_value = mock_instance

    manager = FoundryProjectManager(endpoint="https://test.services.ai.azure.com/api/projects/p123")
    client = manager.get_project_client()

    assert client == mock_instance
    mock_client_cls.assert_called_once()
