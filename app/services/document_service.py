from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LangChainDocument
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.document import Document
from app.models.user import Request
from app.services.interfaces import AbstractDocumentService

if TYPE_CHECKING:
    from app.services.file_storage_service import FileStorageService

logger = logging.getLogger(__name__)

UPLOADS_CATEGORY = "uploads"


class DocumentValidationError(Exception):
    """Raised when document validation fails."""
    pass


class DocumentService(AbstractDocumentService):
    """Service for handling document uploads and management."""

    def __init__(self, settings: Settings, file_storage: FileStorageService) -> None:
        self._settings = settings
        self._file_storage = file_storage
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600, chunk_overlap=100
        )
        self._pgvector_connection: str | None = None
        self._embeddings: HuggingFaceEmbeddings | None = None

    async def initialize(self) -> None:
        """Initialize pgvector connection and embeddings."""
        logger.info("Initializing DocumentService...")
        self._pgvector_connection = self._settings.pgvector_connection_string
        self._embeddings = HuggingFaceEmbeddings(
            model_name=self._settings.EMBEDDING_MODEL_NAME
        )

    def validate_file(self, file: UploadFile) -> None:
        """Validate uploaded file type and size."""
        if not file.filename:
            raise DocumentValidationError("File must have a valid filename")

        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self._settings.ALLOWED_EXTENSIONS:
            raise DocumentValidationError(
                f"Only {', '.join(self._settings.ALLOWED_EXTENSIONS)} files are supported"
            )

        if file.size and file.size > self._settings.MAX_UPLOAD_SIZE:
            raise DocumentValidationError(
                f"File size exceeds {self._settings.MAX_UPLOAD_SIZE / (1024 * 1024):.0f}MB limit"
            )

    async def process_document(
        self,
        file: UploadFile,
        user_id: uuid.UUID,
        user_email: str,
        session: AsyncSession,
    ) -> Document:
        """Process an uploaded document (PDF or TXT) and add to user's pgvector collection."""
        logger.info("Processing document", extra={"doc_filename": file.filename, "user_id": str(user_id)})
        document = Document(
            user_id=user_id,
            original_filename=file.filename,
            file_size=0,
            collection_name=self._get_user_collection_name(user_id),
            status="processing",
        )
        try:
            session.add(document)
            await session.flush()

            content = await self._read_file_content(file)
            self._file_storage.save(
                UPLOADS_CATEGORY, user_id, file.filename or "unknown", content
            )

            file_ext = Path(file.filename).suffix.lower()

            # Load document based on file type
            if file_ext == ".pdf":
                documents = await self._load_pdf(content)
            elif file_ext == ".txt":
                documents = await self._load_text(content, file.filename)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")

            if not documents:
                raise ValueError(f"No content found in {file.filename}")

            splits = self._text_splitter.split_documents(documents)

            if not splits:
                raise ValueError("No text chunks created from file")

            # Enrich each chunk with doc_id and clean filename for citation
            for split in splits:
                split.metadata["doc_id"] = str(document.id)
                split.metadata["filename"] = file.filename or "unknown"
                # Replace temp file paths from PyPDFLoader with the original name
                src = split.metadata.get("source", "")
                if src.startswith("/tmp") or src.startswith("/var"):
                    split.metadata["source"] = file.filename or "unknown"

            collection_name = self._get_user_collection_name(user_id)
            ids = [f"{document.id}_{idx}" for idx in range(len(splits))]

            pgvector_connection = self._pgvector_connection
            embeddings = self._embeddings

            await asyncio.to_thread(
                PGVector.from_documents,
                documents=splits,
                embedding=embeddings,
                collection_name=collection_name,
                connection=pgvector_connection,
                ids=ids,
                pre_delete_collection=False,
            )

            document.file_size = len(content)
            document.chunk_count = len(splits)
            document.status = "ready"
            document.error_message = None

            logger.info("Document processed", extra={"doc_filename": file.filename, "chunks": len(splits)})
            await session.commit()
            return document

        except Exception as e:
            logger.error("Failed to process document", extra={"doc_filename": file.filename, "error": str(e)})
            document.status = "failed"
            document.error_message = str(e)
            await session.commit()
            raise ValueError(f"Failed to process document: {str(e)}")

    async def list_documents(
        self, user_id: uuid.UUID, session: AsyncSession
    ) -> list[Document]:
        """Get all documents for a user."""
        query = select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
        result = await session.execute(query)
        return list(result.scalars().all())

    async def delete_document(
        self, doc_id: uuid.UUID, user_id: uuid.UUID, session: AsyncSession
    ) -> None:
        """Delete a document and its vectors from pgvector."""
        query = select(Document).where(
            (Document.id == doc_id) & (Document.user_id == user_id)
        )
        result = await session.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError("Document not found or unauthorized")

        collection_name = self._get_user_collection_name(user_id)
        doc_ids = [
            f"{doc_id}_{idx}"
            for idx in range(document.chunk_count or 0)
        ]
        if doc_ids:
            try:
                vectorstore = PGVector(
                    embeddings=self._embeddings,
                    collection_name=collection_name,
                    connection=self._pgvector_connection,
                )
                await asyncio.to_thread(vectorstore.delete, ids=doc_ids)
            except Exception as e:
                logger.warning("Failed to delete vectors from pgvector", extra={"error": str(e)})

        await session.delete(document)
        await session.commit()

    async def delete_all_documents(
        self, user_id: uuid.UUID, session: AsyncSession
    ) -> int:
        """Delete all documents for a user and their entire pgvector collection.

        Also exports and deletes all user requests to deleted_users/{user_id}/requests.json.
        """
        collection_name = self._get_user_collection_name(user_id)

        # Export and delete user requests
        await self._export_and_delete_requests(user_id, session)

        # Delete the entire pgvector collection for this user
        try:
            vectorstore = PGVector(
                embeddings=self._embeddings,
                collection_name=collection_name,
                connection=self._pgvector_connection,
            )
            await asyncio.to_thread(vectorstore.delete_collection)
            logger.info("Deleted pgvector collection", extra={"collection": collection_name})
        except Exception as e:
            logger.warning("Failed to delete pgvector collection", extra={"collection": collection_name, "error": str(e)})

        # Delete all document records from PostgreSQL
        query = select(Document).where(Document.user_id == user_id)
        result = await session.execute(query)
        documents = list(result.scalars().all())

        count = len(documents)
        for doc in documents:
            await session.delete(doc)

        await session.commit()
        logger.info("Deleted all documents for user", extra={"user_id": str(user_id), "count": count})

        return count

    async def _export_and_delete_requests(
        self, user_id: uuid.UUID, session: AsyncSession
    ) -> None:
        """Export user requests to JSON and delete them from the database."""
        # Fetch all requests for the user
        query = select(Request).where(Request.user_id == user_id).order_by(Request.created_at)
        result = await session.execute(query)
        requests = list(result.scalars().all())

        if not requests:
            logger.info("No requests to export", extra={"user_id": str(user_id)})
            return

        # Prepare export data
        export_data = [
            {
                "id": str(req.id),
                "question": req.question,
                "answer": req.answer,
                "source": req.source,
                "created_at": req.created_at.isoformat() if isinstance(req.created_at, datetime) else str(req.created_at),
            }
            for req in requests
        ]

        # Save to deleted_users/{user_id}/requests.json
        export_dir = self._file_storage._root / "deleted_users" / str(user_id)
        export_dir.mkdir(parents=True, exist_ok=True)

        export_file = export_dir / "requests.json"
        export_file.write_text(json.dumps(export_data, indent=2, ensure_ascii=False))

        logger.info("Exported user requests", extra={"user_id": str(user_id), "count": len(requests), "path": str(export_file)})

        # Delete all requests from the database
        for req in requests:
            await session.delete(req)

        logger.info("Deleted user requests from DB", extra={"user_id": str(user_id), "count": len(requests)})

    @staticmethod
    def _get_user_collection_name(user_id: uuid.UUID) -> str:
        """Get the collection name for a user."""
        return f"user_{user_id}"

    async def _read_file_content(self, file: UploadFile) -> bytes:
        """Read file content and validate size."""
        content = await file.read()

        if len(content) > self._settings.MAX_UPLOAD_SIZE:
            raise DocumentValidationError(
                f"File size exceeds {self._settings.MAX_UPLOAD_SIZE / (1024 * 1024):.0f}MB limit"
            )

        return content

    async def _load_pdf(self, content: bytes) -> list[LangChainDocument]:
        """Load and parse PDF content."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            loader = PyPDFLoader(tmp_path)
            documents = loader.load()
            return documents
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def _load_text(
        self, content: bytes, filename: str
    ) -> list[LangChainDocument]:
        """Load and parse text file content."""
        try:
            text = content.decode("utf-8", errors="replace")
            # Create a LangChain Document from the text
            return [
                LangChainDocument(
                    page_content=text,
                    metadata={"source": filename, "type": "text"},
                )
            ]
        except Exception as e:
            raise ValueError(f"Failed to parse text file: {str(e)}")


# Module-level singleton
def _create_default() -> DocumentService:
    from app.config import settings
    from app.services.file_storage_service import file_storage_service

    return DocumentService(settings=settings, file_storage=file_storage_service)


document_service = _create_default()
