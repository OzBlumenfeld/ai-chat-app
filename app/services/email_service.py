import logging

from common.notifications.email_notification_sender import EmailNotificationSender
from common.notifications.notification_sender import NotificationInput, NotificationSender

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, sender: NotificationSender) -> None:
        self._sender = sender

    async def send_email(self, recipient_email: str, subject: str, body: str) -> bool:
        notification = NotificationInput(
            sender_email=settings.GMAIL_SENDER_EMAIL,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
        )
        return await self._sender.notify(notification)


def get_email_service() -> EmailService:
    return EmailService(sender=EmailNotificationSender())
