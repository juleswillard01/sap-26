# Integration Guide: 2FA Automation in Indy Adapter

## Overview

The `Indy2FAAdapter` is now production-ready and can be integrated into the main Indy workflow. It handles automated 2FA verification during login without manual intervention.

## Where to Integrate

### Current Architecture
```
InidyAdapter (src/adapters/indy_adapter.py)
├── Login flow (Playwright or Nodriver)
├── 2FA detection (NEW: Indy2FAAdapter)
├── Transaction export
└── CSV parsing
```

### Integration Points

#### 1. CLI Command
File: `src/cli.py`

```python
@cli.command()
@click.option("--2fa", is_flag=True, help="Handle 2FA during login")
def sync(2fa: bool) -> None:
    """Sync Indy transactions with 2FA support."""
    indy = IndyAdapter(settings)
    if 2fa:
        gmail = GmailReader(settings)
        gmail.connect()
        success = indy.login_with_2fa(gmail)
        gmail.close()
    else:
        success = indy.login()

    if success:
        transactions = indy.export_transactions()
        # ... rest of sync logic
```

#### 2. IndyAdapter Method
File: `src/adapters/indy_adapter.py`

```python
from src.adapters.indy_2fa_adapter import Indy2FAAdapter
from src.adapters.gmail_reader import GmailReader

class IndyAdapter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._2fa = Indy2FAAdapter()
        self._browser = None
        self._page = None

    async def login_with_2fa(
        self, gmail: GmailReader, timeout_sec: int = 120
    ) -> bool:
        """Login to Indy with 2FA support.

        Args:
            gmail: Connected GmailReader instance
            timeout_sec: Overall timeout for login

        Returns:
            True if login successful (including 2FA)
        """
        # Launch browser
        browser = await uc.start(headless=True)
        page = await browser.get("https://app.indy.fr/connexion")

        try:
            # Execute 2FA login
            success = await self._2fa.auto_2fa_login(
                page,
                gmail,
                self._settings.indy_email,
                self._settings.indy_password,
                timeout_sec=timeout_sec,
            )

            self._browser = browser
            self._page = page

            return success
        except Exception as e:
            logger.error("2FA login failed: %s", e, exc_info=True)
            browser.stop()
            return False
```

#### 3. FastAPI Dashboard (Optional)
File: `src/app.py`

```python
@app.post("/api/v1/sync/indy")
async def sync_indy(
    request: SyncRequest,
) -> dict[str, Any]:
    """Sync Indy transactions with optional 2FA.

    Request body:
    {
        "enable_2fa": true,
        "timeout_sec": 120
    }
    """
    settings = get_settings()

    # Connect Gmail if 2FA enabled
    gmail = None
    if request.enable_2fa:
        gmail = GmailReader(settings)
        gmail.connect()

    try:
        indy = IndyAdapter(settings)

        if gmail:
            success = await indy.login_with_2fa(gmail)
        else:
            success = await indy.login()  # Existing method

        if not success:
            return {"error": "Login failed", "status": "failed"}

        # ... export transactions, write to Sheets

        return {"status": "success", "transactions": count}

    finally:
        if gmail:
            gmail.close()
```

## Environment Setup

### .env Configuration

```bash
# Gmail (required for 2FA)
GMAIL_IMAP_USER=jules.willard.pro@gmail.com
GMAIL_IMAP_PASSWORD=abcd1234efgh5678  # 16-char app password

# Indy (optional if using CLI interactively)
INDY_EMAIL=jules@example.com
INDY_PASSWORD=secret

# Browser settings
NODRIVER_HEADLESS=true  # or false for debugging
INDY_2FA_TIMEOUT_SEC=120
```

### Gmail Setup (One-time)

1. **Enable 2FA on Jules' Google account**
   - Settings → Security → 2-Step Verification
   - Complete the setup

2. **Generate app password**
   - Settings → Security → App passwords
   - Select "Mail" and "Windows Computer"
   - Google generates 16-character password
   - Copy to `.env` as `GMAIL_IMAP_PASSWORD`

