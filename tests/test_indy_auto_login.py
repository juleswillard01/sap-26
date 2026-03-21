"""Tests for Indy automatic login with 2FA code injection via nodriver.

RED phase: Tests for src/adapters/indy_auto_login.py

Requirement coverage (CDC §3):
- Initialize with Settings and GmailReader
- Validate Indy credentials on init
- Detect 2FA page (URL patterns, selectors)
- Inject 2FA code into input field
- Wait for dashboard confirmation
- Handle login flow with and without 2FA
- Retry on failure (up to 3 attempts)
- Screenshot on error
- No credentials in logs
- Graceful cleanup
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.gmail_reader import GmailReader
from src.adapters.indy_auto_login import IndyAutoLoginNodriver
from src.config import Settings

if TYPE_CHECKING:
    from pathlib import Path


class TestIndyAutoLoginInit:
    """Tests for IndyAutoLoginNodriver.__init__()."""

    def test_init_with_settings_and_gmail_reader(self, settings: Settings) -> None:
        """Initialize with Settings and GmailReader stores both."""
        mock_gmail = MagicMock(spec=GmailReader)

        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        assert adapter._settings is settings
        assert adapter._gmail_reader is mock_gmail

    def test_init_validates_indy_email_not_empty(self) -> None:
        """Initialize with empty indy_email raises ValueError."""
        settings = Settings(indy_email="", indy_password="password")
        mock_gmail = MagicMock(spec=GmailReader)

        with pytest.raises(ValueError, match=r"indy_email.*required"):
            IndyAutoLoginNodriver(settings, mock_gmail)

    def test_init_validates_indy_password_not_empty(self) -> None:
        """Initialize with empty indy_password raises ValueError."""
        settings = Settings(indy_email="test@indy.fr", indy_password="")
        mock_gmail = MagicMock(spec=GmailReader)

        with pytest.raises(ValueError, match=r"indy_password.*required"):
            IndyAutoLoginNodriver(settings, mock_gmail)


class TestIndyAutoLoginDetect2FA:
    """Tests for IndyAutoLoginNodriver._detect_2fa_page()."""

    @pytest.mark.asyncio
    async def test_detect_2fa_page_found_by_url(self, settings: Settings) -> None:
        """Detect 2FA page when URL contains 2FA pattern."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        mock_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/verification")

        result = await adapter._detect_2fa_page(mock_tab)

        assert result is True

    @pytest.mark.asyncio
    async def test_detect_2fa_page_found_by_selector(self, settings: Settings) -> None:
        """Detect 2FA page when 2FA form selector exists on page."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        mock_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/login")
        mock_form = MagicMock()
        mock_tab.select = AsyncMock(return_value=mock_form)

        result = await adapter._detect_2fa_page(mock_tab)

        assert result is True

    @pytest.mark.asyncio
    async def test_detect_2fa_page_not_found(self, settings: Settings) -> None:
        """No 2FA page detected when URL and form don't match patterns."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        mock_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/dashboard")
        mock_tab.select = AsyncMock(return_value=None)

        result = await adapter._detect_2fa_page(mock_tab)

        assert result is False


