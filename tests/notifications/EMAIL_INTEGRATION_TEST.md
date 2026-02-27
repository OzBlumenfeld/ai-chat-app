# Email Integration Tests

This guide explains how to run real email sending tests that actually connect to Gmail SMTP.

## What These Tests Do

These are **integration tests** that:
- ✅ Connect to actual Gmail SMTP servers
- ✅ Send real emails to real addresses
- ✅ Verify the complete email delivery pipeline works
- ✅ Test various email formats and edge cases

**They are NOT mocked** - emails will actually be sent!

## Environment Variables Required

### Required
```bash
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-16-character-app-password
```

### Optional
```bash
TEST_RECIPIENT_EMAIL=where-to-send-test-emails@example.com
# Defaults to GMAIL_SENDER_EMAIL if not specified
```

## Getting Gmail Credentials

### Step 1: Enable 2-Factor Authentication
1. Go to https://myaccount.google.com/security
2. Scroll to "2-Step Verification"
3. Follow the setup process

### Step 2: Generate App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select device: "Windows Computer" (or your device)
3. Select app: "Mail"
4. Google will show a 16-character password
5. Copy it (spaces will be removed automatically)

### Example `.env` for Testing
```bash
# Your Gmail account
GMAIL_SENDER_EMAIL=yourname@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop

# Optional: Send test emails to someone else
TEST_RECIPIENT_EMAIL=friend@example.com
```

## Running the Tests

### Run All Integration Tests
```bash
uv run pytest tests/notifications/test_email_integration.py -v --email-integration
```

### Run a Specific Test
```bash
uv run pytest tests/notifications/test_email_integration.py::test_send_simple_email -v --email-integration
```

### Run Without Integration Tests (Default)
```bash
# This will skip email integration tests
uv run pytest tests/notifications/test_email_integration.py -v
```

## Available Tests

### 1. `test_send_simple_email`
Sends a basic plain text email. The most fundamental test.

```
✓ Connects to Gmail SMTP
✓ Authenticates with credentials
✓ Sends simple email
✓ Verifies successful delivery
```

### 2. `test_send_email_with_formatting`
Tests multi-line emails with structured formatting.

```
✓ Multi-line body support
✓ Maintains formatting/line breaks
✓ Special newlines handled correctly
```

### 3. `test_send_multiple_emails`
Sends multiple emails in sequence to verify reliability.

```
✓ Multiple consecutive sends work
✓ No connection pooling issues
✓ Rate limiting not hit
```

### 4. `test_email_with_special_characters`
Tests emails with Unicode, emojis, and special characters.

```
✓ Unicode characters (中文, Кириллица, العربية)
✓ Emojis (🚀 🌍 ✅)
✓ Special symbols (© ® ™ € £)
```

### 5. `test_email_credentials_validation`
Verifies credentials are loaded correctly on initialization.

```
✓ EmailNotificationSender initializes with env vars
✓ SMTP server and port are correct
```

### 6. `test_send_email_from_different_sender`
Tests Gmail's "from address" handling.

```
✓ Demonstrates Gmail override behavior
✓ Shows how Gmail security works with app passwords
```

## Understanding Test Output

### Successful Test
```
test_send_simple_email PASSED [100%]
```

### Skipped (No Credentials)
```
test_send_simple_email SKIPPED [email integration disabled]
```

### Skipped (Missing --email-integration Flag)
```
test_send_simple_email SKIPPED [Email integration tests disabled. Use --email-integration to enable.]
```

## Troubleshooting

### "Gmail credentials not configured"
```
✗ Error: Set GMAIL_SENDER_EMAIL and GMAIL_APP_PASSWORD
```

**Solution:**
```bash
export GMAIL_SENDER_EMAIL=your-email@gmail.com
export GMAIL_APP_PASSWORD=your-app-password
```

Or add to `.env`:
```
GMAIL_SENDER_EMAIL=your-email@gmail.com
GMAIL_APP_PASSWORD=your-app-password
```

