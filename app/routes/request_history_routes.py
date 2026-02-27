import logging
from itertools import groupby
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.common.uuid_mask import MaskedUUID
from app.database import get_session
from app.models.user import Request
from app.schemas import (
    MonthGroup,
    RequestHistoryDetailResponse,
    RequestHistoryGroupedResponse,
    RequestHistoryListResponse,
    RequestHistoryResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=RequestHistoryListResponse)
async def list_history(
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RequestHistoryListResponse:
    """List all request history entries for the current user."""
    result = await session.execute(
        select(Request)
        .where(Request.user_id == current_user["user_id"])
        .order_by(Request.created_at.desc())
    )
    requests = list(result.scalars().all())
    return RequestHistoryListResponse(
        history=[
            RequestHistoryResponse(
                id=r.id,
                question=r.question,
                source=r.source,
                created_at=r.created_at,
            )
            for r in requests
        ]
    )


@router.get("/grouped", response_model=RequestHistoryGroupedResponse)
async def list_history_grouped(
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RequestHistoryGroupedResponse:
    """List request history entries grouped by month."""
    result = await session.execute(
        select(Request)
        .where(Request.user_id == current_user["user_id"])
        .order_by(Request.created_at.desc())
    )
    requests = list(result.scalars().all())

    def _month_key(r: Request) -> str:
        return r.created_at.strftime("%m-%Y")

    groups: list[MonthGroup] = []
    for month, group_reqs in groupby(requests, key=_month_key):
        groups.append(
            MonthGroup(
                month=month,
                entries=[
                    RequestHistoryResponse(
                        id=r.id,
                        question=r.question,
                        source=r.source,
                        created_at=r.created_at,
                    )
                    for r in group_reqs
                ],
            )
        )

    return RequestHistoryGroupedResponse(groups=groups)


@router.get("/{request_id}", response_model=RequestHistoryDetailResponse)
async def get_history_detail(
    request_id: MaskedUUID,
    current_user: dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RequestHistoryDetailResponse:
    """Get a specific history entry with its full response."""
    result = await session.execute(
        select(Request).where(
            (Request.id == request_id) & (Request.user_id == current_user["user_id"])
        )
    )
    request = result.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="History entry not found")

    return RequestHistoryDetailResponse(
        id=request.id,
        question=request.question,
        source=request.source,
        created_at=request.created_at,
        response=request.answer,
    )
