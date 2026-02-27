import logging
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.common.uuid_mask import MaskedUUID
from app.config import settings
from app.database import get_session
from app.models.document import Document
from app.rate_limit import upload_rate_limiter
from app.schemas import DocumentListResponse, DocumentResponse, UploadResponse
from app.services.document_service import DocumentValidationError, document_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse, dependencies=[Depends(upload_rate_limiter)])
async def upload_documents(
    files: list[UploadFile] = File(...),
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UploadResponse:
    """Upload one or more documents (PDF or TXT files)."""
    user_id = current_user["user_id"]
    user_email = current_user["email"]

    if len(files) > settings.MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.MAX_FILES_PER_UPLOAD} files allowed per upload",
        )

    uploaded = []
    errors = []

    for file in files:
        try:
            document_service.validate_file(file)
            document = await document_service.process_document(
                file, user_id, user_email, session
            )
            uploaded.append(
                DocumentResponse(
                    id=document.id,
                    original_filename=document.original_filename,
                    file_size=document.file_size,
                    chunk_count=document.chunk_count,
                    status=document.status,
                    created_at=document.created_at,
                )
            )
        except DocumentValidationError as e:
            logger.warning("Validation failed for '%s': %s", file.filename, e)
            errors.append(f"{file.filename}: {str(e)}")
        except Exception as e:
            logger.error("Failed to process '%s': %s", file.filename, e)
            errors.append(f"{file.filename}: {str(e)}")

    return UploadResponse(uploaded=uploaded, errors=errors)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentListResponse:
    """List all documents for the current user."""
    documents = await document_service.list_documents(current_user["user_id"], session)
    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=doc.id,
                original_filename=doc.original_filename,
                file_size=doc.file_size,
                chunk_count=doc.chunk_count,
                status=doc.status,
                created_at=doc.created_at,
            )
            for doc in documents
        ]
    )


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: MaskedUUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Delete a document and its vectors."""
    try:
        await document_service.delete_document(doc_id, current_user["user_id"], session)
        return {"message": "Document deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: MaskedUUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DocumentResponse:
    """Get document details."""
    query = select(Document).where(
        (Document.id == doc_id) & (Document.user_id == current_user["user_id"])
    )
    result = await session.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        file_size=document.file_size,
        chunk_count=document.chunk_count,
        status=document.status,
        created_at=document.created_at,
    )
