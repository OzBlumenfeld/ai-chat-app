import logging
from celery import shared_task
from .email_notification_sender import EmailNotificationSender
from .notification_sender import NotificationInput

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_task(
    self: object,
    sender_email: str,
    recipient_email: str,
    subject: str,
    body: str,
) -> bool:
    """
    Celery task to send an email asynchronously.

    Args:
        sender_email: Email address of sender
        recipient_email: Email address of recipient
        subject: Email subject
        body: Email body

    Returns:
        True if successful, False otherwise
    """
    try:
        notification = NotificationInput(
            sender_email=sender_email,
            recipient_email=recipient_email,
            subject=subject,
            body=body,
        )

        sender = EmailNotificationSender()
        import asyncio

        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(sender.notify(notification))
        loop.close()

        return result
    except Exception as exc:
        logger.error("Task send_email_task failed", extra={"error": str(exc)}, exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
