import os
import pytest
from unittest.mock import patch, AsyncMock
from common.notifications.tasks import send_email_task


@pytest.fixture
def mock_env_vars() -> None:
    """Set up mock environment variables"""
    with patch.dict(os.environ, {
        "GMAIL_SENDER_EMAIL": "test@gmail.com",
        "GMAIL_APP_PASSWORD": "test-password",
    }):
        yield


def test_send_email_task_success(mock_env_vars) -> None:
    """Test successful email sending task"""
    with patch(
        "common.notifications.email_notification_sender.EmailNotificationSender.notify",
        new_callable=AsyncMock,
    ) as mock_notify:
        mock_notify.return_value = True

        result = send_email_task(
            sender_email="test@gmail.com",
            recipient_email="recipient@gmail.com",
            subject="Test",
            body="Test body",
        )

        assert result is True
        mock_notify.assert_called_once()


def test_send_email_task_creates_notification(mock_env_vars) -> None:
    """Test email sending task creates proper NotificationInput"""
    with patch(
        "common.notifications.email_notification_sender.EmailNotificationSender.notify",
        new_callable=AsyncMock,
    ) as mock_notify:
        mock_notify.return_value = True

        send_email_task(
            sender_email="test@gmail.com",
            recipient_email="recipient@gmail.com",
            subject="Test Subject",
            body="Test body",
        )

        # Verify notify was called with correct NotificationInput
        assert mock_notify.called
        call_args = mock_notify.call_args
        notification = call_args[0][0]  # First positional arg
        assert notification.sender_email == "test@gmail.com"
        assert notification.recipient_email == "recipient@gmail.com"
        assert notification.subject == "Test Subject"
        assert notification.body == "Test body"
