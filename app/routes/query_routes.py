import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models import Request as RequestLog
from app.rate_limit import query_rate_limiter
from app.schemas import QueryRequest, QueryResponse
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse, dependencies=[Depends(query_rate_limiter)])
async def query_model(
    request: QueryRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QueryResponse:
    if not rag_service.is_ready:
        raise HTTPException(
            status_code=503,
            detail="Service is not initialized. Please wait a moment and try again.",
        )

    try:
        answer, source = await rag_service.query(request.question, current_user["user_id"])

        session.add(RequestLog(
            user_id=current_user["user_id"],
            question=request.question,
            answer=answer,
            source=source,
        ))
        await session.commit()

        return QueryResponse(answer=answer, source=source)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error during query processing: %s", e)
        raise HTTPException(status_code=500, detail="Failed to process the query.")
