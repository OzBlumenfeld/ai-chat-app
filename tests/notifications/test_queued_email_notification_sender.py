import os
import pytest
from unittest.mock import patch, MagicMock
from common.notifications.queued_email_notification_sender import (
    QueuedEmailNotificationSender,
)
from common.notifications.notification_sender import NotificationInput


@pytest.fixture
def mock_env_vars() -> None:
    """Set up mock environment variables"""
    with patch.dict(os.environ, {
        "GMAIL_SENDER_EMAIL": "test@gmail.com",
        "GMAIL_APP_PASSWORD": "test-password",
        "CELERY_BROKER_URL": "redis://localhost:6379/0",
        "CELERY_RESULT_BACKEND": "redis://localhost:6379/1",
    }):
        yield


@pytest.fixture
def queued_sender(mock_env_vars) -> QueuedEmailNotificationSender:
    """Create a QueuedEmailNotificationSender instance"""
    return QueuedEmailNotificationSender()


@pytest.fixture
def notification_input() -> NotificationInput:
    """Create a sample notification input"""
    return NotificationInput(
        sender_email="test@gmail.com",
        recipient_email="recipient@gmail.com",
        subject="Test Subject",
        body="This is a test email body",
    )


@pytest.mark.asyncio
async def test_queued_sender_enqueues_task(
    queued_sender: QueuedEmailNotificationSender,
    notification_input: NotificationInput,
) -> None:
    """Test that QueuedEmailNotificationSender enqueues a task"""
    with patch("common.notifications.tasks.send_email_task.delay") as mock_delay:
        mock_task = MagicMock()
        mock_task.id = "test-task-id"
        mock_delay.return_value = mock_task

        result = await queued_sender.notify(notification_input)

        assert result is True
        mock_delay.assert_called_once_with(
            sender_email="test@gmail.com",
            recipient_email="recipient@gmail.com",
            subject="Test Subject",
            body="This is a test email body",
        )


@pytest.mark.asyncio
async def test_queued_sender_handles_enqueue_failure(
    queued_sender: QueuedEmailNotificationSender,
    notification_input: NotificationInput,
) -> None:
    """Test that QueuedEmailNotificationSender handles enqueue failures"""
    with patch("common.notifications.tasks.send_email_task.delay") as mock_delay:
        mock_delay.side_effect = Exception("Connection to broker failed")

        result = await queued_sender.notify(notification_input)

        assert result is False