### "Connection refused" or "timeout"
```
✗ Error: Failed to send email: Connection timed out
```

**Solutions:**
1. Check internet connection
2. Verify Gmail SMTP is accessible: `telnet smtp.gmail.com 587`
3. Check firewall/antivirus blocking port 587
4. Ensure credentials are correct

### "Invalid credentials" or "Authentication failed"
```
✗ Error: Failed to send email: [Errno 535] b'5.7.8 Username and password not accepted.'
```

**Solutions:**
1. Verify app password is correct (16 chars, no spaces)
2. Ensure 2FA is enabled on Gmail account
3. Regenerate app password at https://myaccount.google.com/apppasswords
4. Use a fresh app password (old ones might expire)

### "Invalid recipient address"
```
✗ Error: Failed to send email: The email address is not valid.
```

**Solution:**
- Verify TEST_RECIPIENT_EMAIL is a valid email format
- Use a real email address that can receive emails

## CI/CD Considerations

### In GitHub Actions / GitLab CI / etc.

**Store credentials as secrets:**
```yaml
# GitHub Actions example
env:
  GMAIL_SENDER_EMAIL: ${{ secrets.GMAIL_SENDER_EMAIL }}
  GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
```

**Run integration tests conditionally:**
```bash
# Only run if secrets are available
if [ -n "$GMAIL_SENDER_EMAIL" ]; then
  uv run pytest tests/notifications/test_email_integration.py -v --email-integration
else
  echo "Skipping email integration tests (no credentials in CI)"
fi
```

## Best Practices

### 1. Use a Dedicated Test Account
Don't use your personal Gmail account. Create a dedicated test account:
```
test-notifications@gmail.com
```

### 2. Monitor Test Emails
The test emails are real and will appear in the inbox. You might want to:
- Set up a filter to auto-archive test emails
- Use a separate Gmail account just for testing
- Delete test emails periodically

### 3. Don't Run Too Frequently
Gmail has rate limits. Don't run tests hundreds of times per day.

**Recommended:**
- Run during development as needed
- Run in CI/CD once per commit
- Run full suite once per day

### 4. Keep Credentials Secure
```bash
# ✓ Good: Use environment variables
export GMAIL_APP_PASSWORD="secret"
uv run pytest ... --email-integration

# ✗ Bad: Hardcode in test files
GMAIL_APP_PASSWORD = "secret"  # DON'T DO THIS!

# ✗ Bad: Commit to git
# Commit .env file with secrets  # DON'T DO THIS!
```

## Example: Full Integration Test Run

```bash
# 1. Set up environment
export GMAIL_SENDER_EMAIL=test-notifications@gmail.com
export GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
export TEST_RECIPIENT_EMAIL=me@example.com

# 2. Run all integration tests
uv run pytest tests/notifications/test_email_integration.py -v --email-integration

# Output:
# test_send_simple_email PASSED
# test_send_email_with_formatting PASSED
# test_send_multiple_emails PASSED
# test_email_with_special_characters PASSED
# test_email_credentials_validation PASSED
# test_send_email_from_different_sender PASSED
# ====== 6 passed in 15.23s ======
```

## Next Steps

After verifying email sending works:

1. **Test with Celery Queue**: Run the queued email tests
   ```bash
   uv run pytest tests/notifications/test_queued_email_notification_sender.py -v
   ```

2. **Test Full Flow**: Start a worker and send real queued emails
   ```bash
   # Terminal 1
   redis-server

   # Terminal 2
   uv run celery -A common.celery_app worker --loglevel=info

   # Terminal 3
   uv run python scripts/example_send_email_queue.py
   ```

3. **Integrate into FastAPI**: Create an endpoint and test end-to-end
   ```python
   @app.post("/send-email")
   async def send_email(notification: NotificationInput):
       sender = QueuedEmailNotificationSender()
       success = await sender.notify(notification)
       return {"queued": success}
   ```