3. **Verify IMAP is enabled**
   - Gmail Settings → Forwarding and POP/IMAP
   - Ensure "Enable IMAP" is selected

## Testing Integration

### Unit Tests

```bash
# Run all 2FA adapter tests
pytest tests/test_indy_2fa_adapter.py -v

# Run with coverage
pytest tests/test_indy_2fa_adapter.py --cov=src.adapters.indy_2fa_adapter

# Run specific test
pytest tests/test_indy_2fa_adapter.py::TestIndy2FAAdapterAuto2FALogin::test_auto_2fa_login_full_flow_success -v
```

### Integration Test

```bash
# Manual test (requires real credentials)
python examples/indy_2fa_nodriver_example.py --headed

# With debug logging
LOGLEVEL=DEBUG python examples/indy_2fa_nodriver_example.py --headed
```

### Checklist

- [ ] Unit tests pass: `pytest tests/test_indy_2fa_adapter.py`
- [ ] Type check: `pyright --strict src/adapters/indy_2fa_adapter.py`
- [ ] Linting: `ruff check src/adapters/indy_2fa_adapter.py`
- [ ] Example runs successfully
- [ ] Gmail IMAP works (test GmailReader)
- [ ] Screenshots captured on error
- [ ] Logging doesn't expose secrets

## Monitoring & Observability

### Key Metrics to Track

```python
# Login duration
login_duration_sec = time.monotonic() - start_time
metrics["login_duration"] = login_duration_sec

# 2FA success rate
metrics["2fa_success_rate"] = success_count / total_attempts

# Gmail latency
gmail_latency_sec = time.monotonic() - email_send_time
metrics["gmail_latency"] = gmail_latency_sec

# Timeout rate
metrics["timeout_rate"] = timeout_count / total_attempts
```

### Logging Points

```python
# Start
logger.info("2FA login started", extra={"email": "j***@example.com"})

# 2FA detected
logger.info("2FA page detected", extra={"url": page.url})

# Code received
logger.info("2FA code received", extra={"code": "123***"})

# Success
logger.info("2FA login succeeded", extra={"elapsed_sec": 25})

# Failure
logger.error("2FA login failed", extra={
    "phase": "verify_button_click",
    "screenshot": "io/cache/indy-2fa-errors/xyz.png",
})
```

### Error Monitoring

Error screenshots are automatically saved to:
```
io/cache/indy-2fa-errors/
├── gmail-timeout-{uuid}.png
├── inject-failed-{uuid}.png
├── dashboard-not-reached-{uuid}.png
└── exception-{uuid}.png
```

Review these periodically to catch page changes or unexpected failures.

## Troubleshooting Guide

### Gmail IMAP Connection Fails

**Error**: `Gmail IMAP login failed` or `Permission denied`

**Solutions**:
1. Verify credentials: `python -c "from src.adapters.gmail_reader import GmailReader; GmailReader(Settings()).connect()"`
2. Check app password is 16 characters
3. Ensure 2FA is enabled on Jules' Google account
4. Verify IMAP is enabled in Gmail settings

### 2FA Page Not Detected

**Error**: `2FA page not detected, assuming already authenticated`

**Likely causes**:
1. Indy changed the 2FA URL pattern
2. Selector for code input no longer valid
3. Page loads too quickly (race condition)

**Solutions**:
1. Run exploration tool: `python tools/explore_indy.py --headed`
2. Take screenshot at 2FA step and inspect HTML
3. Update `URL_PATTERNS_2FA` or `SELECTORS_CODE_INPUT` in adapter
4. Add new selectors to `_detect_2fa_page()`

### Code Injection Fails

**Error**: `Failed to inject code or click verify button`

**Likely causes**:
1. Input field selector changed
2. Verify button text/selector changed
3. OTP field (6 separate digit inputs) instead of single text field

**Solutions**:
1. Inspect error screenshot (`io/cache/indy-2fa-errors/inject-failed-*.png`)
2. Add new selectors to `SELECTORS_CODE_INPUT` or `BUTTON_TEXTS_VERIFY`
3. Implement OTP digit-by-digit injection if needed

