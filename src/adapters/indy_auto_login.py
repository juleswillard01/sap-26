"""Indy automatic login with 2FA code injection via nodriver.

CDC §3 support: Automates Indy login with 2FA verification code extraction from Gmail.

Uses nodriver (lightweight headless browser automation) to:
1. Navigate to app.indy.fr login page
2. Submit email and password credentials
3. Detect if 2FA verification page appears
4. Extract 2FA code from Gmail (IMAP) if needed
5. Inject code into verification form
6. Wait for dashboard confirmation
7. Retry up to 3 times on failure

Security:
- Credentials validated at init time
- No credentials logged (masked in output)
- Screenshots saved on error for debugging (RGPD-safe)
- Supports async context manager for proper cleanup
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from src.adapters.gmail_reader import GmailReader
    from src.config import Settings

logger = logging.getLogger(__name__)


class IndyAutoLoginNodriver:
    """Automate Indy login with 2FA code injection via nodriver."""

    INDY_BASE_URL: ClassVar[str] = "https://app.indy.fr"
    LOGIN_PATH: ClassVar[str] = "/login"
    DASHBOARD_SELECTOR: ClassVar[str] = (
        "[data-testid='dashboard'], .dashboard, [class*='dashboard']"
    )
    TWO_FA_URL_PATTERNS: ClassVar[list[str]] = [
        "/verification",
        "/verify",
        "/two-fa",
        "2fa",
    ]
    TWO_FA_FORM_SELECTOR: ClassVar[str] = (
        "[name='code'], input[placeholder*='code'], input[placeholder*='Code'], "
        "input[type='text'][name*='verify'], input[type='text'][class*='code']"
    )
    VERIFY_BUTTON_SELECTOR: ClassVar[str] = (
        "button[type='submit'], button:has-text('Vérifier'), "
        "button:has-text('Verify'), button[class*='submit']"
    )

    def __init__(self, settings: Settings, gmail_reader: GmailReader) -> None:
        """Initialize IndyAutoLoginNodriver with credentials and Gmail reader.

        Args:
            settings: Settings instance with indy_email and indy_password.
            gmail_reader: GmailReader instance for 2FA code extraction.

        Raises:
            ValueError: If indy_email or indy_password is empty.
        """
        if not settings.indy_email:
            msg = "indy_email is required"
            raise ValueError(msg)
        if not settings.indy_password:
            msg = "indy_password is required"
            raise ValueError(msg)

        self._settings = settings
        self._gmail_reader = gmail_reader
        self._browser: Any = None
        self._tab: Any = None

    async def login(self) -> bool:
        """Perform Indy login with 2FA support and retry logic.

        Attempts login up to 3 times:
        1. Navigate to Indy login page
        2. Fill email and password
        3. Submit credentials
        4. Detect if 2FA page appears
        5. If 2FA: extract code from Gmail and inject
        6. Wait for dashboard confirmation

        Returns:
            True if login succeeds and dashboard is reached, False otherwise.
        """
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"Indy login attempt {attempt}/{max_retries}")

                # Ensure we have a tab to work with
                if not self._tab and self._browser:
                    self._tab = await self._browser.get_tab()
                elif not self._browser or not self._tab:
                    await self._launch_browser()

                # Navigate to login page
                try:
                    await self._tab.goto(
                        f"{self.INDY_BASE_URL}{self.LOGIN_PATH}",
                        timeout=self._settings.sheets_timeout * 1000,
                    )
                except Exception as e:
                    logger.warning(f"Failed to navigate to login page: {e}")
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue

                # Fill email and password fields with selectors
                try:
                    # Try multiple email selectors
                    email_selectors = [
                        "input[type='email']",
                        "input[name='email']",
                        "input[id*='email']",
                    ]
                    email_filled = False
                    for selector in email_selectors:
                        try:
                            await self._tab.fill(selector, self._settings.indy_email)
                            email_filled = True
                            break
                        except Exception:
                            continue

                    if not email_filled:
                        logger.warning("Could not find email input field")
                        await asyncio.sleep(2 ** (attempt - 1))
                        continue

                    # Try multiple password selectors
                    password_selectors = [
                        "input[type='password']",
                        "input[name='password']",
                        "input[id*='password']",
                    ]
                    password_filled = False
                    for selector in password_selectors:
                        try:
                            await self._tab.fill(selector, self._settings.indy_password)
                            password_filled = True
                            break
                        except Exception:
                            continue

                    if not password_filled:
                        logger.warning("Could not find password input field")
                        await asyncio.sleep(2 ** (attempt - 1))
                        continue

                    # Click submit button
                    submit_selectors = [
                        "button[type='submit']",
                        "button:has-text('Connexion')",
                        "button:has-text('Login')",
                        "button[class*='submit']",
                    ]
                    submit_clicked = False
                    for selector in submit_selectors:
                        try:
                            await self._tab.click(selector)
                            submit_clicked = True
                            break
                        except Exception:
                            continue

                    if not submit_clicked:
                        logger.warning("Could not find submit button")
                        await asyncio.sleep(2 ** (attempt - 1))
                        continue

                    logger.debug("Credentials submitted, waiting for response")

                except Exception as e:
                    logger.warning(f"Error filling credentials: {e}")
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue

                # Wait briefly for login response
                await asyncio.sleep(1)

                # Check for 2FA page and handle accordingly
                is_2fa = await self._detect_2fa_page(self._tab)
                if is_2fa:
                    logger.debug("2FA page detected, extracting code from Gmail")
                    code = self._gmail_reader.get_latest_2fa_code(
                        sender_filter="indy",
                        timeout_sec=self._settings.sheets_timeout,
                    )
                    if not code:
                        logger.warning("2FA code not received within timeout")
                        await asyncio.sleep(2 ** (attempt - 1))  # Backoff
                        continue

                    # Inject 2FA code
                    inject_ok = await self._inject_2fa_code(self._tab, code)
                    # Clear code from memory to prevent accidental logging
                    del code  # type: ignore[name-defined]
                    if not inject_ok:
                        logger.warning("Failed to inject 2FA code")
                        await asyncio.sleep(2 ** (attempt - 1))  # Backoff
                        continue

                    await asyncio.sleep(2)  # Wait for verification

                # Wait for dashboard
                dashboard_ok = await self._wait_for_dashboard(self._tab)
                if dashboard_ok:
                    logger.info("Indy login successful")
                    return True

                logger.warning(f"Dashboard not reached on attempt {attempt}")

            except Exception:
                # Clear any sensitive data from memory before logging exception
                import contextlib

                with contextlib.suppress(NameError):
                    del code  # type: ignore[name-defined]
                logger.warning(
                    f"Indy login failed on attempt {attempt}",
                    exc_info=True,
                )
                await self._screenshot_error(f"login-attempt-{attempt}")

            # Backoff before retry
            if attempt < max_retries:
                await asyncio.sleep(2 ** (attempt - 1))

        logger.error("Indy login failed after all retry attempts")
        return False

    async def _detect_2fa_page(self, tab: Any) -> bool:
        """Detect if 2FA verification page is displayed.

        Checks both URL patterns and form selectors to identify 2FA page.

        Args:
            tab: nodriver tab instance.

        Returns:
            True if 2FA page detected, False otherwise.
        """
        try:
            # Check URL for 2FA patterns
            current_url = await tab.get_current_url()
            if current_url:
                url_lower = current_url.lower()
                for pattern in self.TWO_FA_URL_PATTERNS:
                    if pattern in url_lower:
                        logger.debug("2FA page detected via URL pattern")
                        return True

            # Check for 2FA form selector
            form = await tab.select(self.TWO_FA_FORM_SELECTOR)
            if form:
                logger.debug("2FA page detected via form selector")
                return True

            return False

        except Exception as e:
            logger.debug(f"Error detecting 2FA page: {e}")
            return False

    async def _inject_2fa_code(self, tab: Any, code: str) -> bool:
        """Inject 2FA verification code into form and submit.

        Args:
            tab: nodriver tab instance.
            code: 2FA code (typically 6 digits).

        Returns:
            True if code injected and button clicked successfully, False otherwise.
        """
        try:
            # Find and fill 2FA code input
            code_input = await tab.select(self.TWO_FA_FORM_SELECTOR)
            if not code_input:
                logger.warning("2FA code input field not found")
                return False

            await code_input.send_keys(code)
            logger.debug("2FA code injected")

            # Find and click verify button
            verify_button = await tab.select(self.VERIFY_BUTTON_SELECTOR)
            if not verify_button:
                logger.warning("Verify button not found")
                return False

            await verify_button.click()
            logger.debug("Verify button clicked")

            return True

        except Exception as e:
            logger.warning(f"Error injecting 2FA code: {e}")
            return False

    async def _wait_for_dashboard(self, tab: Any, timeout_sec: int = 10) -> bool:
        """Wait for dashboard element to appear.

        Args:
            tab: nodriver tab instance.
            timeout_sec: Maximum seconds to wait (default 10).

        Returns:
            True if dashboard element found, False on timeout.
        """
        try:
            deadline = asyncio.get_event_loop().time() + timeout_sec
            poll_interval = 0.5

            while asyncio.get_event_loop().time() < deadline:
                dashboard = await tab.select(self.DASHBOARD_SELECTOR)
                if dashboard:
                    logger.debug("Dashboard element found")
                    return True

                await asyncio.sleep(poll_interval)

            logger.warning("Dashboard not found within timeout")
            return False

        except Exception as e:
            logger.debug(f"Error waiting for dashboard: {e}")
            return False

    async def _launch_browser(self) -> None:
        """Launch nodriver browser and initialize tab.

        Raises:
            RuntimeError: If browser launch fails.
        """
        try:
            import nodriver

            self._browser = await nodriver.start()
            self._tab = await self._browser.get_tab()
            logger.debug("nodriver browser launched")

        except ImportError as e:
            msg = "nodriver not installed (required: nodriver>=0.48.1)"
            raise RuntimeError(msg) from e
        except Exception as e:
            logger.error("Failed to launch nodriver browser")
            raise RuntimeError(f"Browser launch failed: {e}") from e

    async def _screenshot_error(self, context: str) -> None:
        """Capture screenshot on error for debugging (RGPD-safe).

        Args:
            context: Error context label (e.g., "login-failed").
        """
        if not self._tab:
            return

        try:
            screenshot_dir = self._settings.export_output_dir
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            from uuid import uuid4

            filename = screenshot_dir / f"indy-{context}-{uuid4()}.png"
            await self._tab.screenshot(path=str(filename))
            logger.info(f"Error screenshot saved: {filename}")

        except Exception as e:
            logger.debug(f"Failed to capture screenshot: {e}")

    async def close(self) -> None:
        """Close browser and cleanup resources.

        Idempotent: safe to call multiple times.
        """
        if self._browser:
            try:
                await self._browser.close()
                logger.debug("nodriver browser closed")
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")
            finally:
                self._browser = None
                self._tab = None

    async def __aenter__(self) -> IndyAutoLoginNodriver:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit (cleanup)."""
        await self.close()
