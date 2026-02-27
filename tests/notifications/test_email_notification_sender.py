import os
import pytest
from unittest.mock import patch, MagicMock
from common.notifications.email_notification_sender import EmailNotificationSender
from common.notifications.notification_sender import NotificationInput


@pytest.fixture
def mock_env_vars() -> None:
    """Set up mock environment variables"""
    with patch.dict(os.environ, {
        "GMAIL_SENDER_EMAIL": "test@gmail.com",
        "GMAIL_APP_PASSWORD": "test-password",
        "GMAIL_SMTP_SERVER": "smtp.gmail.com",
        "GMAIL_SMTP_PORT": "587",
    }):
        yield


@pytest.fixture
def email_sender(mock_env_vars) -> EmailNotificationSender:
    """Create an EmailNotificationSender instance with mocked env vars"""
    return EmailNotificationSender()


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
async def test_email_sender_initialization(mock_env_vars) -> None:
    """Test that EmailNotificationSender initializes with correct env vars"""
    sender = EmailNotificationSender()
    assert sender.sender_email == "test@gmail.com"
    assert sender.sender_password == "test-password"
    assert sender.smtp_server == "smtp.gmail.com"
    assert sender.smtp_port == 587


def test_email_sender_missing_env_vars() -> None:
    """Test that EmailNotificationSender raises error when env vars are missing"""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="GMAIL_SENDER_EMAIL and GMAIL_APP_PASSWORD"):
            EmailNotificationSender()


@pytest.mark.asyncio
async def test_notify_success(
    email_sender: EmailNotificationSender,
    notification_input: NotificationInput,
) -> None:
    """Test successful email sending"""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        result = await email_sender.notify(notification_input)

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@gmail.com", "test-password")
        mock_server.sendmail.assert_called_once()


@pytest.mark.asyncio
async def test_notify_failure(
    email_sender: EmailNotificationSender,
    notification_input: NotificationInput,
) -> None:
    """Test email sending failure"""
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = Exception("SMTP connection failed")

        result = await email_sender.notify(notification_input)

        assert result is False
