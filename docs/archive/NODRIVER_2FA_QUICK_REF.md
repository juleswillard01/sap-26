# Nodriver 2FA Injection — Quick Reference

## Problem
Indy requires 2FA after login. We need to:
1. Detect 2FA page
2. Get code from Gmail
3. Inject code
4. Click verify
5. Confirm dashboard

## Solution
Use `Indy2FAAdapter` with nodriver + Gmail IMAP:

```python
from src.adapters.indy_2fa_adapter import Indy2FAAdapter
from src.adapters.gmail_reader import GmailReader
import nodriver as uc

# Setup
gmail = GmailReader(settings)
gmail.connect()
adapter = Indy2FAAdapter()

browser = await uc.start(headless=False)
page = await browser.get("https://app.indy.fr/connexion")

# Login with 2FA
success = await adapter.auto_2fa_login(
    page, gmail, "email@indy.fr", "password", timeout_sec=120
)

# Cleanup
gmail.close()
browser.stop()
```

## Key Components

### 1. Nodriver Element Finding

```python
# By text (powerful!)
button = await page.find("Vérifier")

# By CSS selector
input_field = await page.query_selector("input[type='text']")

# By XPath
elements = await page.query_selector_all("//button")
```

### 2. Keyboard Input

```python
# Send keys
await element.send_keys("123456")  # Text
await element.send_keys("Enter")   # Special key
await element.send_keys("Ctrl", "a")  # Modifiers

# Clear + fill
await element.send_keys("Ctrl", "a")
await element.send_keys("Backspace")
await element.send_keys("new_value")
```

### 3. Waiting & Checking

```python
# Sleep
await page.sleep(2)  # 2 seconds

# Check URL
if "dashboard" in page.url:
    ...

# Get page content
html = await page.get_content()

# Take screenshot
await page.save_screenshot("screenshot.png")
```

### 4. Gmail Code

```python
# Get code from Gmail (blocking, runs in thread pool)
code = await adapter._get_2fa_code_async(gmail, timeout_sec=60)

# Or directly:
code = gmail.get_latest_2fa_code(timeout_sec=60)
```

## Configuration

### .env Requirements

```bash
# Gmail (required for 2FA)
GMAIL_IMAP_USER=jules.willard.pro@gmail.com
GMAIL_IMAP_PASSWORD=abcd1234efgh5678  # 16-char app password, NOT account password

# Indy (optional, for auto-fill)
INDY_EMAIL=jules@example.com
INDY_PASSWORD=secret

# Debug
APP_ENV=development  # or "production"
```

### Gmail App Password Setup

1. Enable 2FA on Jules' Google account
2. Settings → Security → App passwords
3. Select "Mail" + "Windows Computer"
4. Google generates 16-char password
5. Copy to .env as GMAIL_IMAP_PASSWORD

**Important**: Use app password, NOT account password.

## Selectors Reference

### Email Input
```
input[type='email']
input[name='email']
input[placeholder*='email']
```

### Password Input
```
input[type='password']
input[name='password']
input[placeholder*='mot de passe']
```

### 2FA Code Input
```
input[placeholder*='code']
input[placeholder*='verification']
input[placeholder*='authentification']
input[name='code']
input[type='text']  # Fallback
```

### Verify Button
```
Text: "Vérifier", "Valider", "Confirmer", "Verify", "Confirm"
Selector: button[type='submit']
```

## Timeout Values

| Phase | Default (s) | Purpose |
|-------|-------------|---------|
| 2FA page detection | 30 | Wait for URL/selector |
| Gmail polling | 60 | Email can be slow |
| Code injection | 10 | Fill + click |
| Dashboard wait | 30 | Redirect + page load |
| **Total** | **120** | Overall deadline |

## Error Handling

### 2FA page not detected?
- Check URL: `https://app.indy.fr/verification`
- Check selectors in `docs/NODRIVER_2FA_INJECTION.md`
- Look at `io/cache/indy-2fa-errors/*.png` screenshots

