import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import override

from .notification_sender import NotificationInput, NotificationSender

logger = logging.getLogger(__name__)


class EmailNotificationSender(NotificationSender):
    def __init__(self) -> None:
        self.smtp_server = os.getenv("GMAIL_SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("GMAIL_SMTP_PORT", "587"))
        self.sender_email = os.getenv("GMAIL_SENDER_EMAIL")
        self.sender_password = os.getenv("GMAIL_APP_PASSWORD")

        if not self.sender_email or not self.sender_password:
            raise ValueError("GMAIL_SENDER_EMAIL and GMAIL_APP_PASSWORD environment variables must be set")

    @override
    async def notify(self, notification_input: NotificationInput) -> bool:
        """Send email via Gmail SMTP"""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = notification_input.subject
            message["From"] = self.sender_email
            message["To"] = notification_input.recipient_email

            # Attach body
            part = MIMEText(notification_input.body, "plain")
            message.attach(part)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(
                    self.sender_email,
                    notification_input.recipient_email,
                    message.as_string(),
                )

            logger.info("Email sent successfully", extra={"recipient": notification_input.recipient_email})
            return True
        except Exception as e:
            logger.error("Failed to send email", extra={"recipient": notification_input.recipient_email, "error": str(e)})
            return False