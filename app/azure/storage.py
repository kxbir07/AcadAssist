"""Azure Blob Storage Infrastructure Integration.

Responsible for securely interacting with Azure Blob Storage
using Entra ID / DefaultAzureCredential.
Does NOT implement extraction, chunking, or embedding (owned by Person 2).
"""

import logging
from typing import BinaryIO, List, Optional, Union
from azure.core.credentials import TokenCredential
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContainerClient, ContentSettings

from config.settings import get_settings
from app.azure.credentials import get_azure_credential

logger = logging.getLogger(__name__)


_DEFAULT = object()


class AzureStorageClient:
    """Infrastructure client for managing AcadAssist study materials in Azure Blob Storage."""

    def __init__(
        self,
        storage_account: Optional[str] = _DEFAULT,
        container_name: Optional[str] = _DEFAULT,
        credential: Optional[TokenCredential] = None,
    ):
        settings = get_settings()
        self.storage_account = settings.azure_storage_account if storage_account is _DEFAULT else storage_account
        self.container_name = settings.azure_storage_container if container_name is _DEFAULT else container_name
        self.credential = credential or get_azure_credential()
        self._blob_service_client: Optional[BlobServiceClient] = None
        self._container_client: Optional[ContainerClient] = None

    @property
    def account_url(self) -> Optional[str]:
        """Construct blob service URL from storage account name."""
        if not self.storage_account:
            return None
        if self.storage_account.startswith("http"):
            return self.storage_account
        return f"https://{self.storage_account}.blob.core.windows.net"

    def get_service_client(self) -> BlobServiceClient:
        """Initialize or return cached BlobServiceClient."""
        if self._blob_service_client is None:
            if not self.account_url:
                raise ValueError(
                    "Azure Storage Account is not configured. Set AZURE_STORAGE_ACCOUNT."
                )
            logger.info("Connecting to Azure Blob Storage at %s", self.account_url)
            self._blob_service_client = BlobServiceClient(
                account_url=self.account_url,
                credential=self.credential,
            )
        return self._blob_service_client

    def get_container_client(self) -> ContainerClient:
        """Initialize or return cached ContainerClient."""
        if self._container_client is None:
            service_client = self.get_service_client()
            self._container_client = service_client.get_container_client(self.container_name)
        return self._container_client

    def ensure_container_exists(self) -> bool:
        """Ensure the target container exists; creates it if absent."""
        container_client = self.get_container_client()
        try:
            container_client.create_container()
            logger.info("Created container '%s'", self.container_name)
            return True
        except ResourceExistsError:
            logger.debug("Container '%s' already exists", self.container_name)
            return True
        except Exception as exc:
            logger.error("Failed to ensure container '%s': %s", self.container_name, exc)
            raise

    def upload_blob(
        self,
        blob_name: str,
        data: Union[bytes, BinaryIO],
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = True,
    ) -> str:
        """Upload raw academic document data to the container."""
        container_client = self.get_container_client()
        blob_client = container_client.get_blob_client(blob_name)

        content_settings = ContentSettings(content_type=content_type) if content_type else None
        blob_client.upload_blob(
            data=data,
            overwrite=overwrite,
            content_settings=content_settings,
            metadata=metadata or {},
        )
        logger.info("Uploaded blob '%s' (%s bytes)", blob_name, len(data) if isinstance(data, bytes) else "stream")
        return blob_client.url

    def download_blob(self, blob_name: str) -> bytes:
        """Download raw blob content as bytes."""
        container_client = self.get_container_client()
        blob_client = container_client.get_blob_client(blob_name)
        try:
            stream = blob_client.download_blob()
            return stream.readall()
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob '{blob_name}' not found in container '{self.container_name}'")

    def list_blobs(self, prefix: Optional[str] = None) -> List[str]:
        """List blob names in the container with an optional prefix."""
        container_client = self.get_container_client()
        return [b.name for b in container_client.list_blobs(name_starts_with=prefix)]

    def delete_blob(self, blob_name: str) -> bool:
        """Delete a blob from the container."""
        container_client = self.get_container_client()
        blob_client = container_client.get_blob_client(blob_name)
        try:
            blob_client.delete_blob()
            logger.info("Deleted blob '%s'", blob_name)
            return True
        except ResourceNotFoundError:
            return False


__all__ = ["AzureStorageClient"]
