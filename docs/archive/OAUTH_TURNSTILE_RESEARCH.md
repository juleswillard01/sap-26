# Research: Automating "Connexion avec Google" on Indy WITHOUT Triggering Cloudflare Turnstile

**Status**: Deep Research + Feasibility Analysis
**Date**: 2026-03-21
**Context**: Jules' Indy account has NO 2FA enabled, making this simpler than typical OAuth flows.

---

## Executive Summary

The "Connexion avec Google" button on Indy's login page triggers **Cloudflare Turnstile CAPTCHA** — a bot detector that blocks headless Playwright automation. However, **three feasible approaches exist** to bypass it:

1. **Direct Google OAuth URL Bypass** (RECOMMENDED) — Skip Indy's login page entirely
2. **Session Persistence + Headed Mode** (CURRENT, WORKING) — Your existing strategy
3. **Cookies/Token Reuse** (ADVANCED) — Extract auth tokens from headed login

This document provides concrete Python implementations, security considerations, and trade-offs.

---

## The Problem: Cloudflare Turnstile

### How Turnstile Works

1. Indy loads `<iframe src="https://challenges.cloudflare.com/turnstile/...">` on `/login`
2. Turnstile checks for:
   - Browser automation indicators (headless mode, Playwright detection)
   - User interaction patterns (mouse movement, typing speed, etc.)
   - IP reputation, TLS fingerprints
3. If suspected bot → blocks login, requires CAPTCHA solve
4. Turnstile **cannot be easily bypassed** by modifying headers or User-Agent alone

### Why Session Persistence Works

Your current strategy (saved state in `SESSION_STATE_FILE`) bypasses Turnstile by:
- Reusing cookies from a previous **headed** (interactive) login
- Headed mode includes real browser automation traces
- Turnstile passes because the session is already authenticated

**Limitation**: Cookies expire (typically 30-90 days), requiring periodic re-login with `session_mode="headed"`.

---

## Three Feasible Approaches

### Approach 1: Direct Google OAuth URL Bypass (RECOMMENDED)

**Key Insight**: Indy's "Connexion avec Google" button redirects to Google OAuth URL.
**Google's OAuth page has NO Turnstile** → bot-proof automation possible.

#### How It Works

1. **Discover Indy's OAuth Parameters**
   - Indy registers with Google's OAuth 2.0
   - When you click "Connexion avec Google", Indy redirects to:
     ```
     https://accounts.google.com/o/oauth2/v2/auth?
       client_id=INDY_CLIENT_ID&
       redirect_uri=https://app.indy.fr/oauth/callback&
       scope=email%20profile&
       response_type=code&
       state=RANDOM_STATE_TOKEN
     ```

2. **Authenticate with Google** (no Turnstile)
   - Navigate Playwright directly to Google OAuth URL
   - Fill Google credentials (email/password)
   - Google verifies → generates auth `code`

3. **Redirect Back to Indy**
   - Google redirects to `https://app.indy.fr/oauth/callback?code=AUTH_CODE`
   - Indy callback endpoint exchanges code for session token
   - **Turnstile may not trigger on callback** (already redirected from Google)

#### Implementation

