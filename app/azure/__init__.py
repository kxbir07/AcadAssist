"""Azure and Microsoft Foundry Integration Layer for AcadAssist."""

from app.azure.credentials import get_azure_credential
from app.azure.storage import AzureStorageClient
from app.azure.search import AzureSearchManager, build_acadassist_index_schema
from app.azure.foundry import FoundryProjectManager
from app.azure.agent import AcadAssistAgentService
from app.azure.tools import get_agent_tools, FOUNDRY_TOOL_DEFINITIONS
from app.azure.adapters import ToolDispatcher

__all__ = [
    "get_azure_credential",
    "AzureStorageClient",
    "AzureSearchManager",
    "build_acadassist_index_schema",
    "FoundryProjectManager",
    "AcadAssistAgentService",
    "get_agent_tools",
    "FOUNDRY_TOOL_DEFINITIONS",
    "ToolDispatcher",
]