### Dashboard Not Reached

**Error**: `Dashboard not reached after 2FA verification`

**Likely causes**:
1. Wrong code entered (code was old/expired)
2. Page still loading (increase timeout)
3. Dashboard URL/element changed

**Solutions**:
1. Check screenshot for error messages
2. Increase `TIMEOUT_VERIFY_RESPONSE` in adapter
3. Update dashboard detection patterns in `_wait_for_dashboard()`

## Performance Optimization

### Reduce Login Time

1. **Reuse session (headless mode)**
   ```python
   # Save after first successful login
   await browser.save_storage_state("session.json")

   # Load on next login (skip 2FA)
   await browser.load_storage_state("session.json")
   ```

2. **Parallel 2FA flows** (if batch processing)
   ```python
   results = await asyncio.gather(
       auto_2fa_login(page1, gmail, ...),
       auto_2fa_login(page2, gmail, ...),
   )
   ```

3. **Adjust timeouts** after profiling
   ```python
   # If email always arrives < 10s
   TIMEOUT_GMAIL_POLL = 30  # Reduced from 60
   ```

## Security Hardening

### Secrets Management

- [ ] `.env` file is in `.gitignore`
- [ ] No credentials logged
- [ ] Email addresses masked in logs (`j***@example.com`)
- [ ] 2FA codes masked in logs (`123***`)
- [ ] Error screenshots don't contain sensitive data

### Access Control

- [ ] 2FA only enabled for authorized users
- [ ] Gmail credentials stored securely
- [ ] Session cookies encrypted (if stored)
- [ ] Error screenshots require authentication to view

### Audit Trail

```python
# Log successful logins
logger.info("Indy login successful", extra={
    "user": "j***@example.com",
    "method": "2fa",
    "timestamp": datetime.now().isoformat(),
})

# Log failed attempts
logger.warning("Indy login failed", extra={
    "user": "j***@example.com",
    "phase": "2fa_verification",
    "attempts": 1,
    "timestamp": datetime.now().isoformat(),
})
```

## Future Enhancements

### Phase 2
- [ ] Session reuse (avoid 2FA on subsequent logins)
- [ ] Adaptive timeout (learn email delivery times)
- [ ] OTP field support (digit-by-digit injection)
- [ ] Retry logic (auto-request new code if expired)

### Phase 3
- [ ] SMS 2FA support (if Indy adds it)
- [ ] Biometric support (if Indy adds it)
- [ ] Push notification approval (if Indy adds it)
- [ ] Batch user management (parallel logins)

## Rollback Plan

If 2FA breaks production:

1. **Immediate**: Disable 2FA in CLI
   ```bash
   # Use existing OAuth/session method
   python -m src.cli sync --no-2fa
   ```

2. **Short-term**: Revert to Playwright (if available)
   ```bash
   # Use Playwright instead of nodriver
   export BROWSER_ENGINE=playwright
   python -m src.cli sync
   ```

3. **Long-term**: Investigate root cause
   - Review error screenshots
   - Run exploration tool (headed mode)
   - Update selectors/patterns
   - Redeploy

## Support

- **Documentation**: `docs/NODRIVER_2FA_INJECTION.md`
- **Quick reference**: `docs/NODRIVER_2FA_QUICK_REF.md`
- **Example code**: `examples/indy_2fa_nodriver_example.py`
- **Research**: `docs/RESEARCH_NODRIVER_2FA.md`
- **Error screenshots**: `io/cache/indy-2fa-errors/`

## Deployment Checklist

- [ ] Unit tests pass (100% coverage)
- [ ] Integration tests pass (real login)
- [ ] Type checking passes (`pyright --strict`)
- [ ] Linting passes (`ruff check`)
- [ ] Documentation updated
- [ ] Example works
- [ ] Error handling tested
- [ ] Secrets hardened
- [ ] Monitoring configured
- [ ] Rollback plan documented
