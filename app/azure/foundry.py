"""Microsoft Foundry Project Integration Layer.

Uses Azure AI Projects SDK 2.x (`azure-ai-projects`) and `DefaultAzureCredential`.
Reads model and embedding deployments from typed configuration.
"""

import logging
from typing import Optional
from azure.core.credentials import TokenCredential
from azure.ai.projects import AIProjectClient
import openai

from config.settings import get_settings
from app.azure.credentials import get_azure_credential

logger = logging.getLogger(__name__)


_DEFAULT = object()


class FoundryProjectManager:
    """Manager for Microsoft Foundry Project connection and client lifecycle."""

    def __init__(
        self,
        endpoint: Optional[str] = _DEFAULT,
        credential: Optional[TokenCredential] = None,
        model_deployment: Optional[str] = _DEFAULT,
        embedding_deployment: Optional[str] = _DEFAULT,
    ):
        settings = get_settings()
        self.endpoint = settings.foundry_project_endpoint if endpoint is _DEFAULT else endpoint
        self.credential = credential or get_azure_credential()
        self.model_deployment = settings.foundry_model_deployment if model_deployment is _DEFAULT else model_deployment
        self.embedding_deployment = settings.foundry_embedding_deployment if embedding_deployment is _DEFAULT else embedding_deployment
        self._project_client: Optional[AIProjectClient] = None
        self._openai_client: Optional[openai.OpenAI] = None

    @property
    def is_configured(self) -> bool:
        """Check whether get_openai_client() can actually authenticate.

        get_openai_client() supports three independent auth paths: a Foundry
        Project endpoint (Entra ID), a direct Azure OpenAI key + endpoint, or
        a plain OpenAI API key. This must recognize all three -- previously it
        only checked the Foundry Project endpoint, which meant a deployment
        configured the way the app's own production validation requires
        (AZURE_OPENAI_API_KEY/OPENAI_API_KEY, see Settings.validate_production_azure)
        but WITHOUT a separate Foundry Project resource was treated as
        "not configured" and silently skipped real quiz generation for every
        document, always falling through to an insufficient-material error.
        """
        settings = get_settings()
        has_foundry_project = bool(self.endpoint)
        has_azure_key_pair = bool(
            (settings.AZURE_OPENAI_API_KEY or settings.AZURE_API_KEY)
            and (settings.AZURE_OPENAI_ENDPOINT or settings.AZURE_ENDPOINT)
        )
        has_plain_openai_key = bool(settings.OPENAI_API_KEY)
        return has_foundry_project or has_azure_key_pair or has_plain_openai_key

    def get_project_client(self) -> AIProjectClient:
        """Get or initialize AIProjectClient using Entra ID credentials."""
        if self._project_client is None:
            if not self.endpoint:
                raise ValueError(
                    "Foundry Project endpoint is not configured. Set FOUNDRY_PROJECT_ENDPOINT in .env."
                )
            logger.info("Connecting to Microsoft Foundry project at %s", self.endpoint)
            self._project_client = AIProjectClient(
                endpoint=self.endpoint,
                credential=self.credential,
            )
        return self._project_client

    def get_openai_client(self) -> openai.OpenAI:
        """Get the authenticated OpenAI client configured for this Foundry project.

        Prefers direct AzureOpenAI construction using AZURE_OPENAI_API_KEY +
        AZURE_OPENAI_ENDPOINT when available (API-key path, no Entra ID required).
        Falls back to AIProjectClient.get_openai_client() when only Entra ID
        credentials are configured (Managed Identity / Azure CLI / VS Code auth).
        """
        if self._openai_client is None:
            settings = get_settings()
            api_key = settings.AZURE_OPENAI_API_KEY or settings.AZURE_API_KEY
            azure_endpoint = settings.AZURE_OPENAI_ENDPOINT or settings.AZURE_ENDPOINT

            if api_key and azure_endpoint:
                # Direct API-key path - works without Entra ID / DefaultAzureCredential.
                # Mirrors how EmbeddingService (embedding.py) authenticates.
                logger.info(
                    "Creating AzureOpenAI client with API key for endpoint %s", azure_endpoint
                )
                self._openai_client = openai.AzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=azure_endpoint,
                    api_version="2024-12-01-preview",
                )
            elif settings.OPENAI_API_KEY:
                # Plain OpenAI API-key path - no Azure resource required at all.
                logger.info("Creating plain OpenAI client (no Azure endpoint configured)")
                self._openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            elif self.endpoint:
                # Entra ID / DefaultAzureCredential path (Managed Identity, Azure CLI, etc.)
                logger.info(
                    "No API key found; using AIProjectClient with DefaultAzureCredential"
                )
                project_client = self.get_project_client()
                self._openai_client = project_client.get_openai_client()
            else:
                raise ValueError(
                    "No usable AI credentials configured. Set AZURE_OPENAI_API_KEY + "
                    "AZURE_OPENAI_ENDPOINT, OPENAI_API_KEY, or FOUNDRY_PROJECT_ENDPOINT in .env."
                )

        return self._openai_client


__all__ = ["FoundryProjectManager"]