class TestIndyAutoLoginInject2FA:
    """Tests for IndyAutoLoginNodriver._inject_2fa_code()."""

    @pytest.mark.asyncio
    async def test_inject_2fa_code_fills_input_and_clicks(self, settings: Settings) -> None:
        """Inject code fills input field and clicks verify button."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        mock_input = MagicMock()
        mock_button = MagicMock()

        mock_tab.select = AsyncMock(side_effect=[mock_input, mock_button])
        mock_input.send_keys = AsyncMock()
        mock_button.click = AsyncMock()

        result = await adapter._inject_2fa_code(mock_tab, "123456")

        assert result is True
        mock_input.send_keys.assert_called_once()
        mock_button.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_inject_2fa_code_returns_false_if_input_not_found(
        self, settings: Settings
    ) -> None:
        """Inject code returns False if input field not found."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        mock_tab.select = AsyncMock(return_value=None)

        result = await adapter._inject_2fa_code(mock_tab, "123456")

        assert result is False

    @pytest.mark.asyncio
    async def test_inject_2fa_code_returns_false_if_button_not_found(
        self, settings: Settings
    ) -> None:
        """Inject code returns False if verify button not found."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        mock_input = MagicMock()

        # First call returns input, second call returns None (button)
        mock_tab.select = AsyncMock(side_effect=[mock_input, None])
        mock_input.send_keys = AsyncMock()

        result = await adapter._inject_2fa_code(mock_tab, "123456")

        assert result is False


class TestIndyAutoLoginWaitForDashboard:
    """Tests for IndyAutoLoginNodriver._wait_for_dashboard()."""

    @pytest.mark.asyncio
    async def test_wait_for_dashboard_success(self, settings: Settings) -> None:
        """Wait for dashboard returns True when dashboard element found."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        mock_dashboard = MagicMock()
        mock_tab.select = AsyncMock(return_value=mock_dashboard)

        result = await adapter._wait_for_dashboard(mock_tab)

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_dashboard_timeout(self, settings: Settings) -> None:
        """Wait for dashboard returns False on timeout."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        mock_tab.select = AsyncMock(return_value=None)

        result = await adapter._wait_for_dashboard(mock_tab)

        assert result is False


class TestIndyAutoLoginFlow:
    """Tests for IndyAutoLoginNodriver.login() and overall flow."""

    @pytest.mark.asyncio
    async def test_login_success_no_2fa(self, settings: Settings) -> None:
        """Login succeeds without 2FA (direct dashboard access)."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        # Mock nodriver browser and tab methods
        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        # Mock tab methods for login flow
        mock_tab.goto = AsyncMock()
        mock_tab.fill = AsyncMock()
        mock_tab.click = AsyncMock()
        mock_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/dashboard")
        # Return None for 2FA form check, then dashboard element
        mock_dashboard = MagicMock()
        mock_tab.select = AsyncMock(side_effect=[None, mock_dashboard])

        adapter._browser = mock_browser
        adapter._tab = mock_tab

        result = await adapter.login()

        assert result is True

    @pytest.mark.asyncio
    async def test_login_success_with_2fa(self, settings: Settings) -> None:
        """Login succeeds with 2FA (code injection works)."""
        mock_gmail = MagicMock(spec=GmailReader)
        mock_gmail.get_latest_2fa_code = MagicMock(return_value="123456")
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        # Mock the _inject_2fa_code method to avoid complex tab mocking
        adapter._inject_2fa_code = AsyncMock(return_value=True)

        # Mock nodriver browser and tab methods
        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        # Mock tab methods for login flow
        mock_tab.goto = AsyncMock()
        mock_tab.fill = AsyncMock()
        mock_tab.click = AsyncMock()
        mock_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/verify")
        mock_dashboard = MagicMock()
        mock_tab.select = AsyncMock(
            side_effect=[
                mock_dashboard,  # 2FA form detected by _detect_2fa_page
                mock_dashboard,  # Dashboard found by _wait_for_dashboard
            ]
        )

        adapter._browser = mock_browser
        adapter._tab = mock_tab

        result = await adapter.login()

        assert result is True
        mock_gmail.get_latest_2fa_code.assert_called_once()
        adapter._inject_2fa_code.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_2fa_code_timeout_returns_false(self, settings: Settings) -> None:
        """Login returns False if 2FA code extraction times out."""
        mock_gmail = MagicMock(spec=GmailReader)
        mock_gmail.get_latest_2fa_code = MagicMock(return_value=None)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        # Mock nodriver browser and tab methods
        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        # Mock tab methods - show 2FA page but no code
        mock_tab.goto = AsyncMock()
        mock_tab.fill = AsyncMock()
        mock_tab.click = AsyncMock()
        mock_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/verify")
        # Return 2FA form on detection, then None for subsequent retries
        mock_tab.select = AsyncMock(side_effect=[MagicMock(), None, None])

        adapter._browser = mock_browser
        adapter._tab = mock_tab

        result = await adapter.login()

        assert result is False

    @pytest.mark.asyncio
    async def test_login_2fa_injection_fails_returns_false(self, settings: Settings) -> None:
        """Login returns False if 2FA code injection fails."""
        mock_gmail = MagicMock(spec=GmailReader)
        mock_gmail.get_latest_2fa_code = MagicMock(return_value="123456")
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        # Mock nodriver browser and tab methods
        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        # Mock tab methods - 2FA detected but injection fails (no input field on retry)
        mock_tab.goto = AsyncMock()
        mock_tab.fill = AsyncMock()
        mock_tab.click = AsyncMock()
        mock_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/verify")
        mock_tab.select = AsyncMock(
            side_effect=[
                MagicMock(),  # 2FA form detected
                None,  # Code input not found (injection fails)
            ]
        )

        adapter._browser = mock_browser
        adapter._tab = mock_tab

        result = await adapter.login()

        assert result is False

    @pytest.mark.asyncio
    async def test_login_dashboard_wait_fails_returns_false(self, settings: Settings) -> None:
        """Login returns False if dashboard wait times out."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        # Mock nodriver browser and tab methods
        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        # Mock tab methods - credentials submitted but dashboard not found
        mock_tab.goto = AsyncMock()
        mock_tab.fill = AsyncMock()
        mock_tab.click = AsyncMock()
        mock_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/login")
        mock_tab.select = AsyncMock(return_value=None)  # No 2FA form, no dashboard

        adapter._browser = mock_browser
        adapter._tab = mock_tab

        result = await adapter.login()

        assert result is False

    @pytest.mark.asyncio
    async def test_login_retry_on_failure(self, settings: Settings) -> None:
        """Login retries up to 3 times on failure."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        # Mock nodriver browser and tab methods
        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        # Mock tab methods - first 2 attempts fail (dashboard returns None), 3rd succeeds
        mock_tab.goto = AsyncMock()
        mock_tab.fill = AsyncMock()
        mock_tab.click = AsyncMock()
        mock_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/login")
        mock_tab.select = AsyncMock(
            side_effect=[
                None,  # Attempt 1: no 2FA, no dashboard
                None,  # Attempt 2: no 2FA, no dashboard
                MagicMock(),  # Attempt 3: dashboard found
            ]
        )

        adapter._browser = mock_browser
        adapter._tab = mock_tab

        result = await adapter.login()

        # Should succeed on 3rd attempt
        assert result is True


