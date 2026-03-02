import logging
import uuid
from pathlib import Path

from app.config import Settings
from app.services.interfaces import AbstractFileStorageService

logger = logging.getLogger(__name__)


class FileStorageService(AbstractFileStorageService):
    """Local disk file storage service."""

    def __init__(self, settings: Settings) -> None:
        self._root = Path(settings.FILE_STORAGE_ROOT)

    def save(
        self,
        category: str,
        user_id: uuid.UUID,
        filename: str,
        content: bytes,
        subdirectory: str | None = None,
    ) -> str:
        """Save content to disk and return the relative path."""
        dir_path = self._root / category / str(user_id)
        if subdirectory:
            dir_path = dir_path / subdirectory
        dir_path.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = dir_path / unique_filename
        file_path.write_bytes(content)

        logger.debug("Saved file", extra={"path": str(file_path.relative_to(self._root))})
        return str(file_path.relative_to(self._root))

    def read(self, file_path: str) -> bytes:
        """Read content from a relative path under the storage root."""
        full_path = self._root / file_path
        if not full_path.exists():
            logger.error("File not found", extra={"path": file_path})
            raise FileNotFoundError(f"File not found: {file_path}")
        return full_path.read_bytes()

    def delete(self, file_path: str) -> None:
        """Delete a file by its relative path under the storage root."""
        full_path = self._root / file_path
        full_path.unlink(missing_ok=True)


# Module-level singleton
def _create_default() -> FileStorageService:
    from app.config import settings

    return FileStorageService(settings=settings)


file_storage_service = _create_default()
