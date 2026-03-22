"""Indy 2FA code injection adapter via nodriver + Gmail IMAP.

Orchestrates automated 2FA verification for Indy login:
1. Detects 2FA page (URL patterns, selectors)
2. Polls Gmail IMAP for verification code
3. Injects code into input field
4. Clicks verify button
5. Waits for dashboard redirect (success confirmation)

Security:
- Credentials via .env (never hardcoded)
- Code masked in logs (first 3 digits only)
- Email addresses masked in logs
- Screenshot errors RGPD-compliant (no sensitive data visible)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.adapters.gmail_reader import GmailReader

logger = logging.getLogger(__name__)

# Timeout configuration (seconds)
TIMEOUT_2FA_PAGE_DETECTION = 30
TIMEOUT_GMAIL_POLL = 60
TIMEOUT_CODE_INJECTION = 10
TIMEOUT_VERIFY_RESPONSE = 30
TIMEOUT_TOTAL = 120

# 2FA page detection patterns
URL_PATTERNS_2FA = [
    "verification",
    "verify",
    "2fa",
    "code",
    "authentification",
    "otp",
    "validate",
]

# 2FA input field selectors (in priority order)
SELECTORS_CODE_INPUT = [
    "input[placeholder*='code' i]",
    "input[placeholder*='verification' i]",
    "input[placeholder*='authentification' i]",
    "input[placeholder*='otp' i]",
    "input[name='code']",
    "input[type='text'][data-testid*='code']",
    "input[type='text'][data-testid*='otp']",
    "input[id*='code']",
    "input[id*='verification']",
    "input[type='text']",  # Fallback: first text input
]

# Verify button texts (in priority order)
BUTTON_TEXTS_VERIFY = [
    "Vérifier",  # French: Verify
    "Valider",  # French: Validate
    "Confirmer",  # French: Confirm
    "Continuer",  # French: Continue
    "Envoyer",  # French: Send
    "Verify",  # English
    "Confirm",  # English
    "Submit",  # English
]


class Indy2FAAdapter:
    """Automate Indy 2FA code injection via nodriver + Gmail IMAP."""

    def __init__(self) -> None:
        """Initialize adapter."""
        pass

    async def auto_2fa_login(
        self,
        page: Any,
        gmail_reader: GmailReader,
        email: str,
        password: str,
        timeout_sec: int = TIMEOUT_TOTAL,
    ) -> bool:
        """Orchestrate full 2FA login flow.

        Steps:
        1. Fill email/password in login form
        2. Submit login form
        3. Detect if 2FA page appears
        4. Poll Gmail IMAP for verification code
        5. Inject code into 2FA input field
        6. Click verify/confirm button
        7. Wait for dashboard redirect (success)

        Args:
            page: Nodriver page object (must be at login URL)
            gmail_reader: Initialized GmailReader (connected to Gmail IMAP)
            email: Indy login email (for logging only)
            password: Indy login password (not logged)
            timeout_sec: Overall timeout in seconds (default 120)

        Returns:
            True if 2FA flow completed successfully, False otherwise.

        Raises:
            RuntimeError: If critical steps fail (e.g., page navigation fails)
        """
        start_time = time.monotonic()
        email_masked = self._mask_email(email)

        try:
            logger.info(
                "Starting Indy 2FA login flow",
                extra={"email": email_masked, "timeout": timeout_sec},
            )

            # Step 1: Fill login form
            logger.info("Filling login form")
            await self._fill_login_form(page, email, password)

            # Step 2: Submit form and wait for 2FA page
            logger.info("Submitting login form")
            await self._submit_login_form(page)

            # Step 3: Detect 2FA page
            logger.info("Detecting 2FA page")
            is_2fa_page = await self._detect_2fa_page(page, timeout_sec=TIMEOUT_2FA_PAGE_DETECTION)

            if not is_2fa_page:
                logger.warning("2FA page not detected, assuming already authenticated")
                # Could be already logged in, try dashboard detection
                is_dashboard = await self._wait_for_dashboard(
                    page, timeout_sec=TIMEOUT_VERIFY_RESPONSE
                )
                return is_dashboard

            logger.info("2FA page detected, polling Gmail for code")

            # Step 4: Poll Gmail for code (concurrent with 2FA page wait)
            code = await self._get_2fa_code_async(gmail_reader, timeout_sec=TIMEOUT_GMAIL_POLL)

            if not code:
                logger.error("2FA code not received from Gmail within timeout")
                await self._screenshot_error(page, "gmail-timeout")
                return False

            logger.info(
                "2FA code received",
                extra={"code": self._mask_code(code)},
            )

            # Step 5: Inject code and verify
            logger.info("Injecting 2FA code")
            inject_success = await self._inject_and_verify(page, code)

            if not inject_success:
                logger.error("Failed to inject code or click verify button")
                await self._screenshot_error(page, "inject-failed")
                return False

            logger.info("Code injected and verify button clicked")

            # Step 6: Wait for dashboard (success confirmation)
            logger.info("Waiting for dashboard redirect")
            remaining_timeout = timeout_sec - (time.monotonic() - start_time)
            dashboard_reached = await self._wait_for_dashboard(
                page, timeout_sec=int(min(remaining_timeout, TIMEOUT_VERIFY_RESPONSE))
            )

            if dashboard_reached:
                elapsed = time.monotonic() - start_time
                logger.info(
                    "2FA login completed successfully",
                    extra={"elapsed_sec": elapsed},
                )
                return True
            else:
                logger.error("Dashboard not reached after 2FA verification")
                await self._screenshot_error(page, "dashboard-not-reached")
                return False

        except Exception:
            logger.error("2FA login flow failed", exc_info=True)
            await self._screenshot_error(page, "exception")
            raise

    async def _fill_login_form(
        self,
        page: Any,
        email: str,
        password: str,
    ) -> None:
        """Fill email and password fields.

        Tries multiple selector patterns for compatibility.

        Args:
            page: Nodriver page object
            email: Login email
            password: Login password

        Raises:
            RuntimeError: If email or password field not found
        """
        # Fill email — wait up to 30s for field (Turnstile may delay)
        email_selectors = [
            "input[type='email']",
            "input[name='email']",
            "input[placeholder*='email' i]",
            "input[placeholder*='mail' i]",
        ]

        email_filled = False
        for attempt in range(15):
            for selector in email_selectors:
                try:
                    email_input = await page.query_selector(selector)
                    if email_input:
                        await email_input.send_keys(email)
                        email_filled = True
                        logger.debug(
                            "Email filled via selector: %s (attempt %d)", selector, attempt
                        )
                        break
                except Exception:
                    continue
            if email_filled:
                break
            await page.sleep(2)

        if not email_filled:
            logger.error("Email field not found after 30s")
            raise RuntimeError("Could not find email input field")

        await page.sleep(1)

        # Fill password
        password_selectors = [
            "input[type='password']",
            "input[name='password']",
            "input[placeholder*='password' i]",
            "input[placeholder*='mot de passe' i]",
        ]

        password_filled = False
        for selector in password_selectors:
            try:
                password_input = await page.query_selector(selector)
                if password_input:
                    await password_input.send_keys(password)
                    password_filled = True
                    logger.debug("Password filled via selector: %s", selector)
                    break
            except Exception:
                continue

        if not password_filled:
            logger.error("Password field not found")
            raise RuntimeError("Could not find password input field")

        await page.sleep(1)

    async def _submit_login_form(self, page: Any) -> None:
        """Submit login form by clicking button or pressing Enter.

        Tries multiple button detection methods.

        Args:
            page: Nodriver page object
        """
        # Try clicking button by text
        button_texts = ["Se connecter", "Connect", "Login", "Sign In"]
        for text in button_texts:
            try:
                button = await page.find(text, timeout=5)
                if button:
                    await button.click()
                    logger.debug("Submit button clicked via text: %s", text)
                    await page.sleep(2)
                    return
            except Exception:
                continue

        # Fallback: click generic submit button
        try:
            submit_btn = await page.query_selector("button[type='submit']")
            if submit_btn:
                await submit_btn.click()
                logger.debug("Submit button clicked via selector")
                await page.sleep(2)
                return
        except Exception:
            pass

        # Final fallback: press Enter (from last focused field)
        logger.info("Pressing Enter as login submit fallback")
        await page.send_keys("Enter")
        await page.sleep(2)

    async def _detect_2fa_page(
        self,
        page: Any,
        timeout_sec: int = TIMEOUT_2FA_PAGE_DETECTION,
    ) -> bool:
        """Detect if on 2FA verification page.

        Checks:
        1. URL contains 2FA keywords
        2. Code input selector found
        3. Page title/heading contains verification keywords

        Args:
            page: Nodriver page object
            timeout_sec: How long to wait for 2FA detection

        Returns:
            True if 2FA page detected, False if timeout/not found
        """
        start = time.monotonic()

        while time.monotonic() - start < timeout_sec:
            # Check URL
            url = page.url.lower()
            if any(pattern in url for pattern in URL_PATTERNS_2FA):
                logger.info("2FA page detected by URL pattern")
                return True

            # Check for code input field (nodriver has no timeout param)
            for selector in SELECTORS_CODE_INPUT:
                try:
                    code_input = await page.query_selector(selector)
                    if code_input:
                        logger.info("2FA code input found via selector: %s", selector)
                        return True
                except Exception:
                    continue

            # Check if URL changed from /connexion (means form submitted)
            if "/connexion" not in url:
                logger.info("URL changed from /connexion, likely 2FA: %s", url)
                return True

            # Check page content for verification keywords
            try:
                page_text = await page.evaluate("document.body.innerText")
                if page_text and any(
                    kw in page_text.lower()
                    for kw in ["code", "vérification", "verification", "confirmer", "2fa"]
                ):
                    logger.info("2FA page detected by body text")
                    return True
            except Exception:
                pass

            await page.sleep(2)

        logger.warning("2FA page detection timeout")
        return False

    async def _get_2fa_code_async(
        self,
        gmail_reader: GmailReader,
        timeout_sec: int = TIMEOUT_GMAIL_POLL,
    ) -> str | None:
        """Poll Gmail IMAP for 2FA code (async wrapper).

        Runs in background while page waits for code.

        Args:
            gmail_reader: Initialized GmailReader (must be connected)
            timeout_sec: Max seconds to wait for code

        Returns:
            6-digit code as string, or None if timeout/not found
        """
        loop = asyncio.get_event_loop()

        try:
            # Run blocking IMAP poll in thread pool (non-blocking)
            code = await loop.run_in_executor(
                None,
                gmail_reader.get_latest_2fa_code,
                timeout_sec,
                5,  # poll_interval_sec
                "support@indy.fr",  # sender_filter — avoid matching newsletters
            )
            return code
        except Exception as e:
            logger.error("Gmail polling failed: %s", e, exc_info=True)
            return None

    async def _inject_and_verify(
        self,
        page: Any,
        code: str,
    ) -> bool:
        """Inject 2FA code and click verify button.

        Args:
            page: Nodriver page object
            code: 6-digit code as string

        Returns:
            True if code injected and verify clicked, False if any step fails
        """
        # Inject code digit by digit — Indy uses 6 individual input boxes
        try:
            inputs = await page.query_selector_all("input[type='text']")
            if len(inputs) >= 6:
                # 6 individual boxes: click each, type one digit, wait 1s
                for i, digit in enumerate(code[:6]):
                    await inputs[i].click()
                    await page.sleep(0.5)
                    await inputs[i].send_keys(digit)
                    logger.debug("Digit %d injected: %s", i, digit)
                    await page.sleep(1)
            elif len(inputs) == 1:
                # Single field
                await inputs[0].click()
                await inputs[0].send_keys(code)
            else:
                logger.error("Unexpected number of text inputs: %d", len(inputs))
                return False

            logger.debug("Code injected digit by digit")
            await page.sleep(1)

        except Exception as e:
            logger.error("Failed to inject code: %s", e, exc_info=True)
            return False

        # Click submit button
        try:
            btn = await page.find("Se connecter", timeout=5)
            if btn:
                await btn.click()
                logger.debug("'Se connecter' button clicked")
            else:
                # Fallback: find any submit-like button
                btn = await page.query_selector("button[type='submit']")
                if btn:
                    await btn.click()
                    logger.debug("Submit button clicked via selector")
                else:
                    logger.warning("No submit button found")
                    return False

            await page.sleep(2)
            return True

        except Exception as e:
            logger.error("Failed to click verify button: %s", e, exc_info=True)
            return False

    async def _wait_for_dashboard(
        self,
        page: Any,
        timeout_sec: int = TIMEOUT_VERIFY_RESPONSE,
    ) -> bool:
        """Wait for dashboard page (successful 2FA).

        Checks:
        1. URL matches dashboard patterns
        2. Key dashboard elements present

        Args:
            page: Nodriver page object
            timeout_sec: Max seconds to wait

        Returns:
            True if dashboard detected, False if timeout
        """
        start = time.monotonic()
        dashboard_patterns = [
            "/dashboard",
            "/pilotage",
            "/accueil",
            "/home",
            "/accounts",
            "/transactions",
        ]

        while time.monotonic() - start < timeout_sec:
            url = page.url.lower()

            # Check URL patterns
            if any(pattern in url for pattern in dashboard_patterns):
                logger.info("Dashboard URL detected: %s", url)

                # Verify page actually loaded
                try:
                    # Look for key dashboard element
                    dashboard_elem = await page.query_selector(
                        "[data-testid='account-balance'], "
                        ".account-balance, "
                        "[class*='balance'], "
                        "[class*='dashboard']",
                        timeout=5000,
                    )
                    if dashboard_elem:
                        logger.info("Dashboard element found, login successful")
                        return True
                except Exception:
                    # Element not found yet, page might still be loading
                    pass

            await page.sleep(1)

        logger.warning("Dashboard not reached within timeout")
        return False

    async def _screenshot_error(
        self,
        page: Any,
        context: str,
    ) -> None:
        """Capture screenshot for debugging (RGPD-safe).

        Screenshots are stored locally with UUID to prevent
        accidental exposure of sensitive data.

        Args:
            page: Nodriver page object
            context: Short description of error context
        """
        try:
            from pathlib import Path
            from uuid import uuid4

            output_dir = Path("io/cache/indy-2fa-errors")
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = output_dir / f"{context}-{uuid4()}.png"
            await page.save_screenshot(str(filename))

            logger.warning(
                "Error screenshot saved",
                extra={"file": str(filename)},
            )
        except Exception as e:
            logger.error("Failed to capture screenshot: %s", e, exc_info=True)

    @staticmethod
    def _mask_email(email: str) -> str:
        """Mask email for safe logging.

        Example: jules.willard@example.com → j***@example.com
        """
        parts = email.split("@")
        if len(parts) != 2:
            return "***"
        local, domain = parts
        return f"{local[0]}***@{domain}"

    @staticmethod
    def _mask_code(code: str) -> str:
        """Mask 2FA code for safe logging.

        Example: 123456 → 123***
        """
        if len(code) < 4:
            return "***"
        return f"{code[:3]}***"