```python
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)

INDY_OAUTH_CLIENT_ID = "YOUR_INDY_CLIENT_ID"  # Will be discovered via NetworkLogger
GOOGLE_EMAIL = "jules@example.com"
GOOGLE_PASSWORD = "secure_password"

def login_via_google_oauth(
    headless: bool = True,
    save_cookies: bool = True
) -> dict[str, str]:
    """
    Login to Indy via Google OAuth, bypassing Cloudflare Turnstile.

    Returns:
        Dict with keys: 'email', 'session_token', 'cookies_json'
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Step 1: Discover Indy's OAuth URL (via NetworkLogger or manual inspection)
            indy_oauth_url = (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={INDY_OAUTH_CLIENT_ID}&"
                f"redirect_uri=https://app.indy.fr/oauth/callback&"
                f"scope=email%20profile&"
                f"response_type=code&"
                f"state=sap_facture_{int(time.time())}"
            )

            logger.info(f"Navigating to Google OAuth: {indy_oauth_url}")
            page.goto(indy_oauth_url, wait_until="networkidle")

            # Step 2: Authenticate with Google (no Turnstile here!)
            # Google redirects to login if needed
            if "accounts.google.com" in page.url:
                logger.info("Google login page detected, filling credentials...")

                # Handle "Choose account" screen if it appears
                try:
                    page.wait_for_selector("div[data-email]", timeout=5000)
                    # If we see a "Create account" button, skip it
                    # Try to find Jules' existing account
                    page.click("div[data-email]:first-child")  # Select first account
                except Exception:
                    pass  # No account selector, proceed to login

                # Fill email
                page.wait_for_selector("input[type='email']", timeout=5000)
                page.fill("input[type='email']", GOOGLE_EMAIL)
                page.click("button:has-text('Next')")

                # Fill password (Jules has NO 2FA, so no OTP needed)
                page.wait_for_selector("input[type='password']", timeout=5000)
                page.fill("input[type='password']", GOOGLE_PASSWORD)
                page.click("button:has-text('Next')")

                logger.info("Google credentials filled, waiting for redirect...")

            # Step 3: Wait for redirect back to Indy callback
            # Google will redirect to: https://app.indy.fr/oauth/callback?code=...
            page.wait_for_url(
                "https://app.indy.fr/oauth/callback**",
                timeout=30_000
            )

            logger.info(f"Redirected to Indy callback: {page.url}")

            # Step 4: Extract auth code from callback URL
            parsed_url = urlparse(page.url)
            query_params = parse_qs(parsed_url.query)
            auth_code = query_params.get("code", [None])[0]

            if not auth_code:
                raise ValueError("No auth code in callback URL")

            logger.info(f"Received auth code: {auth_code[:20]}...")

            # Step 5: Indy's callback endpoint now processes the code
            # Wait for dashboard to load (sign of successful auth)
            page.wait_for_url("https://app.indy.fr/dashboard**", timeout=15_000)

            logger.info("Successfully logged in via Google OAuth!")

            # Step 6: Save session state for future headless reuse
            if save_cookies:
                state_file = Path("io/cache/indy_oauth_state.json")
                state_file.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(state_file))
                logger.info(f"Session state saved to {state_file}")

            # Extract session cookies
            cookies = context.cookies()
            cookies_dict = {c["name"]: c["value"] for c in cookies}

            return {
                "email": GOOGLE_EMAIL,
                "auth_code": auth_code,
                "cookies_json": json.dumps(cookies_dict),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Google OAuth login failed: {e}", exc_info=True)
            page.screenshot(path="io/cache/oauth_error.png")
            raise

        finally:
            browser.close()
```

#### Advantages

- ✅ **No Turnstile interaction** — Google's OAuth page has no CAPTCHA
- ✅ **Fully automated** — No manual intervention needed
- ✅ **Fast** — Direct redirect, no need for session persistence
- ✅ **Deterministic** — Jules has NO 2FA, so no OTP extraction needed
- ✅ **Reusable tokens** — Can extract and cache auth code

#### Disadvantages

- ❌ **Requires discovering Indy's OAuth `client_id`** — Need to inspect network traffic
- ❌ **Callback URL may change** — If Indy updates OAuth config
- ❌ **Google may detect bot patterns** — Though less likely than Turnstile
- ❌ **Depends on Google OAuth stability** — Google could change OAuth flow

#### Security Considerations

- **Store Google password in `.env`** (never hardcode)
- **Don't log auth codes** (handle as secrets)
- **Validate callback URL origin** (ensure it's Indy's domain)
- **Use HTTPS only** (Playwright enforces by default)

#### Discovery: Finding Indy's OAuth Client ID

Use **NetworkLogger** to discover the OAuth URL:

```python
from pathlib import Path
from src.adapters.network_logger import NetworkLogger
from playwright.sync_api import sync_playwright

net_logger = NetworkLogger(output_dir=Path("io/research/indy_oauth"))

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    net_logger.attach(page)

    page.goto("https://app.indy.fr/login")
    page.wait_for_selector("button:has-text('Google')")

    # Intercept the redirect
    with page.expect_navigation():
        page.click("button:has-text('Google')")

    # Check the network log for the Google OAuth URL
    endpoints = net_logger.get_api_endpoints()
    for key, info in endpoints.items():
        if "oauth" in key or "accounts.google" in key:
            print(f"Found OAuth endpoint: {key}")

    browser.close()

net_logger.export()
# Review io/research/indy_oauth/api-endpoints.md for OAuth URL parameters
```

---

### Approach 2: Session Persistence + Headed Mode (CURRENT, WORKING)

This is your **existing strategy** in `IndyBrowserAdapter.connect()`.

#### How It Works

1. **First login (headed)**
   - User starts Playwright in **headed mode** (browser visible)
   - Turnstile allows human interaction
   - Session cookies saved to `io/cache/indy_browser_state.json`

2. **Subsequent logins (headless)**
   - Playwright loads saved session state
   - Already authenticated, **no login page visit needed**
   - No Turnstile encounter

#### Implementation (Already in Your Code)

