from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


@dataclass
class SourceInfo:
    """Information about a source chunk used in a RAG response."""

    filename: str
    doc_id: str
    excerpt: str
    page: int | None = field(default=None)


class AbstractFileStorageService(ABC):
    """Interface for file storage operations."""

    @abstractmethod
    def save(
        self,
        category: str,
        user_id: UUID,
        filename: str,
        content: bytes,
        subdirectory: str | None = None,
    ) -> str: ...

    @abstractmethod
    def read(self, file_path: str) -> bytes: ...

    @abstractmethod
    def delete(self, file_path: str) -> None: ...


class AbstractRAGService(ABC):
    """Interface for RAG query services."""

    @property
    @abstractmethod
    def is_ready(self) -> bool: ...

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def query(
        self,
        question: str,
        user_id: UUID,
        history: list[dict[str, str]] | None = None,
    ) -> tuple[str, str, list[SourceInfo]]: ...


class AbstractDocumentService(ABC):
    """Interface for document management services."""

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def process_document(
        self,
        file: UploadFile,
        user_id: UUID,
        user_email: str,
        session: AsyncSession,
    ) -> Document: ...

    @abstractmethod
    async def list_documents(
        self, user_id: UUID, session: AsyncSession
    ) -> list[Document]: ...

    @abstractmethod
    async def delete_document(
        self, doc_id: UUID, user_id: UUID, session: AsyncSession
    ) -> None: ...

    @abstractmethod
    def validate_file(self, file: UploadFile) -> None: ...


class AbstractAuthService(ABC):
    """Interface for authentication services."""

    @abstractmethod
    def hash_password(self, password: str) -> str: ...

    @abstractmethod
    def verify_password(self, password: str, hashed: str) -> bool: ...

    @abstractmethod
    def create_token(self, user_id: UUID, email: str) -> str: ...
