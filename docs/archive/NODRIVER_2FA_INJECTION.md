# Nodriver 2FA Code Injection — Complete Guide

## Problem Statement

After nodriver bypasses Cloudflare Turnstile and submits email/password on app.indy.fr, Indy shows a 2FA code input page. We need to:

1. Detect the 2FA page (selectors, URL patterns)
2. Read the code from Gmail (via GmailReader IMAP)
3. Fill the code into the input field
4. Click submit/verify
5. Wait for dashboard confirmation

## Nodriver vs Playwright

| Feature | Nodriver | Playwright |
|---------|----------|-----------|
| Turnstile bypass | ✅ Built-in | ❌ Requires solvers |
| Detection | ⚠️ Hard to detect | ✅ Easier |
| Async API | ✅ Fully async | ✅ Fully async |
| Element finding | ✅ `find()`, `query_selector()` | ✅ `locator()` |
| Keyboard input | ✅ `send_keys()` | ✅ `fill()` |
| Waiting | ✅ `sleep()`, `wait_for()` | ✅ `wait_for_selector()` |
| Performance | ✅ Slightly faster | ✅ Comparable |

**Key difference**: Nodriver's `find()` is powerful for text-based selectors:
```python
# Find by text (powerful!)
button = await page.find("Se connecter")  # Finds button with exact text

# Find by CSS selector
button = await page.query_selector("button[type='submit']")

# Find by XPath
elements = await page.query_selector_all("//input[@type='text']")
```

---

## Indy 2FA Page Detection

### URL Patterns

Indy's 2FA page typically appears at one of:
- `https://app.indy.fr/verification`
- `https://app.indy.fr/verify-code`
- `https://app.indy.fr/2fa`
- `https://app.indy.fr/connexion?step=verify` (status = 2FA active)

### Page Indicators

After login form submission, watch for:
```python
# Indicative headers/titles
"Verification"
"Verification Code"
"Code d'authentification"
"Confirmez votre identité"
"Entrez le code"
```

### Common Selectors

Indy's 2FA input likely uses one of:
```
input[type='text'] + button          # Standard text input + submit
input[placeholder*='code']           # Placeholder contains "code"
input[placeholder*='verification']   # Placeholder contains "verification"
input[placeholder*='authentification']  # French version
input[name='code']                   # Explicit name
input[id='verification-code']        # Explicit ID
input[data-testid='otp-input']      # React data-testid
```

### Verify Button Selectors

```
button:has-text('Vérifier')          # French: Verify
button:has-text('Confirmer')         # French: Confirm
button:has-text('Valider')           # French: Validate
button[type='submit']                # Generic submit
button:contains('Verify')             # Generic English
```

---

## Gmail Code Extraction

### Prerequisites

1. Jules' Gmail IMAP credentials must be in `.env`:
```
GMAIL_IMAP_USER=jules.willard.pro@gmail.com
GMAIL_IMAP_PASSWORD=<16-char app password, NOT account password>
```

