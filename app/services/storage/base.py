"""Abstract base class for storage services."""

from abc import ABC, abstractmethod


class StorageService(ABC):
    """Abstract storage service interface."""

    @abstractmethod
    def save_file(self, file_bytes: bytes, filename: str, user_id: str) -> str:
        """Save raw document bytes and return a unique storage_path."""
        pass

    @abstractmethod
    def get_file(self, storage_path: str) -> bytes:
        """Retrieve raw document bytes from storage."""
        pass

    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """Delete raw document from storage. Return True if deleted or already absent."""
        pass
