"""Regression test: quiz generation must work when only AZURE_OPENAI_API_KEY +
AZURE_OPENAI_ENDPOINT are configured, with NO FOUNDRY_PROJECT_ENDPOINT set.

This is the configuration the app's own Settings.validate_production_azure()
requires and validates as sufficient for production. Before this fix,
FoundryProjectManager.is_configured checked only FOUNDRY_PROJECT_ENDPOINT, so
a deployment configured exactly per the app's own documented requirements
would silently skip real LLM quiz generation for every document and always
return an "insufficient_material" error, even with perfectly good, retrieved
document chunks.
"""

from unittest.mock import patch
from app.azure.foundry import FoundryProjectManager


def test_is_configured_true_with_azure_openai_key_and_endpoint_only():
    """FOUNDRY_PROJECT_ENDPOINT unset, but AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT
    set -> is_configured must be True (this is the exact bug that was fixed)."""
    manager = FoundryProjectManager(endpoint=None)

    with patch("app.azure.foundry.get_settings") as mock_get_settings:
        mock_settings = mock_get_settings.return_value
        mock_settings.AZURE_OPENAI_API_KEY = "test-key"
        mock_settings.AZURE_API_KEY = None
        mock_settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com"
        mock_settings.AZURE_ENDPOINT = None
        mock_settings.OPENAI_API_KEY = None

        assert manager.is_configured is True


def test_is_configured_true_with_plain_openai_key_only():
    """Only OPENAI_API_KEY set (no Azure resource at all) -> is_configured True."""
    manager = FoundryProjectManager(endpoint=None)

    with patch("app.azure.foundry.get_settings") as mock_get_settings:
        mock_settings = mock_get_settings.return_value
        mock_settings.AZURE_OPENAI_API_KEY = None
        mock_settings.AZURE_API_KEY = None
        mock_settings.AZURE_OPENAI_ENDPOINT = None
        mock_settings.AZURE_ENDPOINT = None
        mock_settings.OPENAI_API_KEY = "sk-test"

        assert manager.is_configured is True


def test_is_configured_false_when_nothing_set():
    """No credentials anywhere -> is_configured stays False (no regression)."""
    manager = FoundryProjectManager(endpoint=None)

    with patch("app.azure.foundry.get_settings") as mock_get_settings:
        mock_settings = mock_get_settings.return_value
        mock_settings.AZURE_OPENAI_API_KEY = None
        mock_settings.AZURE_API_KEY = None
        mock_settings.AZURE_OPENAI_ENDPOINT = None
        mock_settings.AZURE_ENDPOINT = None
        mock_settings.OPENAI_API_KEY = None

        assert manager.is_configured is False


def test_get_openai_client_uses_azure_key_path_without_foundry_endpoint():
    """get_openai_client must build an AzureOpenAI client from the key/endpoint
    pair alone, without needing a Foundry Project endpoint or Entra ID."""
    manager = FoundryProjectManager(endpoint=None)

    with patch("app.azure.foundry.get_settings") as mock_get_settings, \
         patch("app.azure.foundry.openai.AzureOpenAI") as mock_azure_openai:
        mock_settings = mock_get_settings.return_value
        mock_settings.AZURE_OPENAI_API_KEY = "test-key"
        mock_settings.AZURE_API_KEY = None
        mock_settings.AZURE_OPENAI_ENDPOINT = "https://test.openai.azure.com"
        mock_settings.AZURE_ENDPOINT = None

        client = manager.get_openai_client()

        mock_azure_openai.assert_called_once_with(
            api_key="test-key",
            azure_endpoint="https://test.openai.azure.com",
            api_version="2024-12-01-preview",
        )
        assert client is mock_azure_openai.return_value
