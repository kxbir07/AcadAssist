"""Azure Credential and Identity Management.

Encapsulates authentication using Azure Identity and Entra ID (DefaultAzureCredential).
Ensures zero hardcoded secrets or access keys.
"""

import logging
from typing import Optional
from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

_cached_credential: Optional[TokenCredential] = None


def get_azure_credential(force_refresh: bool = False) -> TokenCredential:
    """Obtain a reusable DefaultAzureCredential instance.

    Uses Entra ID authentication via:
    1. Environment variables (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)
    2. Workload Identity / Managed Identity (in Azure container apps / VMs)
    3. Azure CLI (`az login`) for local development

    Does not use long-lived access keys or passwords.
    """
    global _cached_credential
    if _cached_credential is None or force_refresh:
        logger.info("Initializing DefaultAzureCredential for Entra ID authentication")
        _cached_credential = DefaultAzureCredential(
            exclude_interactive_browser_credential=True
        )
    return _cached_credential


__all__ = ["get_azure_credential"]
