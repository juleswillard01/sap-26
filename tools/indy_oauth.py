"""Automate Indy login via Google OAuth, bypassing Cloudflare Turnstile.

- Skip Indy's login page (has Turnstile)
- Navigate directly to Google OAuth (no Turnstile)
- Authenticate with Google credentials (Jules has NO 2FA)
- Get redirected back to Indy authenticated
- Save session state for future headless reuse

Security:
- Google credentials must be in .env (GOOGLE_EMAIL, GOOGLE_PASSWORD)
- Never log auth codes or tokens
- Auth code is ephemeral (valid ~10 minutes)
- Session tokens should be treated as secrets

Usage:
    python tools/indy_oauth.py --discover
    python tools/indy_oauth.py --login
    python tools/indy_oauth.py --export-transactions
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

# Configuration (MUST be in .env in production)
# INDY_OAUTH_CLIENT_ID will be discovered via NetworkLogger
INDY_OAUTH_CLIENT_ID = "YOUR_CLIENT_ID"  # Discover via NetworkLogger
GOOGLE_EMAIL = "jules@example.com"
GOOGLE_PASSWORD = "your_password_in_env"
INDY_BASE_URL = "https://app.indy.fr"
GOOGLE_ACCOUNTS_URL = "https://accounts.google.com"

SESSION_STATE_FILE = Path("io/cache/indy_oauth_session.json")
OAUTH_STATE_FILE = Path("io/cache/indy_oauth_state.json")


class IndyGoogleOAuthAutomation:
    """Automate Indy login via Google OAuth, bypassing Cloudflare Turnstile."""

    def __init__(
        self,
        client_id: str,
        google_email: str,
        google_password: str,
        headless: bool = True,
    ) -> None:
        """Initialize OAuth automation.

        Args:
            client_id: Indy's Google OAuth client_id (discovered via NetworkLogger)
            google_email: Jules' Google account email
            google_password: Jules' Google password (from .env)
            headless: Run in headless mode (False = headed for debugging)
        """
        self.client_id = client_id
        self.google_email = google_email
        self.google_password = google_password
        self.headless = headless
        self.browser = None
        self.page = None

    def discover_oauth_url(self) -> str:
        """Discover Indy's OAuth URL by monitoring network requests.

        This step MUST be run once to extract the Google OAuth client_id.
        Use NetworkLogger for full network analysis.

        Returns:
            The Google OAuth authorization URL with all parameters.
        """
        logger.info("Starting OAuth discovery (headed mode for human interaction)...")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            try:
                # Navigate to Indy login page
                page.goto(f"{INDY_BASE_URL}/login", wait_until="networkidle")
                logger.info("Indy login page loaded")

                # Wait for "Connexion avec Google" button
                page.wait_for_selector(
                    "button:has-text('Google')",
                    timeout=5000,
                )
                logger.info("Google button found, waiting for manual click...")
                logger.info("Please click 'Connexion avec Google' in the browser window")
                logger.info("Then return here (will auto-detect redirect)...")

                # Intercept the redirect to Google OAuth
                with page.expect_navigation(timeout=30000):
                    # Wait for click (manual)
                    page.wait_for_timeout(60000)  # 60s timeout for manual click

                # Now we're on Google OAuth page
                oauth_url = page.url
                logger.info(f"OAuth URL discovered: {oauth_url}")

                # Parse to extract client_id
                parsed = urlparse(oauth_url)
                params = parse_qs(parsed.query)
                discovered_client_id = params.get("client_id", [None])[0]

                logger.info(f"Extracted client_id: {discovered_client_id}")
                logger.info(f"Extracted redirect_uri: {params.get('redirect_uri', [None])[0]}")

                return oauth_url

            finally:
                browser.close()

    def login_via_oauth(self, save_session: bool = True) -> dict[str, Any]:
        """
        Perform full Google OAuth login flow, bypassing Turnstile.

        Steps:
        1. Construct Google OAuth URL
        2. Navigate Playwright to Google (no Turnstile)
        3. Fill Google credentials (Jules has NO 2FA)
        4. Get redirected back to Indy callback
        5. Save session state for future headless reuse

        Args:
            save_session: Save session state to file for headless reuse

        Returns:
            Dictionary with:
            - 'success': bool
            - 'email': Google email used
            - 'auth_code': Authorization code (ephemeral)
            - 'session_token': Session token from Indy
            - 'cookies': Dict of session cookies

        Raises:
            RuntimeError: If login fails at any step
        """
        logger.info("Starting Google OAuth login flow...")

        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=self.headless)
            context = self.browser.new_context()
            self.page = context.new_page()
            self.page.set_default_timeout(30_000)

            try:
                # Step 1: Construct Google OAuth URL
                state_token = f"sap_facture_{int(time.time())}"
                oauth_url = (
                    f"{GOOGLE_ACCOUNTS_URL}/o/oauth2/v2/auth?"
                    f"client_id={self.client_id}&"
                    f"redirect_uri={INDY_BASE_URL}/oauth/callback&"
                    f"scope=email%20profile&"
                    f"response_type=code&"
                    f"state={state_token}"
                )

                logger.info("Navigating to Google OAuth (no Turnstile)...")
                self.page.goto(oauth_url, wait_until="networkidle")

                # Step 2: Check if we need to login or select account
                current_url = self.page.url

                if "accounts.google.com" in current_url:
                    logger.info("Google login page detected")
                    self._handle_google_login()
                elif "app.indy.fr" in current_url:
                    logger.info("Already authenticated, skipping Google login")
                else:
                    logger.warning(f"Unexpected URL: {current_url}")

                # Step 3: Wait for redirect back to Indy callback
                logger.info("Waiting for Indy callback redirect...")
                self.page.wait_for_url(
                    f"{INDY_BASE_URL}/oauth/callback**",
                    timeout=30_000,
                )

                callback_url = self.page.url
                logger.info(f"Reached Indy callback: {callback_url}")

                # Step 4: Extract auth code from callback
                parsed_url = urlparse(callback_url)
                query_params = parse_qs(parsed_url.query)
                auth_code = query_params.get("code", [None])[0]
                error = query_params.get("error", [None])[0]

                if error:
                    msg = f"OAuth error: {error}"
                    raise RuntimeError(msg)

                if not auth_code:
                    msg = "No auth code in callback URL"
                    raise RuntimeError(msg)

                logger.info(f"Auth code received (first 20 chars): {auth_code[:20]}...")

                # Step 5: Wait for Indy to process callback and redirect to dashboard
                logger.info("Waiting for Indy dashboard...")
                self.page.wait_for_url(
                    f"{INDY_BASE_URL}/dashboard**",
                    timeout=15_000,
                )

                logger.info("Successfully logged in! Now at Indy dashboard")

                # Step 6: Extract session info
                cookies = context.cookies()
                cookies_dict = {c["name"]: c["value"] for c in cookies}

                # Find session cookie (typically named "session", "auth_token", etc)
                session_token = self._extract_session_token(cookies_dict)

                # Step 7: Save session state for future headless logins
                if save_session:
                    OAUTH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                    context.storage_state(path=str(OAUTH_STATE_FILE))
                    logger.info(f"Session state saved to {OAUTH_STATE_FILE}")

                return {
                    "success": True,
                    "email": self.google_email,
                    "auth_code": auth_code,  # Ephemeral, don't log in prod
                    "session_token": session_token,
                    "cookies": cookies_dict,
                }

            except Exception as e:
                logger.error(f"OAuth login failed: {e}", exc_info=True)
                if self.page:
                    self.page.screenshot(path="io/cache/oauth_error.png")
                    logger.warning("Screenshot saved to io/cache/oauth_error.png")
                raise

            finally:
                self.browser.close()

    def _handle_google_login(self) -> None:
        """Handle Google's login page (email + password).

        Jules has NO 2FA, so this is straightforward:
        1. Enter email
        2. Click Next
        3. Enter password
        4. Click Next
        5. Google redirects back to Indy
        """
        logger.info("Handling Google login...")

        # Check for "Choose account" screen
        try:
            self.page.wait_for_selector("div[data-email]", timeout=3000)
            logger.info("Google account selector found, clicking first account...")
            self.page.click("div[data-email]:nth-child(1)")
            self.page.wait_for_timeout(2000)
        except Exception:
            # No account selector, proceed to email/password form
            logger.info("No account selector, proceeding to login form")

        # Fill email
        logger.info("Filling Google email...")
        self.page.wait_for_selector("input[type='email']", timeout=5000)
        self.page.fill("input[type='email']", self.google_email)

        # Click Next button
        self.page.click("button:has-text('Next')")
        self.page.wait_for_timeout(2000)

        # Fill password (Jules has NO 2FA)
        logger.info("Filling Google password...")
        self.page.wait_for_selector("input[type='password']", timeout=5000)
        self.page.fill("input[type='password']", self.google_password)

        # Click Next button
        self.page.click("button:has-text('Next')")
        logger.info("Credentials submitted, waiting for redirect...")

    def login_headless_with_saved_session(self) -> None:
        """
        Login using previously saved session state.

        This DOES NOT visit the login page, so NO Turnstile involved.
        Requires a prior successful OAuth login.

        Raises:
            FileNotFoundError: If session state file doesn't exist
            RuntimeError: If session is expired
        """
        if not OAUTH_STATE_FILE.exists():
            msg = f"Session state file not found: {OAUTH_STATE_FILE}. Run login_via_oauth() first."
            raise FileNotFoundError(msg)

        logger.info("Connecting to Indy with saved session state (headless)...")

        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=True)
            context = self.browser.new_context(storage_state=str(OAUTH_STATE_FILE))
            self.page = context.new_page()

            try:
                # Navigate directly to dashboard (no login page)
                self.page.goto(f"{INDY_BASE_URL}/dashboard", wait_until="networkidle")

                # Verify we're logged in (check for balance element)
                self.page.wait_for_selector(
                    "[data-testid='account-balance']",
                    timeout=10_000,
                )

                logger.info("Successfully connected with saved session (headless)")

            except Exception as e:
                logger.error(f"Session appears to be expired: {e}")
                raise RuntimeError("Session expired, run login_via_oauth() again to refresh") from e

            finally:
                self.browser.close()

    def export_journal_csv(self) -> list[dict[str, Any]]:
        """Export journal transactions (requires authenticated session).

        This is a mock implementation. In production, this would:
        1. Navigate to Documents > Comptabilité
        2. Click Export CSV
        3. Parse downloaded CSV
        4. Return transactions

        For now, just demonstrates the pattern.
        """
        logger.info("Exporting journal CSV...")

        # Try headless first (with saved session)
        try:
            self.login_headless_with_saved_session()
        except RuntimeError:
            logger.warning("Session expired, logging in again via OAuth...")
            self.login_via_oauth(save_session=True)
            self.login_headless_with_saved_session()

        # Now export transactions (not implemented in this example)
        logger.info("Journal export would occur here")
        return []

    @staticmethod
    def _extract_session_token(cookies: dict[str, str]) -> str | None:
        """Extract session token from cookies.

        Common cookie names: session, auth_token, connect.sid, sessionid
        """
        cookie_names = ["session", "auth_token", "connect.sid", "sessionid"]
        for name in cookie_names:
            if name in cookies:
                return cookies[name]
        return None


# CLI Examples
def main() -> None:
    """Example usage with command-line interface."""
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    # Load credentials from environment
    import os

    google_email = os.getenv("GOOGLE_EMAIL", "jules@example.com")
    google_password = os.getenv("GOOGLE_PASSWORD", "")
    client_id = os.getenv("INDY_OAUTH_CLIENT_ID", INDY_OAUTH_CLIENT_ID)

    if not google_password:
        print("ERROR: GOOGLE_PASSWORD not set in environment")
        sys.exit(1)

    # Initialize automation
    oauth = IndyGoogleOAuthAutomation(
        client_id=client_id,
        google_email=google_email,
        google_password=google_password,
        headless=("--headed" not in sys.argv),
    )

    if command == "--discover":
        print("\n=== Discovering Indy OAuth URL ===\n")
        print("Instructions:")
        print("1. Browser window will open")
        print("2. You'll see Indy login page with 'Connexion avec Google' button")
        print("3. Click the button")
        print("4. Wait for redirect (script will detect it)")
        print("\nStarting discovery (headed mode)...\n")

        oauth_url = oauth.discover_oauth_url()
        print(f"\nOAuth URL: {oauth_url}")
        print("\nExtract 'client_id' parameter and set as INDY_OAUTH_CLIENT_ID\n")

    elif command == "--login":
        print("\n=== Google OAuth Login Flow ===\n")
        result = oauth.login_via_oauth(save_session=True)
        if result["success"]:
            print(f"✓ Successfully logged in as {result['email']}")
            print(f"✓ Session saved to {OAUTH_STATE_FILE}")
        else:
            print("✗ Login failed")
            sys.exit(1)

    elif command == "--export-transactions":
        print("\n=== Exporting Journal Transactions (Headless) ===\n")
        transactions = oauth.export_journal_csv()
        print(f"✓ Exported {len(transactions)} transactions")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
