# Running Email Notification Tests

## Quick Reference

### Unit Tests (Mocked - No Credentials Needed)
```bash
# All notification tests
uv run pytest tests/notifications/ -v

# Just unit tests (exclude integration tests)
uv run pytest tests/notifications/test_email_notification_sender.py -v
uv run pytest tests/notifications/test_queued_email_notification_sender.py -v
uv run pytest tests/notifications/test_tasks.py -v
```

**Result:** All 8 tests should pass ✅

---

## Integration Tests (Real Email Sending - Credentials Required)

### Prerequisites

1. **Get Gmail Credentials**
   ```bash
   # 1. Enable 2FA: https://myaccount.google.com/security
   # 2. Generate app password: https://myaccount.google.com/apppasswords
   # 3. Copy the 16-character password
   ```

2. **Set Environment Variables**
   ```bash
   export GMAIL_SENDER_EMAIL=your-email@gmail.com
   export GMAIL_APP_PASSWORD=your-16-char-app-password
   export TEST_RECIPIENT_EMAIL=recipient@example.com  # optional
   ```

### Run Integration Tests

```bash
# Run all 6 integration tests
uv run pytest tests/notifications/test_email_integration.py -v --email-integration

# Run a specific integration test
uv run pytest tests/notifications/test_email_integration.py::test_send_simple_email -v --email-integration

# Run WITHOUT the --email-integration flag (they will be skipped)
uv run pytest tests/notifications/test_email_integration.py -v
# ^ This will skip all integration tests - safe to run without credentials
```

---

## Full Test Suite

### Run Everything
```bash
# All tests (mocked unit tests + skipped integration tests)
uv run pytest tests/notifications/ -v

# Run with integration tests enabled
GMAIL_SENDER_EMAIL=your@gmail.com \
GMAIL_APP_PASSWORD=your-app-password \
uv run pytest tests/notifications/ -v --email-integration
```

### Expected Output (Unit Tests Only)
```
tests/notifications/test_email_notification_sender.py::test_email_sender_initialization PASSED
tests/notifications/test_email_notification_sender.py::test_email_sender_missing_env_vars PASSED
tests/notifications/test_email_notification_sender.py::test_notify_success PASSED
tests/notifications/test_email_notification_sender.py::test_notify_failure PASSED
tests/notifications/test_queued_email_notification_sender.py::test_queued_sender_enqueues_task PASSED
tests/notifications/test_queued_email_notification_sender.py::test_queued_sender_handles_enqueue_failure PASSED
tests/notifications/test_tasks.py::test_send_email_task_success PASSED
tests/notifications/test_tasks.py::test_send_email_task_creates_notification PASSED
tests/notifications/test_email_integration.py::test_send_simple_email SKIPPED (email integration disabled)
tests/notifications/test_email_integration.py::test_send_email_with_formatting SKIPPED (email integration disabled)
tests/notifications/test_email_integration.py::test_send_multiple_emails SKIPPED (email integration disabled)
tests/notifications/test_email_integration.py::test_email_with_special_characters SKIPPED (email integration disabled)
tests/notifications/test_email_integration.py::test_email_credentials_validation SKIPPED (email integration disabled)
tests/notifications/test_email_integration.py::test_send_email_from_different_sender SKIPPED (email integration disabled)

====== 8 passed, 6 skipped in 0.45s ======
```

---

## Test Categories

| Test File | Type | Mocked | Needs Credentials | Tests |
|-----------|------|--------|------------------|-------|
| `test_email_notification_sender.py` | Unit | ✅ Yes | ❌ No | Direct SMTP sending |
| `test_queued_email_notification_sender.py` | Unit | ✅ Yes | ❌ No | Celery queuing |
| `test_tasks.py` | Unit | ✅ Yes | ❌ No | Task creation |
| `test_email_integration.py` | Integration | ❌ No | ✅ Yes | Real Gmail sending |

---

## Environment Variable Guide

```bash
# Required for integration tests
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop  # 16-char app password

# Optional (defaults to GMAIL_SENDER_EMAIL if not set)
TEST_RECIPIENT_EMAIL=test@example.com
```

### Store in `.env`
```bash
# Create or edit .env file
cat > .env << EOF
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-char-app-password
TEST_RECIPIENT_EMAIL=test@example.com
EOF

# Then run tests (they'll load from .env automatically)
uv run pytest tests/notifications/test_email_integration.py -v --email-integration
```

---

## Example: Complete Test Run

```bash
# 1. Get your Gmail credentials
# Go to: https://myaccount.google.com/apppasswords

# 2. Set environment
export GMAIL_SENDER_EMAIL=test-notifications@gmail.com
export GMAIL_APP_PASSWORD="abcd efgh ijkl mnop"

# 3. Run all unit tests (no credentials needed)
uv run pytest tests/notifications/ -v

# Output:
# ====== 8 passed, 6 skipped in 0.45s ======

# 4. Now enable integration tests
uv run pytest tests/notifications/test_email_integration.py -v --email-integration

# Output:
# test_send_simple_email PASSED
# test_send_email_with_formatting PASSED
# test_send_multiple_emails PASSED
# test_email_with_special_characters PASSED
# test_email_credentials_validation PASSED
# test_send_email_from_different_sender PASSED
#
# ====== 6 passed in 8.23s ======
```

---

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Test Emails

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: uv sync

      - name: Run unit tests
        run: uv run pytest tests/notifications/ -v

      - name: Run integration tests
        if: secrets.GMAIL_SENDER_EMAIL != ''
        env:
          GMAIL_SENDER_EMAIL: ${{ secrets.GMAIL_SENDER_EMAIL }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
        run: uv run pytest tests/notifications/test_email_integration.py -v --email-integration
```

---

## Troubleshooting

### Tests Pass but No Emails Arrive
- Check spam/junk folder
- Verify TEST_RECIPIENT_EMAIL is correct
- Gmail app password has expiration (regenerate if old)

### "Gmail credentials not configured"
```bash
# Check if variables are set
echo $GMAIL_SENDER_EMAIL
echo $GMAIL_APP_PASSWORD

# Set them
export GMAIL_SENDER_EMAIL=your@gmail.com
export GMAIL_APP_PASSWORD=xxxx
```

### "Email integration tests disabled"
```bash
# You forgot the --email-integration flag
uv run pytest tests/notifications/test_email_integration.py -v --email-integration
#                                                            ^^^^^^^^^^^^^^^^^^^^^^
```

---

## Documentation

- **Integration Test Details:** See [EMAIL_INTEGRATION_TEST.md](./EMAIL_INTEGRATION_TEST.md)
- **Email Queue System:** See [../QUEUE_README.md](../QUEUE_README.md)
- **Quick Setup:** See [../QUEUE_QUICK_START.md](../QUEUE_QUICK_START.md)
