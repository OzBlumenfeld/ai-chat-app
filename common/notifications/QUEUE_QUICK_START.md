# Quick Start: Email Queue System

Get up and running with Celery-based email queuing in 5 minutes.

## Installation ✅ (Already Done)

```bash
# Dependencies already added:
# - celery>=5.6.2
# - redis>=7.2.0
```

## Setup Steps

### 1️⃣ Start Redis (Message Broker)

**Local development:**
```bash
redis-server
```

**Or with Docker:**
```bash
docker-compose up redis
```

### 2️⃣ Start Celery Worker (In a new terminal)

```bash
uv run celery -A common.celery_app worker --loglevel=info
```

Output should show:
```
 -------------- celery@hostname v5.6.2 (opalescence)
--- ***** -----
-- ******* ----
- *** --- * ---
- ** ---------- [config]
- ** ----------
- ** ----------
[Tasks]
  . common.notifications.tasks.send_email_task
```

### 3️⃣ Configure Gmail (Once)

Create/update `.env` file:
```bash
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

**How to get `GMAIL_APP_PASSWORD`:**
1. Enable 2-Factor Authentication on Gmail
2. Visit https://myaccount.google.com/apppasswords
3. Select "Mail" and "Windows Computer"
4. Copy the 16-character password

### 4️⃣ Start FastAPI (In another terminal)

```bash
uv run fastapi dev main.py
```

## Usage

### Option A: Direct Sending (Synchronous)
```python
from common.notifications.email_notification_sender import EmailNotificationSender
from common.notifications.notification_sender import NotificationInput

async def send_now():
    sender = EmailNotificationSender()
    notification = NotificationInput(
        sender_email="your-email@gmail.com",
        recipient_email="user@example.com",
        subject="Hello!",
        body="This email is sent immediately.",
    )
    success = await sender.notify(notification)
    return {"sent": success}
```

**Pros:** Simple, guaranteed immediate delivery
**Cons:** Blocks API request while sending

---

### Option B: Queued Sending (Asynchronous) ⭐
```python
from common.notifications.queued_email_notification_sender import QueuedEmailNotificationSender
from common.notifications.notification_sender import NotificationInput

async def queue_email():
    sender = QueuedEmailNotificationSender()
    notification = NotificationInput(
        sender_email="your-email@gmail.com",
        recipient_email="user@example.com",
        subject="Hello!",
        body="This email is queued for delivery.",
    )
    success = await sender.notify(notification)
    return {"queued": success}  # Returns immediately!
```

**Pros:** Non-blocking, scales to many workers
**Cons:** Needs Redis and Celery worker running

---

## How It Works

```
┌─────────────────┐
│  FastAPI Route  │
│   (API Server)  │
└────────┬────────┘
         │ Queue email
         ↓
┌─────────────────┐
│ Redis Broker    │
│ (Message Queue) │
└────────┬────────┘
         │ Dequeue when available
         ↓
┌─────────────────┐
│ Celery Worker   │ ← Can run on same machine or remote server
│ (Processor)     │ ← Can have multiple workers for parallelism
└────────┬────────┘
         │ Send via Gmail SMTP
         ↓
┌─────────────────┐
│  Gmail SMTP     │
│  (Actual Send)  │
└─────────────────┘
```

## Monitoring

### Check Queue Status
```bash
# See what tasks are pending
uv run celery -A common.celery_app inspect active

# See registered tasks
uv run celery -A common.celery_app inspect registered

# Real-time monitoring
uv run celery -A common.celery_app events
```

### Use Flower (Web UI)
```bash
uv add flower
uv run celery -A common.celery_app flower
# Open http://localhost:5555
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Start Redis: `redis-server` |
| No emails sending | Check if worker is running |
| Worker won't start | Verify `GMAIL_*` env vars are set |
| Task stuck in PENDING | Worker crashed, restart it |

## Scaling

### Add More Workers

Each worker processes tasks concurrently:

```bash
# Terminal 1: Worker on CPU core 0
uv run celery -A common.celery_app worker -c 4 -n worker1@%h

# Terminal 2: Worker on CPU core 1
uv run celery -A common.celery_app worker -c 4 -n worker2@%h
```

Both will automatically share the same Redis queue.

## Next: MCP Integration

When ready, create an MCP action:

```python
@mcp_tool
async def send_notification_email(recipient: str, subject: str, body: str):
    """Send an email asynchronously"""
    sender = QueuedEmailNotificationSender()
    notification = NotificationInput(
        sender_email=os.getenv("GMAIL_SENDER_EMAIL"),
        recipient_email=recipient,
        subject=subject,
        body=body,
    )
    success = await sender.notify(notification)
    return {"queued": success}
```

The AI model can now send emails without blocking!

---

**See [QUEUE_README.md](./QUEUE_README.md) for advanced configuration.**
