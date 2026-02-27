# Email Queue System (Celery)

This directory contains a production-ready email queue system using Celery for asynchronous email delivery.

## Architecture

### Components

1. **Broker (Redis)**: Message queue that stores tasks temporarily
   - Runs on `redis://localhost:6379/0` by default
   - Fast, in-memory data store
   - Auto-discovery of new tasks

2. **Result Backend (Redis)**: Stores task execution results
   - Runs on `redis://localhost:6379/1` by default
   - Optional but useful for tracking task status

3. **Workers**: Processes that execute tasks
   - Can run on same machine or distributed across servers
   - Auto-retries on failure with exponential backoff
   - Multiple workers can process tasks concurrently

### Flow

```
FastAPI Endpoint
    ↓
NotificationInput
    ↓
QueuedEmailNotificationSender.notify()
    ↓
send_email_task.delay() [Enqueue]
    ↓
Redis Broker
    ↓
Celery Worker [Dequeue & Process]
    ↓
EmailNotificationSender.notify() [Send Email]
    ↓
Result Backend [Store Result]
```

## Setup

### 1. Local Development

**Start Redis locally:**
```bash
redis-server
```

**In a separate terminal, start a Celery worker:**
```bash
uv run celery -A common.celery_app worker --loglevel=info
```

**In another terminal, start FastAPI:**
```bash
uv run fastapi dev main.py
```

### 2. Docker Compose

All services are configured in `docker-compose.yml`:

```bash
# Start all services (Redis, PostgreSQL, Ollama, etc.)
docker-compose up --build

# In another terminal, start worker(s)
docker-compose exec web uv run celery -A common.celery_app worker --loglevel=info
```

## Usage

### Example 1: Queue an Email Task

```python
from common.notifications.notification_sender import NotificationInput
from common.notifications.queued_email_notification_sender import QueuedEmailNotificationSender

async def send_notification():
    sender = QueuedEmailNotificationSender()

    notification = NotificationInput(
        sender_email="your-email@gmail.com",
        recipient_email="user@example.com",
        subject="Welcome!",
        body="Thanks for signing up.",
    )

    # Returns immediately - task is queued
    success = await sender.notify(notification)
    print(f"Task queued: {success}")
```

### Example 2: FastAPI Endpoint

```python
from fastapi import FastAPI
from common.notifications.notification_sender import NotificationInput
from common.notifications.queued_email_notification_sender import QueuedEmailNotificationSender

app = FastAPI()

@app.post("/send-email")
async def send_email(notification: NotificationInput) -> dict:
    sender = QueuedEmailNotificationSender()
    success = await sender.notify(notification)
    return {"queued": success}
```

## Configuration

### Environment Variables

```bash
# Redis Broker
CELERY_BROKER_URL=redis://localhost:6379/0

# Redis Result Backend
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Gmail SMTP
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-specific-password
```

### Celery Options

Edit `common/celery_app.py` to customize:

- **`task_time_limit`**: Hard timeout (30 min default)
- **`task_soft_time_limit`**: Soft timeout before hard limit (25 min default)
- **`max_retries`**: Number of retry attempts (3 default in `tasks.py`)
- **`task_serializer`**: JSON, pickle, etc.

## Task States

Each queued task goes through these states:

- **PENDING**: Waiting in queue
- **STARTED**: Worker picked it up
- **SUCCESS**: Completed successfully
- **FAILURE**: Failed (will retry if < max_retries)
- **RETRY**: Retrying after failure
- **REVOKED**: Task was cancelled

## Monitoring

### Check Queue Status

```bash
# List pending tasks
uv run celery -A common.celery_app inspect active

# Check registered tasks
uv run celery -A common.celery_app inspect registered

# Monitor in real-time
uv run celery -A common.celery_app events
```

### Use Flower (Celery Web UI)

```bash
# Install
uv add flower

# Start (opens http://localhost:5555)
uv run celery -A common.celery_app flower
```

## Troubleshooting

### Queue is not processing tasks

1. Check if Redis is running: `redis-cli ping` → `PONG`
2. Check if worker is running: `ps aux | grep celery`
3. Check logs: Look for error messages in worker terminal

### Task stuck in PENDING

- Worker may have crashed
- Redis connection dropped
- Restart worker: `uv run celery -A common.celery_app worker --loglevel=info`

### Emails not being sent

1. Check task result: Use Flower to see detailed error
2. Verify Gmail credentials in `.env`
3. Check if worker has network access to Gmail SMTP

## Production Considerations

### Use RabbitMQ for Broker (Optional)

Redis works great for small/medium loads. For higher throughput, use RabbitMQ:

```bash
uv add kombu  # Already added with Celery
```

Update `.env`:
```
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### Multiple Workers

Run workers on different servers to scale:

```bash
# Server 1
uv run celery -A common.celery_app worker --loglevel=info --concurrency=4

# Server 2
uv run celery -A common.celery_app worker --loglevel=info --concurrency=4
```

All workers will share the same queue from Redis.

### Beat Scheduler (Optional)

For periodic tasks (e.g., send daily digest):

```python
from celery.schedules import crontab
from common.celery_app import app

app.conf.beat_schedule = {
    'send-daily-digest': {
        'task': 'common.notifications.tasks.send_email_task',
        'schedule': crontab(hour=9, minute=0),  # 9 AM daily
        'args': (...),
    },
}
```

Then run: `uv run celery -A common.celery_app beat`

## Next Steps: MCP Integration

When ready to integrate with MCP:

1. Create an MCP action that calls `QueuedEmailNotificationSender`
2. The action will return immediately (task is queued)
3. Model can request task status if needed (optional)
