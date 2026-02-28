import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.schemas import SendEmailRequest, SendEmailResponse
from app.services.email_service import EmailService, get_email_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/send", response_model=SendEmailResponse)
async def send_email(
    body: SendEmailRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
    email_service: EmailService = Depends(get_email_service),
) -> SendEmailResponse:
    success = await email_service.send_email(
        recipient_email=str(body.recipient_email),
        subject=body.subject,
        body=body.body,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email")
    return SendEmailResponse(success=True, message="Email sent successfully")