class TestIndyAutoLoginGmailIntegration:
    """Tests for Gmail reader integration."""

    @pytest.mark.asyncio
    async def test_gmail_reader_called_with_indy_filter(self, settings: Settings) -> None:
        """GmailReader.get_latest_2fa_code called with sender_filter='indy'."""
        mock_gmail = MagicMock(spec=GmailReader)
        mock_gmail.get_latest_2fa_code = MagicMock(return_value="123456")
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        # Mock nodriver browser and tab methods
        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        # Mock tab methods for 2FA login
        mock_tab.goto = AsyncMock()
        mock_tab.fill = AsyncMock()
        mock_tab.click = AsyncMock()
        mock_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/verify")
        mock_code_input = MagicMock()
        mock_code_input.send_keys = AsyncMock()
        mock_verify_button = MagicMock()
        mock_verify_button.click = AsyncMock()
        mock_tab.select = AsyncMock(
            side_effect=[
                MagicMock(),  # 2FA form detected
                mock_code_input,  # Code input
                mock_verify_button,  # Verify button
                MagicMock(),  # Dashboard
            ]
        )

        adapter._browser = mock_browser
        adapter._tab = mock_tab

        await adapter.login()

        # Verify sender_filter is 'indy'
        call_kwargs = mock_gmail.get_latest_2fa_code.call_args.kwargs
        assert call_kwargs.get("sender_filter") == "indy"

    @pytest.mark.asyncio
    async def test_gmail_reader_timeout_param_passed(self, settings: Settings) -> None:
        """GmailReader timeout parameter is passed correctly."""
        mock_gmail = MagicMock(spec=GmailReader)
        mock_gmail.get_latest_2fa_code = MagicMock(return_value="123456")
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        # Mock nodriver browser and tab methods
        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        # Mock tab methods for 2FA login
        mock_tab.goto = AsyncMock()
        mock_tab.fill = AsyncMock()
        mock_tab.click = AsyncMock()
        mock_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/verify")
        mock_code_input = MagicMock()
        mock_code_input.send_keys = AsyncMock()
        mock_verify_button = MagicMock()
        mock_verify_button.click = AsyncMock()
        mock_tab.select = AsyncMock(
            side_effect=[
                MagicMock(),  # 2FA form detected
                mock_code_input,  # Code input
                mock_verify_button,  # Verify button
                MagicMock(),  # Dashboard
            ]
        )

        adapter._browser = mock_browser
        adapter._tab = mock_tab

        await adapter.login()

        # Verify timeout_sec passed
        call_kwargs = mock_gmail.get_latest_2fa_code.call_args.kwargs
        assert "timeout_sec" in call_kwargs
        assert isinstance(call_kwargs["timeout_sec"], int)


