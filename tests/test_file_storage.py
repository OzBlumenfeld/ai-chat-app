"""Tests for FileStorageService."""
import uuid
from pathlib import Path

import pytest

from app.config import Settings
from app.services.file_storage_service import FileStorageService


@pytest.fixture()
def storage_service(tmp_path: Path) -> FileStorageService:
    """Create a FileStorageService using a temporary directory."""
    settings = Settings(FILE_STORAGE_ROOT=str(tmp_path))
    return FileStorageService(settings=settings)


class TestFileStorageSave:
    def test_save_returns_relative_path(self, storage_service: FileStorageService) -> None:
        user_id = uuid.uuid4()
        path = storage_service.save("uploads", user_id, "test.txt", b"hello")
        assert path.startswith("uploads/")
        assert str(user_id) in path
        assert "test.txt" in path

    def test_save_creates_file_on_disk(
        self, storage_service: FileStorageService, tmp_path: Path
    ) -> None:
        user_id = uuid.uuid4()
        rel_path = storage_service.save("responses", user_id, "resp.txt", b"content")
        full_path = tmp_path / rel_path
        assert full_path.exists()
        assert full_path.read_bytes() == b"content"

    def test_save_different_categories_create_separate_dirs(
        self, storage_service: FileStorageService, tmp_path: Path
    ) -> None:
        user_id = uuid.uuid4()
        storage_service.save("uploads", user_id, "a.txt", b"a")
        storage_service.save("responses", user_id, "b.txt", b"b")
        assert (tmp_path / "uploads" / str(user_id)).is_dir()
        assert (tmp_path / "responses" / str(user_id)).is_dir()

    def test_save_with_subdirectory(
        self, storage_service: FileStorageService, tmp_path: Path
    ) -> None:
        user_id = uuid.uuid4()
        rel_path = storage_service.save(
            "responses", user_id, "resp.txt", b"data", subdirectory="02-2026"
        )
        assert "02-2026" in rel_path
        full_path = tmp_path / rel_path
        assert full_path.exists()
        assert full_path.read_bytes() == b"data"
        assert (tmp_path / "responses" / str(user_id) / "02-2026").is_dir()

    def test_save_without_subdirectory_unchanged(
        self, storage_service: FileStorageService, tmp_path: Path
    ) -> None:
        user_id = uuid.uuid4()
        rel_path = storage_service.save("responses", user_id, "resp.txt", b"data")
        parts = Path(rel_path).parts
        # Should be: responses / {user_id} / {uuid}_resp.txt (3 parts, no subdirectory)
        assert len(parts) == 3


class TestFileStorageRead:
    def test_read_returns_saved_content(self, storage_service: FileStorageService) -> None:
        user_id = uuid.uuid4()
        rel_path = storage_service.save("test", user_id, "data.bin", b"binary data")
        content = storage_service.read(rel_path)
        assert content == b"binary data"

    def test_read_nonexistent_raises_error(self, storage_service: FileStorageService) -> None:
        with pytest.raises(FileNotFoundError):
            storage_service.read("nonexistent/path/file.txt")


class TestFileStorageDelete:
    def test_delete_removes_file(
        self, storage_service: FileStorageService, tmp_path: Path
    ) -> None:
        user_id = uuid.uuid4()
        rel_path = storage_service.save("test", user_id, "delete_me.txt", b"bye")
        full_path = tmp_path / rel_path
        assert full_path.exists()

        storage_service.delete(rel_path)
        assert not full_path.exists()

    def test_delete_nonexistent_does_not_raise(
        self, storage_service: FileStorageService
    ) -> None:
        storage_service.delete("nonexistent/path/file.txt")
