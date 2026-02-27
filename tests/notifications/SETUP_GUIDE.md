# Email Integration Test Setup Guide

## TL;DR - 3 Steps to Run Tests

### Step 1: Get Gmail Credentials
```bash
# 1. Enable 2FA on Gmail: https://myaccount.google.com/security
# 2. Generate app password: https://myaccount.google.com/apppasswords
# 3. Copy the 16-character password
```

### Step 2: Set Environment Variables
```bash
export GMAIL_SENDER_EMAIL=your-email@gmail.com
export GMAIL_APP_PASSWORD=your-16-char-app-password
export TEST_RECIPIENT_EMAIL=recipient@example.com  # optional
```

### Step 3: Run Tests
```bash
# Unit tests (always work, no credentials needed)
uv run pytest tests/notifications/ -v

# Integration tests (actual email sending)
uv run pytest tests/notifications/test_email_integration.py -v --email-integration
```

---

## Detailed Setup

### Environment Variables Required

| Variable | Required | Format | Example |
|----------|----------|--------|---------|
| `GMAIL_SENDER_EMAIL` | ✅ Yes | Email address | `test-notifications@gmail.com` |
| `GMAIL_APP_PASSWORD` | ✅ Yes | 16 characters | `abcd efgh ijkl mnop` |
| `TEST_RECIPIENT_EMAIL` | ❌ Optional | Email address | `recipient@example.com` |

**Note:** If `TEST_RECIPIENT_EMAIL` is not set, emails will be sent to `GMAIL_SENDER_EMAIL`.

### Getting Gmail App Password

1. **Enable 2-Factor Authentication**
   - Go to: https://myaccount.google.com/security
   - Find "2-Step Verification"
   - Follow setup steps

2. **Generate App Password**
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer" (or your device)
   - Google will show a 16-character password
   - Copy it (including spaces)

3. **Example:**
   ```
   Google generates: abcd efgh ijkl mnop
   ```

### Where to Set Variables

#### Option A: Export in Terminal (Session Only)
```bash
export GMAIL_SENDER_EMAIL=your-email@gmail.com
export GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
export TEST_RECIPIENT_EMAIL=test@example.com

uv run pytest tests/notifications/ -v --email-integration
```

#### Option B: .env File (Persistent)
Create `.env` in project root:
```bash
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
TEST_RECIPIENT_EMAIL=test@example.com
```

Then tests will automatically load these variables.

#### Option C: Use a Script (Recommended for CI)
Create `run-email-tests.sh`:
```bash
#!/bin/bash
export GMAIL_SENDER_EMAIL=your-email@gmail.com
export GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
export TEST_RECIPIENT_EMAIL=test@example.com

uv run pytest tests/notifications/test_email_integration.py -v --email-integration
```

---

## Test Commands

### View All Available Tests
```bash
uv run pytest tests/notifications/ --collect-only
```

Output:
```
test_email_notification_sender.py
  test_email_sender_initialization
  test_email_sender_missing_env_vars
  test_notify_success
  test_notify_failure

test_queued_email_notification_sender.py
  test_queued_sender_enqueues_task
  test_queued_sender_handles_enqueue_failure

test_tasks.py
  test_send_email_task_success
  test_send_email_task_creates_notification

test_email_integration.py  (requires --email-integration)
  test_send_simple_email
  test_send_email_with_formatting
  test_send_multiple_emails
  test_email_with_special_characters
  test_email_credentials_validation
  test_send_email_from_different_sender
```

### Run Unit Tests Only
```bash
# All unit tests (mocked, no credentials needed)
uv run pytest tests/notifications/ -v

# Specific unit test file
uv run pytest tests/notifications/test_email_notification_sender.py -v
```

### Run Integration Tests (With Email Sending)
```bash
# All integration tests
uv run pytest tests/notifications/test_email_integration.py -v --email-integration

# Specific integration test
uv run pytest tests/notifications/test_email_integration.py::test_send_simple_email -v --email-integration

# With output
uv run pytest tests/notifications/test_email_integration.py -v -s --email-integration
```

### Run Everything
```bash
uv run pytest tests/notifications/ -v --email-integration
```

---

## Expected Output

### Unit Tests (No Credentials)
```bash
$ uv run pytest tests/notifications/ -v

tests/notifications/test_email_notification_sender.py::test_email_sender_initialization PASSED
tests/notifications/test_email_notification_sender.py::test_email_sender_missing_env_vars PASSED
tests/notifications/test_email_notification_sender.py::test_notify_success PASSED
tests/notifications/test_email_notification_sender.py::test_notify_failure PASSED
tests/notifications/test_queued_email_notification_sender.py::test_queued_sender_enqueues_task PASSED
tests/notifications/test_queued_email_notification_sender.py::test_queued_sender_handles_enqueue_failure PASSED
tests/notifications/test_tasks.py::test_send_email_task_success PASSED
tests/notifications/test_tasks.py::test_send_email_task_creates_notification PASSED
tests/notifications/test_email_integration.py::test_send_simple_email SKIPPED
tests/notifications/test_email_integration.py::test_send_email_with_formatting SKIPPED
tests/notifications/test_email_integration.py::test_send_multiple_emails SKIPPED
tests/notifications/test_email_integration.py::test_email_with_special_characters SKIPPED
tests/notifications/test_email_integration.py::test_email_credentials_validation SKIPPED
tests/notifications/test_email_integration.py::test_send_email_from_different_sender SKIPPED

====== 8 passed, 6 skipped in 0.12s ======
```