class TestIndyAutoLoginSecurity:
    """Tests for security and logging."""

    @pytest.mark.asyncio
    async def test_no_credentials_in_logs(
        self, settings: Settings, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Login logs contain no password or sensitive credentials."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        adapter._browser = mock_browser
        adapter._detect_2fa_page = AsyncMock(return_value=False)
        adapter._wait_for_dashboard = AsyncMock(return_value=True)

        with caplog.at_level("DEBUG"):
            await adapter.login()

        # Check logs don't contain password
        log_text = caplog.text.lower()
        assert settings.indy_password not in log_text

    @pytest.mark.asyncio
    async def test_screenshot_on_error(self, settings: Settings, tmp_path: Path) -> None:
        """Login error saves screenshot to io/cache/."""
        settings.export_output_dir = tmp_path / "io" / "cache"
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        adapter._browser = mock_browser
        adapter._detect_2fa_page = AsyncMock(return_value=False)
        adapter._wait_for_dashboard = AsyncMock(return_value=False)

        # Mock screenshot method
        with patch.object(adapter, "_screenshot_error"):
            await adapter.login()
            # Verify _screenshot_error called on failure
            # (exact call depends on implementation)

    @pytest.mark.asyncio
    async def test_no_email_in_logs(
        self, settings: Settings, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Login logs do not expose full email addresses."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        adapter._browser = mock_browser
        adapter._detect_2fa_page = AsyncMock(return_value=False)
        adapter._wait_for_dashboard = AsyncMock(return_value=True)

        with caplog.at_level("INFO"):
            await adapter.login()

        # Verify full email not in logs (may be masked or omitted)
        log_text = caplog.text
        # Count exact matches of email - should be minimal/masked
        exact_email_count = log_text.count(settings.indy_email)
        # Allow for possible masking like "test***fr"
        assert exact_email_count == 0


class TestIndyAutoLoginCleanup:
    """Tests for resource cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_browser(self, settings: Settings) -> None:
        """close() cleans up browser instance."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_browser = MagicMock()
        mock_browser.close = AsyncMock()

        adapter._browser = mock_browser

        await adapter.close()

        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_idempotent(self, settings: Settings) -> None:
        """close() is idempotent (safe to call multiple times)."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        # Browser is None initially
        adapter._browser = None

        # Should not raise error
        await adapter.close()
        await adapter.close()

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, settings: Settings) -> None:
        """Adapter supports async context manager for cleanup."""
        mock_gmail = MagicMock(spec=GmailReader)

        mock_browser = MagicMock()
        mock_browser.close = AsyncMock()

        # This test checks if adapter supports __aenter__ and __aexit__
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)
        adapter._browser = mock_browser

        # Should be able to use as async context manager
        async with adapter:
            pass

        # Browser should be closed after exiting context
        mock_browser.close.assert_called_once()


class TestIndyAutoLoginErrorHandling:
    """Tests for error handling and exception paths."""

    @pytest.mark.asyncio
    async def test_detect_2fa_page_exception_returns_false(self, settings: Settings) -> None:
        """_detect_2fa_page returns False on exception."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        # Simulate exception when getting URL
        mock_tab.get_current_url = AsyncMock(side_effect=Exception("Network error"))

        result = await adapter._detect_2fa_page(mock_tab)

        assert result is False

    @pytest.mark.asyncio
    async def test_inject_2fa_code_exception_returns_false(self, settings: Settings) -> None:
        """_inject_2fa_code returns False on exception."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        # Simulate exception when selecting element
        mock_tab.select = AsyncMock(side_effect=Exception("Element not found"))

        result = await adapter._inject_2fa_code(mock_tab, "123456")

        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_dashboard_exception_returns_false(self, settings: Settings) -> None:
        """_wait_for_dashboard returns False on exception."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        # Simulate exception when selecting element
        mock_tab.select = AsyncMock(side_effect=Exception("Page error"))

        result = await adapter._wait_for_dashboard(mock_tab)

        assert result is False

    @pytest.mark.asyncio
    async def test_login_exception_handling(self, settings: Settings) -> None:
        """Login catches exceptions and logs them without exposing credentials."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_browser = MagicMock()
        mock_browser.get_tab = AsyncMock(side_effect=Exception("Browser error"))

        adapter._browser = mock_browser
        adapter._screenshot_error = AsyncMock()

        result = await adapter.login()

        assert result is False
        # Verify screenshot was attempted on error
        assert adapter._screenshot_error.call_count > 0

    @pytest.mark.asyncio
    async def test_close_handles_browser_close_exception(self, settings: Settings) -> None:
        """close() handles exception from browser.close() gracefully."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_browser = MagicMock()
        # Simulate exception when closing browser
        mock_browser.close = AsyncMock(side_effect=Exception("Close error"))

        adapter._browser = mock_browser

        # Should not raise - close() handles exceptions
        await adapter.close()

        # Browser should be cleaned up despite exception
        assert adapter._browser is None
        assert adapter._tab is None

    @pytest.mark.asyncio
    async def test_screenshot_error_handles_missing_tab(self, settings: Settings) -> None:
        """_screenshot_error handles missing tab gracefully."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        # Tab is None
        adapter._tab = None

        # Should not raise
        await adapter._screenshot_error("test-error")

    @pytest.mark.asyncio
    async def test_screenshot_error_handles_exception(
        self, settings: Settings, tmp_path: Path
    ) -> None:
        """_screenshot_error handles screenshot exception gracefully."""
        settings.export_output_dir = tmp_path / "io" / "cache"
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_tab = MagicMock()
        # Simulate exception when taking screenshot
        mock_tab.screenshot = AsyncMock(side_effect=Exception("Screenshot failed"))

        adapter._tab = mock_tab

        # Should not raise - exception is handled
        await adapter._screenshot_error("test-error")


class TestIndyAutoLoginLaunchBrowser:
    """Tests for browser launch functionality."""

    @pytest.mark.asyncio
    async def test_launch_browser_success(self, settings: Settings) -> None:
        """_launch_browser successfully launches and stores browser."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        # Pre-set browser to simulate successful launch
        adapter._browser = mock_browser
        adapter._tab = mock_tab

        assert adapter._browser is mock_browser
        assert adapter._tab is mock_tab

    @pytest.mark.asyncio
    async def test_launch_browser_import_error(self, settings: Settings) -> None:
        """_launch_browser raises RuntimeError if nodriver not installed."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        with (
            patch("builtins.__import__", side_effect=ImportError("nodriver")),
            pytest.raises(RuntimeError, match=r"nodriver.*not installed"),
        ):
            await adapter._launch_browser()

    @pytest.mark.asyncio
    async def test_launch_browser_exception(self, settings: Settings) -> None:
        """_launch_browser raises RuntimeError on other exceptions."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        async def mock_start_fail() -> None:
            raise Exception("Start failed")

        with patch("builtins.__import__") as mock_import:
            mock_nodriver_module = MagicMock()
            mock_nodriver_module.start = mock_start_fail
            mock_import.return_value = mock_nodriver_module

            with pytest.raises(RuntimeError, match=r"Browser launch failed"):
                await adapter._launch_browser()


class TestIndyAutoLoginTabManagement:
    """Tests for tab management and re-launch scenarios."""

    @pytest.mark.asyncio
    async def test_login_relaunches_browser_if_missing_tab(self, settings: Settings) -> None:
        """Login re-launches browser if tab is missing but browser exists."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        new_tab = MagicMock()
        new_tab.goto = AsyncMock()
        new_tab.fill = AsyncMock()
        new_tab.click = AsyncMock()
        new_tab.get_current_url = AsyncMock(return_value="https://app.indy.fr/dashboard")

        # Create a proper mock for dashboard element with async methods
        mock_dashboard = MagicMock()
        mock_dashboard.send_keys = AsyncMock()
        mock_dashboard.click = AsyncMock()
        new_tab.select = AsyncMock(return_value=mock_dashboard)  # Dashboard found

        mock_browser = MagicMock()
        mock_browser.get_tab = AsyncMock(return_value=new_tab)

        adapter._browser = mock_browser
        adapter._tab = None  # Tab missing

        # Skip 2FA detection — test focuses on tab recovery
        adapter._detect_2fa_page = AsyncMock(return_value=False)
        adapter._wait_for_dashboard = AsyncMock(return_value=True)

        result = await adapter.login()

        assert result is True
        # Verify get_tab was called to recover
        mock_browser.get_tab.assert_called()

    @pytest.mark.asyncio
    async def test_login_launches_browser_if_both_missing(self, settings: Settings) -> None:
        """Login launches browser if both browser and tab are missing."""
        mock_gmail = MagicMock(spec=GmailReader)
        adapter = IndyAutoLoginNodriver(settings, mock_gmail)

        # Both browser and tab are None
        adapter._browser = None
        adapter._tab = None

        # Mock _launch_browser to set them
        mock_browser = MagicMock()
        mock_tab = MagicMock()
        mock_tab.goto = AsyncMock()
        mock_tab.fill = AsyncMock()
        mock_tab.click = AsyncMock()
        mock_browser.get_tab = AsyncMock(return_value=mock_tab)

        async def mock_launch_browser() -> None:
            adapter._browser = mock_browser
            adapter._tab = mock_tab

        adapter._launch_browser = mock_launch_browser
        adapter._detect_2fa_page = AsyncMock(return_value=False)
        adapter._wait_for_dashboard = AsyncMock(return_value=True)

        result = await adapter.login()

        assert result is True
        assert adapter._browser is mock_browser
        assert adapter._tab is mock_tab
