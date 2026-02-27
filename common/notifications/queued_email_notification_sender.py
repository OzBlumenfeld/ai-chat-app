import logging
from typing import override

from .notification_sender import NotificationInput, NotificationSender
from .tasks import send_email_task

logger = logging.getLogger(__name__)


class QueuedEmailNotificationSender(NotificationSender):
    """
    Sends emails asynchronously by enqueueing them to Celery.

    Notifications are added to the queue immediately (non-blocking) and
    processed by Celery workers when available.
    """

    @override
    async def notify(self, notification_input: NotificationInput) -> bool:
        """
        Enqueue an email sending task.

        Args:
            notification_input: Email details to send

        Returns:
            True if task was enqueued successfully, False otherwise
        """
        try:
            task = send_email_task.delay(
                sender_email=notification_input.sender_email,
                recipient_email=notification_input.recipient_email,
                subject=notification_input.subject,
                body=notification_input.body,
            )
            logger.info(
                f"Email task enqueued (task_id={task.id}) to {notification_input.recipient_email}"
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to enqueue email to {notification_input.recipient_email}: {e}",
                exc_info=True,
            )
            return False
