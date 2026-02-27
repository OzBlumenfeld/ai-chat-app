"""
Example script showing how to send emails using the Celery queue.

This demonstrates both:
1. Direct email sending (synchronous)
2. Queued email sending (asynchronous)

Run this script to see how the queue system works.
"""
import asyncio
import os

from common.notifications.email_notification_sender import EmailNotificationSender
from common.notifications.notification_sender import NotificationInput
from common.notifications.queued_email_notification_sender import (
    QueuedEmailNotificationSender,
)

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


async def example_direct_send() -> None:
    """Example: Direct email sending (blocks until email is sent)"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Direct Email Sending (Synchronous)")
    print("=" * 60)

    sender = EmailNotificationSender()

    notification = NotificationInput(
        sender_email=os.getenv("GMAIL_SENDER_EMAIL", "sender@gmail.com"),
        recipient_email="recipient@gmail.com",
        subject="Direct Send Test",
        body="This email was sent directly (synchronously).\n"
        "The FastAPI request blocks until the email is sent.",
    )

    print(f"\nSending email to: {notification.recipient_email}")
    success = await sender.notify(notification)
    print(f"Result: {'✓ Success' if success else '✗ Failed'}")


async def example_queued_send() -> None:
    """Example: Queued email sending (returns immediately)"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Queued Email Sending (Asynchronous)")
    print("=" * 60)

    sender = QueuedEmailNotificationSender()

    notification = NotificationInput(
        sender_email=os.getenv("GMAIL_SENDER_EMAIL", "sender@gmail.com"),
        recipient_email="recipient@gmail.com",
        subject="Queued Send Test",
        body="This email was queued for delivery.\n"
        "The FastAPI request returns immediately, and a Celery worker\n"
        "will process it when available.",
    )

    print(f"\nQueuing email to: {notification.recipient_email}")
    success = await sender.notify(notification)
    print(f"Result: {'✓ Queued' if success else '✗ Failed to queue'}")
    print("\nNOTE: Email is now in the queue. A Celery worker must be running")
    print("to actually send it. Start a worker with:")
    print("  uv run celery -A common.celery_app worker --loglevel=info")


async def example_multiple_emails() -> None:
    """Example: Queue multiple emails without blocking"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Queue Multiple Emails (Non-blocking)")
    print("=" * 60)

    sender = QueuedEmailNotificationSender()
    recipients = [
        "user1@example.com",
        "user2@example.com",
        "user3@example.com",
    ]

    print(f"\nQueuing {len(recipients)} emails...")
    for recipient in recipients:
        notification = NotificationInput(
            sender_email=os.getenv("GMAIL_SENDER_EMAIL", "sender@gmail.com"),
            recipient_email=recipient,
            subject=f"Hello {recipient}",
            body=f"This is a batch email test sent to {recipient}",
        )
        success = await sender.notify(notification)
        print(f"  {recipient}: {'✓ Queued' if success else '✗ Failed'}")

    print("\nAll emails queued successfully!")
    print("A Celery worker will process them concurrently.")


async def main() -> None:
    """Run all examples"""
    print("\n" + "🚀 " * 20)
    print("\nCelery Queue Examples for Email Notifications")
    print("\n" + "🚀 " * 20)

    # Check if Gmail credentials are set
    if not os.getenv("GMAIL_SENDER_EMAIL") or not os.getenv("GMAIL_APP_PASSWORD"):
        print("\n❌ ERROR: Gmail credentials not configured!")
        print("\nTo run these examples:")
        print("1. Enable 2FA on your Gmail account")
        print("2. Generate an App Password: https://myaccount.google.com/apppasswords")
        print("3. Set environment variables:")
        print("   GMAIL_SENDER_EMAIL=your-email@gmail.com")
        print("   GMAIL_APP_PASSWORD=your-app-specific-password")
        return

    # Run examples
    # Uncomment the one you want to try:

    # await example_direct_send()
    await example_queued_send()
    # await example_multiple_emails()

    print("\n" + "✨ " * 20 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
