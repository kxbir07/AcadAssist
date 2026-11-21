"""Local file system storage service for development and testing."""

import os
import uuid
from pathlib import Path
from app.config import settings
from app.services.storage.base import StorageService


class LocalStorageService(StorageService):
    """Local file system implementation of StorageService."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or settings.STORAGE_LOCAL_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_bytes: bytes, filename: str, user_id: str) -> str:
        """Save file bytes in a user-partitioned directory."""
        user_dir = self.base_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)

        unique_id = str(uuid.uuid4())[:8]
        safe_filename = f"{unique_id}_{Path(filename).name}"
        destination = user_dir / safe_filename

        with open(destination, "wb") as f:
            f.write(file_bytes)

        return str(destination)

    def get_file(self, storage_path: str) -> bytes:
        """Read file bytes from local disk."""
        path = Path(storage_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found at storage path: {storage_path}")
        with open(path, "rb") as f:
            return f.read()

    def delete_file(self, storage_path: str) -> bool:
        """Delete file from local disk."""
        path = Path(storage_path)
        if path.exists():
            path.unlink()
            return True
        return False
