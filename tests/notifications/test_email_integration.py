"""
Integration tests for actual email sending via Gmail SMTP.

These tests require real Gmail credentials and will send actual emails.
Run with: uv run pytest tests/notifications/test_email_integration.py -v --email-integration

Environment variables required:
- GMAIL_SENDER_EMAIL: Your Gmail address
- GMAIL_APP_PASSWORD: Your Gmail app-specific password (16 chars)
- TEST_RECIPIENT_EMAIL: Email to send test messages to (optional, defaults to sender)
"""
import os

import pytest

from common.notifications.email_notification_sender import EmailNotificationSender
from common.notifications.notification_sender import NotificationInput


@pytest.fixture
def gmail_credentials() -> dict[str, str]:
    """Get Gmail credentials from environment variables"""
    sender_email = os.getenv("GMAIL_SENDER_EMAIL")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    recipient_email = os.getenv("TEST_RECIPIENT_EMAIL", sender_email)

    if not sender_email or not app_password:
        pytest.skip(
            "Gmail credentials not configured. Set GMAIL_SENDER_EMAIL and GMAIL_APP_PASSWORD"
        )

    return {
        "sender_email": sender_email,
        "app_password": app_password,
        "recipient_email": recipient_email,
    }


@pytest.mark.email_integration
@pytest.mark.asyncio
async def test_send_simple_email(email_integration, gmail_credentials) -> None:
    """Test sending a simple email via Gmail SMTP"""
    sender = EmailNotificationSender()

    notification = NotificationInput(
        sender_email=gmail_credentials["sender_email"],
        recipient_email=gmail_credentials["recipient_email"],
        subject="Test Email - Simple",
        body="This is a simple test email from the integration test suite.",
    )

    result = await sender.notify(notification)

    assert result is True, "Email should be sent successfully"


@pytest.mark.email_integration
@pytest.mark.asyncio
async def test_send_email_with_formatting(email_integration, gmail_credentials) -> None:
    """Test sending an email with rich formatting"""
    sender = EmailNotificationSender()

    body = """Hello!

This is a test email with multiple lines.

Key Information:
- Test 1: Successful
- Test 2: Verified
- Test 3: Complete

Best regards,
Test Suite"""

    notification = NotificationInput(
        sender_email=gmail_credentials["sender_email"],
        recipient_email=gmail_credentials["recipient_email"],
        subject="Test Email - Formatted",
        body=body,
    )

    result = await sender.notify(notification)

    assert result is True, "Formatted email should be sent successfully"


@pytest.mark.email_integration
@pytest.mark.asyncio
async def test_send_multiple_emails(email_integration, gmail_credentials) -> None:
    """Test sending multiple emails sequentially"""
    sender = EmailNotificationSender()

    recipients = [gmail_credentials["recipient_email"]]
    # You can add more test recipients here if you want
    # recipients = ["test1@example.com", "test2@example.com"]

    for i, recipient in enumerate(recipients, 1):
        notification = NotificationInput(
            sender_email=gmail_credentials["sender_email"],
            recipient_email=recipient,
            subject=f"Test Email #{i}",
            body=f"This is test email number {i} from the integration test suite.",
        )

        result = await sender.notify(notification)
        assert result is True, f"Email {i} should be sent successfully"


@pytest.mark.email_integration
@pytest.mark.asyncio
async def test_email_with_special_characters(email_integration, gmail_credentials) -> None:
    """Test sending emails with special characters and unicode"""
    sender = EmailNotificationSender()

    notification = NotificationInput(
        sender_email=gmail_credentials["sender_email"],
        recipient_email=gmail_credentials["recipient_email"],
        subject="Test Email - Special Characters & Unicode 🚀",
        body="""Testing special characters and unicode:

Special: !@#$%^&*()_+-=[]{}|;:',.<>?/
Unicode: 你好世界 🌍 Привет мир ¡Hola mundo!
Symbols: © ® ™ € £ ¥

All should display correctly in the recipient's email client.""",
    )

    result = await sender.notify(notification)

    assert result is True, "Email with special characters should be sent successfully"


@pytest.mark.email_integration
@pytest.mark.asyncio
async def test_email_credentials_validation(email_integration, gmail_credentials) -> None:
    """Test that EmailNotificationSender validates credentials on init"""
    # This should succeed with valid credentials
    sender = EmailNotificationSender()

    assert sender.sender_email == gmail_credentials["sender_email"]
    assert sender.smtp_server == "smtp.gmail.com"
    assert sender.smtp_port == 587


@pytest.mark.email_integration
@pytest.mark.asyncio
async def test_send_email_from_different_sender(email_integration, gmail_credentials) -> None:
    """
    Test that emails are sent FROM the configured Gmail address,
    regardless of what sender_email is specified in NotificationInput
    (This is a Gmail security feature)
    """
    sender = EmailNotificationSender()

    # Try to specify a different "from" address
    # Gmail will override this and send from the configured account
    notification = NotificationInput(
        sender_email="someone-else@example.com",  # This will be overridden
        recipient_email=gmail_credentials["recipient_email"],
        subject="Test Email - From Address",
        body="This email demonstrates Gmail's 'from' address handling.",
    )

    result = await sender.notify(notification)

    assert result is True
    # Note: The email will actually be sent FROM the configured Gmail address,
    # even though we specified a different one above.
    # This is expected Gmail behavior for app passwords.