```python
def connect(self, session_mode: str = "headless") -> None:
    if session_mode == "headless" and self.SESSION_STATE_FILE.exists():
        context_kwargs = {"storage_state": str(self.SESSION_STATE_FILE)}
        # Reuse saved cookies → skip login, bypass Turnstile
    elif session_mode == "headed":
        # Interactive login with 2FA wait (120s timeout)
        self._login_interactive()
```

#### Advantages

- ✅ **Already implemented** in your codebase
- ✅ **Proven working** with 2FA (even though Jules has none)
- ✅ **Low complexity** — No OAuth discovery needed
- ✅ **No Google account needed** — Pure Indy login

#### Disadvantages

- ❌ **Requires manual login every 30-90 days** when cookies expire
- ❌ **Headed mode timeout** — 120s window for manual entry
- ❌ **Session state file management** — Must handle renewal
- ❌ **Not fully autonomous** — Human intervention periodic

#### When to Use

- **Scheduled jobs** — Token refresh on a cron (weekly/monthly)
- **Acceptable manual intervention** — Not a blocker for your use case
- **Simplicity over automation** — Avoid OAuth complexity

---

### Approach 3: Token Reuse + API-Based Session Extension (ADVANCED)

**Concept**: Extract auth tokens from a headed login, then use API calls to keep session alive without revisiting login page.

#### How It Works

1. **Extract tokens from headed login**
   - After successful login in headed mode, capture session tokens
   - These are typically in localStorage or secure cookies

2. **Extend session via API calls**
   - Some portals support refresh token endpoints
   - Call refresh endpoint periodically to keep session fresh
   - Avoid login page entirely

#### Research Needed

This requires discovering:
- **Indy's session token structure** — JWT? Opaque? Where stored?
- **Refresh endpoint** — Does Indy support `POST /oauth/refresh`?
- **Token TTL** — How long before expiration?

**NetworkLogger usage**:

```python
net_logger = NetworkLogger(output_dir=Path("io/research/indy_tokens"))
# Login in headed mode
# Capture all requests to endpoints containing "token", "refresh", "session"
# Save network log and analyze token lifecycle
```

#### Advantages

- ✅ **Fully autonomous** — No manual intervention
- ✅ **No Google OAuth needed** — Pure Indy tokens
- ✅ **Potential for extended session** — If refresh endpoint exists

#### Disadvantages

- ❌ **Requires deep token analysis** — Unknown if endpoint exists
- ❌ **Fragile to API changes** — Indy could change token structure
- ❌ **May violate Indy's ToS** — Directly manipulating tokens is aggressive

---

## Recommendation & Implementation Plan

### For SAP-Facture

**Use Approach 1 (Google OAuth) as PRIMARY**, with Approach 2 (Session Persistence) as FALLBACK.

#### Phase 1: Discover OAuth URL (1-2 hours)

```bash
# Run NetworkLogger to capture OAuth flow
python examples/network_logger_example.py --mode indy_oauth

# Review output in io/research/indy_oauth/api-endpoints.md
# Extract INDY_OAUTH_CLIENT_ID and redirect_uri parameters
```

#### Phase 2: Implement OAuth Login (2-3 hours)

Add new method to `IndyBrowserAdapter`:

```python
async def login_via_google_oauth(self) -> None:
    """Alternative login: Google OAuth instead of email/password."""
    # Implementation from "Approach 1" above
    # Store auth code and session state
```

#### Phase 3: Integration Tests (1-2 hours)

```python
# tests/test_indy_google_oauth.py
def test_google_oauth_login():
    """OAuth login should skip Turnstile and land on dashboard."""
    adapter = IndyBrowserAdapter(settings)
    adapter.login_via_google_oauth()
    assert adapter._page.url.startswith("https://app.indy.fr/dashboard")
```

#### Phase 4: Fallback to Session Persistence

Keep existing `session_mode="headed"` flow as backup:
- If OAuth fails → fall back to session persistence
- If session expired → trigger OAuth refresh

### Code Structure

```python
# src/adapters/indy_adapter.py (updated)

class IndyBrowserAdapter:

    OAUTH_MODE_GOOGLE = "oauth_google"
    OAUTH_MODE_SESSION = "session_persistence"

    def connect(self, session_mode: str = "auto") -> None:
        """Connect to Indy with auto fallback strategy."""
        if session_mode == "auto":
            try:
                self._login_via_google_oauth()
            except Exception as e:
                logger.warning(f"OAuth login failed: {e}, falling back to session persistence")
                if self.SESSION_STATE_FILE.exists():
                    self._login_via_session_persistence()
                else:
                    self._login_interactive()
        elif session_mode == "oauth":
            self._login_via_google_oauth()
        elif session_mode == "session":
            self._login_via_session_persistence()
        else:
            raise ValueError(f"Invalid session_mode: {session_mode}")

    def _login_via_google_oauth(self) -> None:
        """Login via Google OAuth (no Turnstile)."""
        # Implementation from Approach 1
        pass

    def _login_via_session_persistence(self) -> None:
        """Login via reused session cookies (existing)."""
        # Existing code
        pass
```

