"""Azure Blob Storage implementation of StorageService."""

import logging
import uuid
from pathlib import Path

from app.config import settings
from app.services.storage.base import StorageService
from app.services.storage.local_storage import LocalStorageService

logger = logging.getLogger(__name__)

# Cache connection failure in non-production to prevent repeated Entra ID / network hangs
_azure_storage_unreachable: bool = False


class AzureStorageService(StorageService):
    """Azure Blob Storage service with production enforcement and dev fallback."""

    def __init__(
        self,
        connection_string: str | None = None,
        container_name: str | None = None,
    ):
        global _azure_storage_unreachable
        self.connection_string = connection_string or settings.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = container_name or settings.AZURE_STORAGE_CONTAINER
        self.fallback_storage: LocalStorageService | None = None
        self.azure_client = None

        has_azure_storage = bool(self.connection_string or settings.azure_storage_account)

        if settings.is_test() and not connection_string:
            self.fallback_storage = LocalStorageService()
            self.blob_service_client = None
            self.container_client = None
            return

        if not has_azure_storage or (not settings.is_production() and _azure_storage_unreachable):
            if settings.is_production():
                raise ValueError(
                    "Azure Storage configuration (AZURE_STORAGE_ACCOUNT or AZURE_STORAGE_CONNECTION_STRING) is mandatory in production environment."
                )
            self.fallback_storage = LocalStorageService()
            self.blob_service_client = None
            self.container_client = None
        else:
            try:
                from app.azure.storage import AzureStorageClient
                self.azure_client = AzureStorageClient(
                    storage_account=settings.azure_storage_account,
                    container_name=self.container_name,
                )
                if self.connection_string:
                    from azure.storage.blob import BlobServiceClient
                    self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
                    self.container_client = self.blob_service_client.get_container_client(self.container_name)
                else:
                    self.container_client = self.azure_client.get_container_client()
                    self.blob_service_client = self.azure_client.get_service_client()

                if not self.container_client.exists():
                    self.container_client.create_container()
            except Exception as e:
                if settings.is_production():
                    raise ValueError(f"Failed to connect to Azure Blob container '{self.container_name}': {e}")
                _azure_storage_unreachable = True
                logger.warning(f"Could not connect to Azure Blob container '{self.container_name}', using local fallback: {e}")
                self.fallback_storage = LocalStorageService()
                self.blob_service_client = None
                self.container_client = None

    def save_file(self, file_bytes: bytes, filename: str, user_id: str) -> str:
        """Save file bytes to Azure Blob container (or local fallback)."""
        if self.fallback_storage:
            return self.fallback_storage.save_file(file_bytes, filename, user_id)

        blob_name = f"{user_id}/{uuid.uuid4().hex[:8]}_{Path(filename).name}"
        blob_client = self.container_client.get_blob_client(blob_name)
        blob_client.upload_blob(file_bytes, overwrite=True)
        return f"azure://{self.container_name}/{blob_name}"

    def get_file(self, storage_path: str) -> bytes:
        """Retrieve file bytes from Azure Blob container (or local fallback)."""
        if self.fallback_storage:
            return self.fallback_storage.get_file(storage_path)

        if not storage_path.startswith("azure://"):
            if Path(storage_path).exists():
                with open(storage_path, "rb") as f:
                    return f.read()
            raise ValueError(f"Invalid Azure storage path: {storage_path}")

        raw_path = storage_path.replace(f"azure://{self.container_name}/", "")
        blob_client = self.container_client.get_blob_client(raw_path)
        return blob_client.download_blob().readall()

    def delete_file(self, storage_path: str) -> bool:
        """Delete blob from Azure container (or local fallback)."""
        if self.fallback_storage:
            return self.fallback_storage.delete_file(storage_path)

        if not storage_path.startswith("azure://"):
            if Path(storage_path).exists():
                Path(storage_path).unlink()
                return True
            return False

        raw_path = storage_path.replace(f"azure://{self.container_name}/", "")
        blob_client = self.container_client.get_blob_client(raw_path)
        if blob_client.exists():
            blob_client.delete_blob()
            return True
        return False