### Integration Tests (With Credentials)
```bash
$ GMAIL_SENDER_EMAIL=test@gmail.com GMAIL_APP_PASSWORD=abcd... uv run pytest tests/notifications/test_email_integration.py -v --email-integration

tests/notifications/test_email_integration.py::test_send_simple_email PASSED
tests/notifications/test_email_integration.py::test_send_email_with_formatting PASSED
tests/notifications/test_email_integration.py::test_send_multiple_emails PASSED
tests/notifications/test_email_integration.py::test_email_with_special_characters PASSED
tests/notifications/test_email_integration.py::test_email_credentials_validation PASSED
tests/notifications/test_email_integration.py::test_send_email_from_different_sender PASSED

====== 6 passed in 8.45s ======
```

---

## What Each Test Does

### Unit Tests (Mocked - Safe)
- ✅ No real emails sent
- ✅ No credentials needed
- ✅ Test logic and error handling
- ✅ Fast (~100ms)

### Integration Tests (Real Email)
- ✅ Actual Gmail SMTP connection
- ✅ Real emails sent to inbox
- ✅ Verifies complete pipeline
- ✅ Slower (~8-15 seconds)

| Test | What It Tests | Result |
|------|---------------|--------|
| `test_send_simple_email` | Basic email sending | Real email received |
| `test_send_email_with_formatting` | Multi-line body with formatting | Real email received |
| `test_send_multiple_emails` | Sequential sends work | Multiple real emails |
| `test_email_with_special_characters` | Unicode/emojis/symbols | Email with correct encoding |
| `test_email_credentials_validation` | Credentials loaded from env | Validates SMTP settings |
| `test_send_email_from_different_sender` | Gmail's "from" override | Shows Gmail behavior |

---

## Troubleshooting

### "Email integration tests disabled"
```
SKIPPED [Email integration tests disabled. Use --email-integration to enable.]
```

**Solution:** Add `--email-integration` flag
```bash
uv run pytest tests/notifications/test_email_integration.py -v --email-integration
```

### "Gmail credentials not configured"
```
SKIPPED [Gmail credentials not configured. Set GMAIL_SENDER_EMAIL and GMAIL_APP_PASSWORD]
```

**Solution:** Set environment variables
```bash
export GMAIL_SENDER_EMAIL=your-email@gmail.com
export GMAIL_APP_PASSWORD=your-16-char-app-password
uv run pytest tests/notifications/test_email_integration.py -v --email-integration
```

### "Invalid credentials" or "Authentication failed"
```
FAILED [Errno 535] Username and password not accepted
```

**Causes & Solutions:**
1. ❌ Wrong app password
   - Regenerate at https://myaccount.google.com/apppasswords
2. ❌ 2FA not enabled
   - Enable at https://myaccount.google.com/security
3. ❌ Spaces in password
   - Copy exactly as shown: `abcd efgh ijkl mnop`
4. ❌ Old password
   - Google app passwords can expire, regenerate

### "Connection timeout"
```
FAILED Connection timed out
```

**Causes & Solutions:**
1. Internet connection down
2. Gmail SMTP blocked (port 587)
   - Check firewall/antivirus
   - Try: `telnet smtp.gmail.com 587`
3. Gmail account restricted
   - Sign in at myaccount.google.com to verify

### Emails not arriving
```
Test passes but email not in inbox
```

**Solutions:**
1. Check spam/junk folder
2. Verify correct recipient email
3. Wait a few seconds (sometimes delayed)
4. Check if TEST_RECIPIENT_EMAIL is set correctly

---

## Tips & Best Practices

### 1. Use a Dedicated Test Gmail Account
```bash
# Create a new Gmail account just for testing
test-notifications@gmail.com

# Keep your personal account for other uses
```

### 2. Don't Hardcode Credentials
```bash
# ✗ BAD - Don't do this
GMAIL_SENDER_EMAIL = "your@gmail.com"  # In code
GMAIL_APP_PASSWORD = "secret"          # In code

# ✓ GOOD - Use environment variables
export GMAIL_SENDER_EMAIL="your@gmail.com"
export GMAIL_APP_PASSWORD="secret"
```

### 3. Don't Commit .env File
```bash
# Add to .gitignore
echo ".env" >> .gitignore
echo ".env.local" >> .gitignore

# Keep .env.example with placeholders
```

### 4. Rate Limiting
- Gmail allows ~30 emails per second
- Tests send slowly (1-2 per second)
- Safe to run frequently

### 5. Monitor Test Emails
- Delete old test emails periodically
- Set up filter to auto-archive
- Consider reading your inbox after tests

---

## Full Example Workflow

```bash
# 1. Generate Gmail app password
# Go to: https://myaccount.google.com/apppasswords
# Get: abcd efgh ijkl mnop

# 2. Create .env file
cat > .env << EOF
GMAIL_SENDER_EMAIL=test-notifications@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
TEST_RECIPIENT_EMAIL=yourname@example.com
EOF

# 3. Run unit tests (always work)
uv run pytest tests/notifications/ -v
# ====== 8 passed, 6 skipped ======

# 4. Run integration tests (send real emails)
uv run pytest tests/notifications/test_email_integration.py -v --email-integration
# ====== 6 passed ======

# 5. Check your inbox - 6 test emails should arrive!
```

---

## Next Steps

After confirming email sending works:

1. **Test Celery Queue**: See [../QUEUE_README.md](../QUEUE_README.md)
2. **Run Worker**: See [../QUEUE_QUICK_START.md](../QUEUE_QUICK_START.md)
3. **Create MCP Action**: Ready to integrate with your model!

---

**See Also:**
- [RUN_TESTS.md](./RUN_TESTS.md) - Test command reference
- [EMAIL_INTEGRATION_TEST.md](./EMAIL_INTEGRATION_TEST.md) - Detailed test documentation