2. Gmail App Passwords enabled (2FA on Jules' Google account required):
   - Settings → Security → App passwords
   - Select "Mail" and "Windows Computer"
   - Generate 16-char app password

3. GmailReader module available:
```python
from src.adapters.gmail_reader import GmailReader
from src.config import Settings
```

### Timing Considerations

**Email delivery delays**:
- Indy sends code immediately (< 1 second)
- Gmail IMAP sync: 2-5 seconds typical
- **Total expected time**: 5-15 seconds
- **Upper bound**: 30 seconds
- **Timeout policy**: 60 seconds (safe margin)

**Code validity period**:
- Typical 2FA codes: valid for 5-10 minutes
- Indy likely: 10 minutes (standard)
- Retry strategy: If code expires, request new code and poll again

**Polling interval**:
- Check every 3-5 seconds (avoid hammering)
- GmailReader default: 5 seconds
- Adjust if emails arrive faster/slower

---

## Implementation Architecture

### Module: `src/adapters/indy_2fa_adapter.py`

```python
class Indy2FAAdapter:
    """Handle Indy 2FA code injection via nodriver + Gmail."""

    async def auto_2fa_login(
        self,
        page,  # nodriver page object
        email: str,
        password: str,
        timeout_sec: int = 120,
    ) -> bool:
        """
        Orchestrate full 2FA flow:
        1. Fill email/password
        2. Submit login form
        3. Detect 2FA page
        4. Poll Gmail for code
        5. Inject code
        6. Click verify
        7. Wait for dashboard

        Returns:
            True if successful, False otherwise.

        Raises:
            RuntimeError: If critical step fails.
        """
        ...
```

### Phase 1: Detect 2FA Page

```python
async def _detect_2fa_page(page, timeout_sec: int = 30) -> bool:
    """Detect if we're on 2FA page by URL or selector."""
    start = time.monotonic()

    while time.monotonic() - start < timeout_sec:
        url = page.url.lower()

        # Check URL patterns
        if any(x in url for x in [
            "verification", "2fa", "verify",
            "authentification", "code",
        ]):
            return True

        # Check for 2FA input selector
        try:
            code_input = await page.query_selector(
                "input[placeholder*='code']"
            )
            if code_input:
                return True
        except Exception:
            pass

        await page.sleep(2)

    return False
```

### Phase 2: Poll Gmail for Code

```python
async def _get_2fa_code(
    self,
    gmail_reader: GmailReader,
    timeout_sec: int = 60,
) -> str | None:
    """Poll Gmail IMAP for 2FA code with timeout."""
    code = gmail_reader.get_latest_2fa_code(
        timeout_sec=timeout_sec,
        poll_interval_sec=5,
        sender_filter="indy",
    )
    return code
```

### Phase 3: Inject Code + Verify

```python
async def _inject_and_verify(
    page,
    code: str,
) -> bool:
    """Inject code into input field and click verify."""

    # Find code input (try multiple selectors)
    code_input = None
    selectors = [
        "input[placeholder*='code']",
        "input[placeholder*='verification']",
        "input[placeholder*='authentification']",
        "input[name='code']",
        "input[type='text']",
    ]

    for selector in selectors:
        try:
            code_input = await page.query_selector(selector)
            if code_input:
                break
        except Exception:
            continue

    if not code_input:
        return False

    # Fill code
    await code_input.send_keys(code)
    await page.sleep(1)

    # Find and click verify button
    verify_btn = None
    button_texts = [
        "Vérifier", "Valider", "Confirmer",
        "Verify", "Confirm", "Submit",
    ]

    for text in button_texts:
        try:
            verify_btn = await page.find(text)
            if verify_btn:
                break
        except Exception:
            continue

    if not verify_btn:
        # Fallback to generic submit button
        verify_btn = await page.query_selector("button[type='submit']")

    if not verify_btn:
        return False

    await verify_btn.click()
    return True
```

### Phase 4: Wait for Dashboard

```python
async def _wait_for_dashboard(
    page,
    timeout_sec: int = 30,
) -> bool:
    """Wait for redirect to dashboard (successful 2FA)."""
    start = time.monotonic()

    while time.monotonic() - start < timeout_sec:
        url = page.url.lower()

        # Check if on dashboard
        if any(x in url for x in [
            "dashboard", "accueil", "app.indy.fr",
            "/accounts", "/transactions",
        ]):
            # Verify page loaded (look for key element)
            try:
                await page.query_selector(
                    "[data-testid='account-balance']",
                    timeout=5000
                )
                return True
            except Exception:
                # Page changed but element not found yet, wait
                pass

        await page.sleep(2)

    return False
```

---

## Error Handling & Retry

### Scenarios

| Scenario | Action | Retry? |
|----------|--------|--------|
| 2FA page not detected | Screenshot, log, fail | No (configuration issue) |
| Gmail code not received | Screenshot, timeout log | Yes (1x, request new code) |
| Code input not found | Screenshot, log, fail | No (page changed) |
| Code injection fails | Screenshot, log, fail | No (code format issue?) |
| Verify button not found | Screenshot, log, fail | No (page layout changed) |
| Dashboard not reached | Screenshot, log, fail | Maybe (retry if < 30s) |

### Timeout Values

```python
TIMEOUT_2FA_PAGE_DETECTION = 30  # seconds
TIMEOUT_GMAIL_POLL = 60           # seconds (Gmail can be slow)
TIMEOUT_CODE_INJECTION = 10       # seconds
TIMEOUT_VERIFY_RESPONSE = 15      # seconds (wait for dashboard redirect)
TIMEOUT_TOTAL = 120               # seconds (overall deadline)
```

### Screenshot on Error

```python
async def _screenshot_error(page, context: str) -> None:
    """Capture screenshot for debugging (RGPD-safe)."""
    try:
        from uuid import uuid4
        filename = f"io/cache/indy-2fa-error-{context}-{uuid4()}.png"
        await page.save_screenshot(filename)
        logger.warning(f"Error screenshot saved: {filename}")
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
```

---

## Nodriver API Reference

### Finding Elements

```python
# By text (preferred for buttons)
element = await page.find("Vérifier")

# By CSS selector
element = await page.query_selector("input[type='text']")

# By XPath
elements = await page.query_selector_all("//button")

# Wait for element (with timeout)
element = await page.find("Code", timeout=10000)  # ms
```

### Keyboard Input

```python
# Send keys (supports text + special keys)
await element.send_keys("123456")
await element.send_keys("Enter")  # Submit
await element.send_keys("Tab")    # Move focus
await element.send_keys("Shift", "A")  # Modifier keys

# Clear field before filling (optional)
await element.send_keys("Control", "a")
await element.send_keys("Backspace")
```

### Click & Navigation

```python
# Click element
await button.click()

# Wait for URL change (navigation)
await page.wait_for_navigation(timeout=10000)

# Get current URL
url = page.url

# Sleep/wait
await page.sleep(2)  # 2 seconds

# Get page content (HTML)
html = await page.get_content()

# Take screenshot
await page.save_screenshot("screenshot.png")
```

### Async Patterns

```python
# Run multiple tasks concurrently
tasks = [
    poll_gmail(gmail_reader),
    wait_for_2fa_page(page),
]
results = await asyncio.gather(*tasks, return_exceptions=True)

# Handle exceptions in gather
results = await asyncio.gather(*tasks, return_exceptions=True)
for result in results:
    if isinstance(result, Exception):
        logger.error(f"Task failed: {result}")
```

---

## Complete Implementation

See: `src/adapters/indy_2fa_adapter.py`

Key features:
- ✅ Robust element detection (multiple selectors)
- ✅ Gmail IMAP polling with timeout
- ✅ Error screenshots (RGPD-compliant)
- ✅ Async-first, no blocking I/O
- ✅ Comprehensive logging
- ✅ Configurable timeouts
- ✅ Retry logic for transient failures

---

## Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_auto_2fa_login_success():
    """Full 2FA flow succeeds."""
    # Mock nodriver page
    mock_page = MagicMock()
    mock_page.url = "https://app.indy.fr/verification"

    # Mock Gmail reader
    mock_gmail = MagicMock()
    mock_gmail.get_latest_2fa_code.return_value = "123456"

    # Execute
    adapter = Indy2FAAdapter()
    result = await adapter.auto_2fa_login(
        mock_page, "test@example.com", "password"
    )

    assert result is True
```

### Integration Tests

- Real nodriver browser (headed mode)
- Real Gmail IMAP (test account)
- Actual Indy login (optional, requires 2FA)

---

## Logging & Observability

```python
logger.info(
    "2FA flow started",
    extra={
        "email": "j***@example.com",  # Mask
        "timeout": 120,
    }
)

logger.info(
    "2FA page detected",
    extra={"url": page.url}
)

logger.info(
    "2FA code received",
    extra={"code": "***456"}  # Mask first 3 digits
)

logger.error(
    "2FA flow failed",
    extra={
        "phase": "verify_button_click",
        "url": page.url,
        "screenshot": "io/cache/indy-2fa-error-xyz.png",
    },
    exc_info=True,
)
```

---

## Security & Secrets

### Do's ✅

- Store credentials in `.env`
- Mask credentials in logs
- Use app passwords (not account passwords)
- Mask codes (first 3 digits in logs)
- Encrypt stored session cookies
- Clear sensitive data from memory after use

### Don'ts ❌

- Log full email addresses (mask username)
- Log full codes (mask)
- Store passwords in code
- Commit `.env`
- Store cookies in plaintext
- Log raw HTML (may contain sensitive data)

---

## Troubleshooting

### 2FA page not detected

**Likely causes**:
1. URL pattern not in detection list
2. Selector changed by Indy
3. Login already successful (no 2FA needed)

**Solutions**:
1. Check `io/cache/indy-2fa-error-*.png` screenshots
2. Add new URL pattern or selector
3. Inspect Indy's page HTML in `explore_indy.py` (headed mode)

### Gmail code never arrives

**Likely causes**:
1. App password incorrect
2. Gmail account 2FA not set up
3. Email address mismatch (Indy sends to different address)
4. Indy using SMS instead of email

**Solutions**:
1. Test GmailReader independently
2. Check Gmail security settings
3. Verify Indy's account email settings
4. Check if Indy has SMS 2FA enabled

### Code injection fails

**Likely causes**:
1. Input field selector changed
2. Field type is OTP (one-per-digit)
3. Code format mismatch (with dashes/spaces)

**Solutions**:
1. Update selectors
2. Split code into individual digits: `"1", "2", "3", "4", "5", "6"`
3. Format code before injection

### Dashboard never reached

**Likely causes**:
1. Code was wrong
2. Code expired (took > 10 min)
3. Page layout changed

**Solutions**:
1. Check screenshots for errors
2. Increase code polling timeout
3. Request new code and retry

---

## References

- **Nodriver docs**: https://github.com/ultrafunkamsterdam/nodriver
- **Nodriver element selection**: Element finding patterns (CSS, XPath, text)
- **Gmail IMAP**: See `src/adapters/gmail_reader.py`
- **Indy exploration**: `tools/explore_indy.py`
- **CDC reference**: `docs/CDC.md` §3.1 (Indy banking import)