---

## Security Checklist

- [ ] Google credentials stored in `.env`, never hardcoded
- [ ] Auth codes never logged (redact in debug logs)
- [ ] Session state file (`indy_oauth_state.json`) never committed
- [ ] HTTPS validation enabled (Playwright default)
- [ ] Callback URL origin validation (ensure `app.indy.fr`)
- [ ] OAuth URL parameters validated (no injection)
- [ ] Session tokens handled as secrets (no broadcast)

---

## Testing Strategy

### Unit Tests (Mock)

```python
# tests/test_indy_oauth.py
@pytest.mark.asyncio
async def test_oauth_url_construction():
    """OAuth URL should contain correct client_id and redirect_uri."""
    url = IndyBrowserAdapter._build_oauth_url(
        client_id="test_client",
        redirect_uri="https://app.indy.fr/oauth/callback"
    )
    assert "client_id=test_client" in url
    assert "redirect_uri=" in url

@pytest.mark.asyncio
async def test_oauth_callback_extraction():
    """Extract auth code from callback URL."""
    callback_url = "https://app.indy.fr/oauth/callback?code=abc123&state=xyz"
    code = IndyBrowserAdapter._extract_auth_code(callback_url)
    assert code == "abc123"
```

### Integration Tests (Real)

```python
# tests/integration/test_indy_oauth_real.py
@pytest.mark.integration
def test_oauth_login_real():
    """Real OAuth login to Indy (requires credentials)."""
    adapter = IndyBrowserAdapter(settings)
    adapter.login_via_google_oauth()
    assert adapter._page.url.startswith("https://app.indy.fr/dashboard")

    # Verify session persistence
    assert Path("io/cache/indy_oauth_state.json").exists()
```

---

## Appendix: NetworkLogger for OAuth Discovery

### Step 1: Run NetworkLogger on Indy Login Page

```python
from pathlib import Path
from src.adapters.network_logger import NetworkLogger
from playwright.sync_api import sync_playwright
import time

net_logger = NetworkLogger(output_dir=Path("io/research/indy_oauth"))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Headed to capture human interaction
    page = browser.new_page()
    net_logger.attach(page)

    # Navigate to Indy login
    page.goto("https://app.indy.fr/login")
    page.wait_for_selector("button:has-text('Google')", timeout=5000)

    # Log all network requests up to this point
    logger.info("Network log before click:")
    for key, info in net_logger.get_api_endpoints().items():
        print(f"  {key}")

    # Click "Connexion avec Google"
    page.click("button:has-text('Google')")

    # Wait for redirect to Google OAuth
    page.wait_for_url("https://accounts.google.com/o/oauth2/**", timeout=10000)

    # Log the OAuth URL
    logger.info(f"Redirected to: {page.url}")

    # DON'T log in, just capture the URL
    browser.close()

# Export network log
net_logger.export()

# Read the exported API endpoints
import json
with open("io/research/indy_oauth/api-endpoints.md") as f:
    print(f.read())
```

### Step 2: Extract OAuth Parameters

The exported markdown will show:

```markdown
| Method | URL | Params |
|--------|-----|--------|
| GET | `https://accounts.google.com/o/oauth2/v2/auth` | `client_id=123456.apps.googleusercontent.com&redirect_uri=https://app.indy.fr/oauth/callback&scope=email%20profile&response_type=code&state=...` |
```

Extract:
- `client_id` → Your INDY_OAUTH_CLIENT_ID
- `redirect_uri` → Your callback target
- `scope` → Requested permissions
- `state` → CSRF token (generate fresh each time)

---

## References

- [Google OAuth 2.0 Authorization Code Flow](https://developers.google.com/identity/protocols/oauth2/web-server#httprest)
- [Cloudflare Turnstile Documentation](https://developers.cloudflare.com/turnstile/)
- [Playwright Session Persistence](https://playwright.dev/python/docs/api/class-browsercontext#browser-context-storage-state)
- SAP-Facture `docs/NETWORK_LOGGER.md` — Your network analysis tool

---

## Next Steps

1. **Run NetworkLogger** on Indy login → capture OAuth URL
2. **Extract INDY_OAUTH_CLIENT_ID** from OAuth URL
3. **Implement `_login_via_google_oauth()`** in IndyBrowserAdapter
4. **Test with real credentials** (headed mode first)
5. **Add fallback to session persistence** for resilience
6. **Document OAuth URL parameters** in config

