# Email Notifications

## Setup

To use the email notification system with Gmail:

### 1. Gmail Configuration
- Enable 2-Factor Authentication on your Gmail account
- Generate an App Password at https://myaccount.google.com/apppasswords
- Add to your `.env` file:
  ```
  GMAIL_SENDER_EMAIL=your-email@gmail.com
  GMAIL_APP_PASSWORD=your-app-specific-password
  ```

### 2. Usage Example

```python
from common.notifications.email_notification_sender import EmailNotificationSender
from common.notifications.notification_sender import NotificationInput

# Initialize the sender
sender = EmailNotificationSender()

# Create a notification
notification = NotificationInput(
    sender_email="your-email@gmail.com",
    recipient_email="recipient@gmail.com",
    subject="Hello!",
    body="This is a test email.",
)

# Send the email
success = await sender.notify(notification)
if success:
    print("Email sent successfully!")
else:
    print("Failed to send email")
```

### 3. Integration with FastAPI

For use as an MCP action or FastAPI endpoint:

```python
from fastapi import Depends
from common.notifications.email_notification_sender import EmailNotificationSender
from common.notifications.notification_sender import NotificationInput

async def send_email(
    notification: NotificationInput,
    sender: EmailNotificationSender = Depends(lambda: EmailNotificationSender()),
) -> dict:
    success = await sender.notify(notification)
    return {"success": success}
```

## Notes

- All methods are async for proper integration with FastAPI
- The sender validates that required environment variables are set on initialization
- SMTP errors are caught and logged, returning `False` on failure