### Gmail code never arrives?
- Test GmailReader independently
- Check Gmail app password is correct
- Verify Indy's account uses Gmail for 2FA (not SMS)

### Code injection fails?
- Check selector still valid (Indy may change HTML)
- Try different code format (with/without dashes)
- Look at error screenshots

### Dashboard not reached?
- Code may have been wrong (old/expired)
- Wait a bit longer (set timeout higher)
- Check screenshots for error messages

## Logging & Debugging

### Standard Flow Log
```
Starting Indy 2FA login flow
Filling login form
Submitting login form
Detecting 2FA page
2FA page detected, polling Gmail for code
2FA code received
Injecting 2FA code
Code injected and verify button clicked
Waiting for dashboard redirect
2FA login completed successfully
```

### Debug Mode
```python
import logging
logging.getLogger("src.adapters").setLevel(logging.DEBUG)
```

### Screenshots on Error
Saved to: `io/cache/indy-2fa-errors/{context}-{uuid}.png`

Contexts:
- `gmail-timeout` — Code not received from Gmail
- `inject-failed` — Code injection or button click failed
- `dashboard-not-reached` — Dashboard not detected after 2FA
- `exception` — Unhandled exception during flow

## Security Notes

### ✓ DO
- Store credentials in `.env`
- Use app passwords (not account passwords)
- Mask emails in logs (`j***@example.com`)
- Mask codes in logs (`123***`)
- Take error screenshots without sensitive data
- Clear sensitive data from memory

### ✗ DON'T
- Log full email/password
- Log full codes
- Store passwords in code
- Commit `.env`
- Store session cookies unencrypted
- Log raw page HTML (may contain sensitive data)

## Performance Tips

### Gmail Polling is Slow
- Email takes 3-15 seconds to arrive
- Gmail IMAP sync adds 2-5 seconds
- Total: ~5-30 seconds (60s timeout = safe)
- Don't reduce timeout below 30s

### Browser Performance
- nodriver is lightweight (undetected Chrome)
- Typical login: 5-20 seconds total
- Network latency matters (especially Gmail IMAP)

### Concurrent Operations
- Could parallelize: page waiting + Gmail polling
- Currently sequential (simpler, safer)
- See `asyncio.gather()` if needed in future

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| 2FA page not found | URL/selector changed | Update `URL_PATTERNS_2FA`, `SELECTORS_CODE_INPUT` |
| Code injection fails | Input field type changed | Try different selector or OTP digit-by-digit input |
| Gmail times out | Email not sent/received | Check SMTP settings on Indy, test GmailReader |
| Dashboard never reached | Wrong code or timeout | Increase timeout, check error screenshots |
| Permission denied | Gmail IMAP not enabled | Enable in Gmail settings, use app password |
| Browser crashes | nodriver issue | Try with `--no-first-run`, reinstall nodriver |

## Files & References

| File | Purpose |
|------|---------|
| `src/adapters/indy_2fa_adapter.py` | Main implementation |
| `src/adapters/gmail_reader.py` | Gmail IMAP reader |
| `tests/test_indy_2fa_adapter.py` | Unit tests |
| `examples/indy_2fa_nodriver_example.py` | Standalone example |
| `docs/NODRIVER_2FA_INJECTION.md` | Full documentation |
| `tools/explore_indy.py` | Page exploration (headed mode) |

## Next Steps

1. **Test Gmail reader**: `pytest tests/test_gmail_reader.py`
2. **Test adapter**: `pytest tests/test_indy_2fa_adapter.py`
3. **Run example**: `python examples/indy_2fa_nodriver_example.py`
4. **Integrate into InidyAdapter**: Use in `src/adapters/indy_adapter.py`
5. **Add to CLI**: `python -m src.cli sync --2fa`

## Support

- **Debug screenshots**: `io/cache/indy-2fa-errors/`
- **Logs**: Check stdout for `2FA login` messages
- **Manual run**: `examples/indy_2fa_nodriver_example.py --headed`
