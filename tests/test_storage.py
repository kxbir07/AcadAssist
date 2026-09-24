"""Unit tests for Azure Storage client infrastructure."""

import pytest
from unittest.mock import MagicMock, patch
from app.azure.storage import AzureStorageClient


def test_storage_client_initialization():
    """Verify initialization and URL computation."""
    client = AzureStorageClient(storage_account="teststorage", container_name="acadassist-documents")
    assert client.storage_account == "teststorage"
    assert client.container_name == "acadassist-documents"
    assert client.account_url == "https://teststorage.blob.core.windows.net"


def test_storage_client_missing_account_error():
    """Verify error when attempting to access service without storage account."""
    client = AzureStorageClient(storage_account=None)
    with pytest.raises(ValueError, match="Azure Storage Account is not configured"):
        client.get_service_client()


@patch("app.azure.storage.BlobServiceClient")
def test_storage_upload_download(mock_service_cls):
    """Verify upload and download delegate to Azure SDK clients."""
    mock_service = MagicMock()
    mock_container = MagicMock()
    mock_blob = MagicMock()
    mock_service_cls.return_value = mock_service
    mock_service.get_container_client.return_value = mock_container
    mock_container.get_blob_client.return_value = mock_blob
    mock_blob.url = "https://teststorage.blob.core.windows.net/acadassist-documents/lecture1.pdf"
    mock_blob.download_blob.return_value.readall.return_value = b"PDF content"

    client = AzureStorageClient(storage_account="teststorage", container_name="acadassist-documents")

    url = client.upload_blob("lecture1.pdf", b"PDF content", content_type="application/pdf")
    assert url == "https://teststorage.blob.core.windows.net/acadassist-documents/lecture1.pdf"
    mock_blob.upload_blob.assert_called_once()

    data = client.download_blob("lecture1.pdf")
    assert data == b"PDF content"
