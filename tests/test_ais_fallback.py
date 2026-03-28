"""Tests for AIS Playwright fallback adapter and REST-to-Playwright facade.

Tests:
- AISPlaywrightFallback has the same interface as AISAPIAdapter
- connect() launches headless Chromium, logs in via form
- get_clients() parses the clients table
- get_invoices() / get_invoice_statuses() parse demandes table with status badges
- get_invoice_status() returns single status
- get_pending_reminders() filters EN_ATTENTE > N hours
- Screenshot on error saved to io/cache/ais_error_*.png
- Sensitive data NOT in screenshot filename
- close() cleans up browser resources
- AISAdapterWithFallback tries REST first, falls back to Playwright
- Forbidden operations raise NotImplementedError
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.adapters.ais_playwright_fallback import (
    AIS_BASE_URL,
    AISAdapterWithFallback,
    AISPlaywrightFallback,
    AISSelectors,
)
from src.config import Settings

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture
def ais_settings() -> Settings:
    """Settings with AIS credentials for testing."""
    return Settings(
        ais_email="jules@test.fr",
        ais_password="secret_ais_123",
    )


@pytest.fixture
def mock_page() -> AsyncMock:
    """Mock Playwright page with async methods."""
    page = AsyncMock()
    page.screenshot = AsyncMock()
    page.goto = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=[])
    page.evaluate = AsyncMock(return_value=[])
    page.close = AsyncMock()
    return page


@pytest.fixture
def mock_browser(mock_page: AsyncMock) -> AsyncMock:
    """Mock Playwright browser."""
    browser = AsyncMock()
    context = AsyncMock()
    browser.new_context = AsyncMock(return_value=context)
    context.new_page = AsyncMock(return_value=mock_page)
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def fallback(ais_settings: Settings) -> AISPlaywrightFallback:
    """AISPlaywrightFallback instance for testing."""
    return AISPlaywrightFallback(ais_settings)


# ──────────────────────────────────────────────
# Selectors Mapping
# ──────────────────────────────────────────────


class TestAISSelectors:
    """Verify AIS CSS selectors are defined and mapped."""

    def test_login_selectors_defined(self) -> None:
        """Login form selectors must be defined."""
        assert AISSelectors.LOGIN_EMAIL == "input[name='email']"
        assert AISSelectors.LOGIN_PASSWORD == "input[name='password']"
        assert AISSelectors.LOGIN_SUBMIT == "button[type='submit']"

    def test_navigation_selectors_defined(self) -> None:
        """Navigation selectors for clients and demandes pages."""
        assert isinstance(AISSelectors.NAV_CLIENTS, str)
        assert isinstance(AISSelectors.NAV_DEMANDES, str)
        assert len(AISSelectors.NAV_CLIENTS) > 0
        assert len(AISSelectors.NAV_DEMANDES) > 0

    def test_table_selectors_defined(self) -> None:
        """Table body row selectors must be defined."""
        assert isinstance(AISSelectors.TABLE_ROWS, str)
        assert len(AISSelectors.TABLE_ROWS) > 0


# ──────────────────────────────────────────────
# Interface Parity with AISAPIAdapter
# ──────────────────────────────────────────────


class TestInterfaceParity:
    """AISPlaywrightFallback must expose the same public methods as AISAPIAdapter."""

    def test_has_connect_method(self, fallback: AISPlaywrightFallback) -> None:
        """Must have connect() method."""
        assert hasattr(fallback, "connect")
        assert callable(fallback.connect)

    def test_has_get_clients_method(self, fallback: AISPlaywrightFallback) -> None:
        """Must have get_clients() method."""
        assert hasattr(fallback, "get_clients")
        assert callable(fallback.get_clients)

    def test_has_get_invoices_method(self, fallback: AISPlaywrightFallback) -> None:
        """Must have get_invoices() method."""
        assert hasattr(fallback, "get_invoices")
        assert callable(fallback.get_invoices)

    def test_has_get_invoice_statuses_method(self, fallback: AISPlaywrightFallback) -> None:
        """Must have get_invoice_statuses() method."""
        assert hasattr(fallback, "get_invoice_statuses")
        assert callable(fallback.get_invoice_statuses)

    def test_has_get_invoice_status_method(self, fallback: AISPlaywrightFallback) -> None:
        """Must have get_invoice_status() method."""
        assert hasattr(fallback, "get_invoice_status")
        assert callable(fallback.get_invoice_status)

    def test_has_get_pending_reminders_method(self, fallback: AISPlaywrightFallback) -> None:
        """Must have get_pending_reminders() method."""
        assert hasattr(fallback, "get_pending_reminders")
        assert callable(fallback.get_pending_reminders)

    def test_has_close_method(self, fallback: AISPlaywrightFallback) -> None:
        """Must have close() method."""
        assert hasattr(fallback, "close")
        assert callable(fallback.close)

    def test_forbidden_register_client(self, fallback: AISPlaywrightFallback) -> None:
        """register_client() must raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="INTERDIT"):
            fallback.register_client({"nom": "Test"})

    def test_forbidden_submit_invoice(self, fallback: AISPlaywrightFallback) -> None:
        """submit_invoice() must raise NotImplementedError."""
        with pytest.raises(NotImplementedError, match="INTERDIT"):
            fallback.submit_invoice("C123", {"montant": 100})


# ──────────────────────────────────────────────
# Connect (Login via Playwright)
# ──────────────────────────────────────────────


class TestConnect:
    """Test Playwright-based login to AIS."""

    @pytest.mark.asyncio
    async def test_connect_launches_headless_chromium(
        self,
        ais_settings: Settings,
        mock_browser: AsyncMock,
        mock_page: AsyncMock,
    ) -> None:
        """connect() must launch headless Chromium and login."""
        fallback = AISPlaywrightFallback(ais_settings)

        with patch("src.adapters.ais_playwright_fallback.async_playwright") as mock_pw_fn:
            mock_pw = AsyncMock()
            mock_pw_fn.return_value.__aenter__ = AsyncMock(return_value=mock_pw)
            mock_pw_fn.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            await fallback.connect()

            mock_pw.chromium.launch.assert_called_once_with(headless=True)

    @pytest.mark.asyncio
    async def test_connect_fills_login_form(
        self,
        ais_settings: Settings,
        mock_browser: AsyncMock,
        mock_page: AsyncMock,
    ) -> None:
        """connect() must fill email and password fields."""
        fallback = AISPlaywrightFallback(ais_settings)

        with patch("src.adapters.ais_playwright_fallback.async_playwright") as mock_pw_fn:
            mock_pw = AsyncMock()
            mock_pw_fn.return_value.__aenter__ = AsyncMock(return_value=mock_pw)
            mock_pw_fn.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            await fallback.connect()

            fill_calls = mock_page.fill.call_args_list
            assert any(
                call[0][0] == AISSelectors.LOGIN_EMAIL and call[0][1] == ais_settings.ais_email
                for call in fill_calls
            )
            assert any(
                call[0][0] == AISSelectors.LOGIN_PASSWORD
                and call[0][1] == ais_settings.ais_password
                for call in fill_calls
            )

    @pytest.mark.asyncio
    async def test_connect_clicks_submit(
        self,
        ais_settings: Settings,
        mock_browser: AsyncMock,
        mock_page: AsyncMock,
    ) -> None:
        """connect() must click the login submit button."""
        fallback = AISPlaywrightFallback(ais_settings)

        with patch("src.adapters.ais_playwright_fallback.async_playwright") as mock_pw_fn:
            mock_pw = AsyncMock()
            mock_pw_fn.return_value.__aenter__ = AsyncMock(return_value=mock_pw)
            mock_pw_fn.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            await fallback.connect()

            mock_page.click.assert_any_call(AISSelectors.LOGIN_SUBMIT)

    @pytest.mark.asyncio
    async def test_connect_navigates_to_ais(
        self,
        ais_settings: Settings,
        mock_browser: AsyncMock,
        mock_page: AsyncMock,
    ) -> None:
        """connect() must navigate to the AIS login page."""
        fallback = AISPlaywrightFallback(ais_settings)

        with patch("src.adapters.ais_playwright_fallback.async_playwright") as mock_pw_fn:
            mock_pw = AsyncMock()
            mock_pw_fn.return_value.__aenter__ = AsyncMock(return_value=mock_pw)
            mock_pw_fn.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

            await fallback.connect()

            goto_calls = [str(c) for c in mock_page.goto.call_args_list]
            assert any(AIS_BASE_URL in c for c in goto_calls)


# ──────────────────────────────────────────────
# DOM Parsing — Clients
# ──────────────────────────────────────────────


class TestGetClients:
    """Test parsing clients table from AIS DOM."""

    @pytest.mark.asyncio
    async def test_get_clients_parses_table(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_clients() must parse rows from the clients table."""
        fallback._page = mock_page

        # Simulate JS evaluate returning table data
        mock_page.evaluate.return_value = [
            {
                "client_id": "URSSAF-001",
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@test.fr",
                "statut_urssaf": "INSCRIT",
            },
            {
                "client_id": "URSSAF-002",
                "nom": "Martin",
                "prenom": "Bob",
                "email": "bob@test.fr",
                "statut_urssaf": "EN_ATTENTE",
            },
        ]

        result = await fallback.get_clients()

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["client_id"] == "URSSAF-001"
        assert result[0]["nom"] == "Dupont"
        assert result[1]["email"] == "bob@test.fr"

    @pytest.mark.asyncio
    async def test_get_clients_empty_table(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_clients() returns [] when table has no rows."""
        fallback._page = mock_page
        mock_page.evaluate.return_value = []

        result = await fallback.get_clients()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_clients_deduplicates(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_clients() deduplicates by client_id."""
        fallback._page = mock_page
        mock_page.evaluate.return_value = [
            {
                "client_id": "URSSAF-001",
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@test.fr",
                "statut_urssaf": "INSCRIT",
            },
            {
                "client_id": "URSSAF-001",
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@test.fr",
                "statut_urssaf": "INSCRIT",
            },
        ]

        result = await fallback.get_clients()

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_clients_requires_page(self, fallback: AISPlaywrightFallback) -> None:
        """get_clients() raises RuntimeError if not connected."""
        fallback._page = None

        with pytest.raises(RuntimeError, match="connect"):
            await fallback.get_clients()


# ──────────────────────────────────────────────
# DOM Parsing — Invoices / Statuses
# ──────────────────────────────────────────────


class TestGetInvoiceStatuses:
    """Test parsing invoice statuses from AIS DOM."""

    @pytest.mark.asyncio
    async def test_get_invoice_statuses_parses_all_statuses(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_invoice_statuses() parses demandes table with status badges."""
        fallback._page = mock_page
        mock_page.evaluate.return_value = [
            {
                "demande_id": "DEM-001",
                "statut": "EN_ATTENTE",
                "client_id": "URSSAF-001",
                "montant": 500.0,
                "date": "2026-03-21T10:00:00Z",
            },
            {
                "demande_id": "DEM-002",
                "statut": "PAYEE",
                "client_id": "URSSAF-002",
                "montant": 1000.0,
                "date": "2026-03-20T10:00:00Z",
            },
        ]

        result = await fallback.get_invoice_statuses()

        assert len(result) == 2
        assert result[0]["demande_id"] == "DEM-001"
        assert result[0]["statut"] == "EN_ATTENTE"
        assert result[1]["statut"] == "PAYEE"

    @pytest.mark.asyncio
    async def test_get_invoice_statuses_deduplicates(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_invoice_statuses() deduplicates by demande_id."""
        fallback._page = mock_page
        mock_page.evaluate.return_value = [
            {
                "demande_id": "DEM-001",
                "statut": "EN_ATTENTE",
                "client_id": "C1",
                "montant": 500.0,
                "date": "2026-03-21T10:00:00Z",
            },
            {
                "demande_id": "DEM-001",
                "statut": "EN_ATTENTE",
                "client_id": "C1",
                "montant": 500.0,
                "date": "2026-03-21T10:00:00Z",
            },
        ]

        result = await fallback.get_invoice_statuses()

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_invoice_statuses_requires_page(
        self, fallback: AISPlaywrightFallback
    ) -> None:
        """get_invoice_statuses() raises RuntimeError if not connected."""
        fallback._page = None

        with pytest.raises(RuntimeError, match="connect"):
            await fallback.get_invoice_statuses()


class TestGetInvoices:
    """Test get_invoices() with optional status filter."""

    @pytest.mark.asyncio
    async def test_get_invoices_returns_all_without_filter(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_invoices() returns all when no status filter."""
        fallback._page = mock_page
        mock_page.evaluate.return_value = [
            {
                "demande_id": "DEM-001",
                "statut": "EN_ATTENTE",
                "client_id": "C1",
                "montant": 500.0,
                "date": "2026-03-21T10:00:00Z",
            },
            {
                "demande_id": "DEM-002",
                "statut": "PAYEE",
                "client_id": "C2",
                "montant": 1000.0,
                "date": "2026-03-20T10:00:00Z",
            },
        ]

        result = await fallback.get_invoices()

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_invoices_filters_by_status(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_invoices(status='PAYEE') filters correctly."""
        fallback._page = mock_page
        mock_page.evaluate.return_value = [
            {
                "demande_id": "DEM-001",
                "statut": "EN_ATTENTE",
                "client_id": "C1",
                "montant": 500.0,
                "date": "2026-03-21T10:00:00Z",
            },
            {
                "demande_id": "DEM-002",
                "statut": "PAYEE",
                "client_id": "C2",
                "montant": 1000.0,
                "date": "2026-03-20T10:00:00Z",
            },
        ]

        result = await fallback.get_invoices(status="PAYEE")

        assert len(result) == 1
        assert result[0]["statut"] == "PAYEE"


class TestGetInvoiceStatus:
    """Test get_invoice_status() for a single invoice."""

    @pytest.mark.asyncio
    async def test_get_invoice_status_returns_string(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_invoice_status() returns the status string."""
        fallback._page = mock_page
        mock_page.evaluate.return_value = [
            {
                "demande_id": "DEM-001",
                "statut": "PAYEE",
                "client_id": "C1",
                "montant": 500.0,
                "date": "2026-03-21T10:00:00Z",
            },
        ]

        result = await fallback.get_invoice_status("DEM-001")

        assert result == "PAYEE"

    @pytest.mark.asyncio
    async def test_get_invoice_status_raises_if_not_found(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_invoice_status() raises ValueError if demande_id not found."""
        fallback._page = mock_page
        mock_page.evaluate.return_value = []

        with pytest.raises(ValueError, match="non trouvée"):
            await fallback.get_invoice_status("UNKNOWN")


# ──────────────────────────────────────────────
# Pending Reminders (T+36h)
# ──────────────────────────────────────────────


class TestGetPendingReminders:
    """Test pending reminder detection."""

    @pytest.mark.asyncio
    async def test_get_pending_reminders_finds_old_waiting(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_pending_reminders() finds EN_ATTENTE > threshold."""
        fallback._page = mock_page
        old_date = (datetime.now() - timedelta(hours=40)).isoformat() + "Z"
        mock_page.evaluate.return_value = [
            {
                "demande_id": "DEM-001",
                "statut": "EN_ATTENTE",
                "client_id": "C1",
                "montant": 500.0,
                "date": old_date,
            },
        ]

        result = await fallback.get_pending_reminders(hours_threshold=36)

        assert len(result) == 1
        assert result[0]["demande_id"] == "DEM-001"
        assert "hours_waiting" in result[0]

    @pytest.mark.asyncio
    async def test_get_pending_reminders_ignores_recent(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_pending_reminders() ignores EN_ATTENTE < threshold."""
        fallback._page = mock_page
        recent_date = (datetime.now() - timedelta(hours=10)).isoformat() + "Z"
        mock_page.evaluate.return_value = [
            {
                "demande_id": "DEM-001",
                "statut": "EN_ATTENTE",
                "client_id": "C1",
                "montant": 500.0,
                "date": recent_date,
            },
        ]

        result = await fallback.get_pending_reminders(hours_threshold=36)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_pending_reminders_ignores_non_waiting(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """get_pending_reminders() ignores statuses other than EN_ATTENTE."""
        fallback._page = mock_page
        old_date = (datetime.now() - timedelta(hours=40)).isoformat() + "Z"
        mock_page.evaluate.return_value = [
            {
                "demande_id": "DEM-001",
                "statut": "PAYEE",
                "client_id": "C1",
                "montant": 500.0,
                "date": old_date,
            },
        ]

        result = await fallback.get_pending_reminders(hours_threshold=36)

        assert len(result) == 0


# ──────────────────────────────────────────────
# Screenshot on Error
# ──────────────────────────────────────────────


class TestScreenshotOnError:
    """Test error screenshot capture."""

    @pytest.mark.asyncio
    async def test_screenshot_saves_to_cache_dir(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """_screenshot_on_error() saves to io/cache/ais_error_*.png."""
        fallback._page = mock_page

        with patch("pathlib.Path.mkdir"):
            await fallback._screenshot_on_error("login_failed")

            mock_page.screenshot.assert_called_once()
            call_kwargs = mock_page.screenshot.call_args[1]
            path_str = str(call_kwargs["path"])
            assert "io/cache/" in path_str or "io\\cache\\" in path_str
            assert "ais_error_" in path_str
            assert path_str.endswith(".png")

    @pytest.mark.asyncio
    async def test_screenshot_filename_has_no_sensitive_data(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """Screenshot filename must NOT contain email, password, or tokens."""
        fallback._page = mock_page

        with patch("pathlib.Path.mkdir"):
            await fallback._screenshot_on_error("login_failed")

            call_kwargs = mock_page.screenshot.call_args[1]
            path_str = str(call_kwargs["path"])
            assert fallback._settings.ais_email not in path_str
            assert fallback._settings.ais_password not in path_str

    @pytest.mark.asyncio
    async def test_screenshot_no_page_does_nothing(self, fallback: AISPlaywrightFallback) -> None:
        """_screenshot_on_error() does nothing if page is None."""
        fallback._page = None

        # Should not raise
        await fallback._screenshot_on_error("test")

    @pytest.mark.asyncio
    async def test_screenshot_failure_does_not_propagate(
        self, fallback: AISPlaywrightFallback, mock_page: AsyncMock
    ) -> None:
        """Screenshot failure must not propagate exceptions."""
        fallback._page = mock_page
        mock_page.screenshot.side_effect = RuntimeError("browser crashed")

        with patch("pathlib.Path.mkdir"):
            # Should not raise
            await fallback._screenshot_on_error("crash_test")


# ──────────────────────────────────────────────
# Close
# ──────────────────────────────────────────────


class TestClose:
    """Test browser cleanup."""

    @pytest.mark.asyncio
    async def test_close_closes_browser(
        self, fallback: AISPlaywrightFallback, mock_browser: AsyncMock
    ) -> None:
        """close() closes the browser."""
        fallback._browser = mock_browser

        await fallback.close()

        mock_browser.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_nullifies_state(
        self, fallback: AISPlaywrightFallback, mock_browser: AsyncMock
    ) -> None:
        """close() sets _browser and _page to None."""
        fallback._browser = mock_browser
        fallback._page = AsyncMock()

        await fallback.close()

        assert fallback._browser is None
        assert fallback._page is None

    @pytest.mark.asyncio
    async def test_close_idempotent(self, fallback: AISPlaywrightFallback) -> None:
        """close() is safe to call when already closed."""
        fallback._browser = None
        fallback._page = None

        await fallback.close()

        assert fallback._browser is None


# ──────────────────────────────────────────────
# Facade: AISAdapterWithFallback
# ──────────────────────────────────────────────


class TestAISAdapterWithFallback:
    """Test the REST-first, Playwright-fallback facade."""

    def test_init_creates_both_adapters(self, ais_settings: Settings) -> None:
        """Facade initializes both REST and Playwright adapters."""
        facade = AISAdapterWithFallback(ais_settings)

        assert facade._rest is not None
        assert facade._playwright is not None

    @pytest.mark.asyncio
    async def test_get_clients_uses_rest_first(self, ais_settings: Settings) -> None:
        """Facade tries REST adapter first for get_clients()."""
        facade = AISAdapterWithFallback(ais_settings)
        expected = [{"client_id": "C001", "nom": "Test"}]

        facade._rest.get_clients = MagicMock(return_value=expected)

        result = await facade.get_clients()

        assert result == expected
        facade._rest.get_clients.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_clients_falls_back_to_playwright(self, ais_settings: Settings) -> None:
        """Facade falls back to Playwright when REST fails."""
        facade = AISAdapterWithFallback(ais_settings)
        expected = [{"client_id": "C002", "nom": "Fallback"}]

        facade._rest.get_clients = MagicMock(side_effect=RuntimeError("REST down"))
        facade._playwright.connect = AsyncMock()  # no-op lazy connect
        facade._playwright.get_clients = AsyncMock(return_value=expected)

        result = await facade.get_clients()

        assert result == expected
        facade._playwright.get_clients.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_invoices_uses_rest_first(self, ais_settings: Settings) -> None:
        """Facade tries REST for get_invoices()."""
        facade = AISAdapterWithFallback(ais_settings)
        expected = [{"demande_id": "D001", "statut": "PAYEE"}]

        facade._rest.get_invoices = MagicMock(return_value=expected)

        result = await facade.get_invoices(status="PAYEE")

        assert result == expected
        facade._rest.get_invoices.assert_called_once_with(status="PAYEE")

    @pytest.mark.asyncio
    async def test_get_invoices_falls_back_to_playwright(self, ais_settings: Settings) -> None:
        """Facade falls back to Playwright for get_invoices() on REST failure."""
        facade = AISAdapterWithFallback(ais_settings)
        expected = [{"demande_id": "D002", "statut": "EN_ATTENTE"}]

        facade._rest.get_invoices = MagicMock(side_effect=Exception("REST error"))
        facade._playwright.connect = AsyncMock()  # no-op lazy connect
        facade._playwright.get_invoices = AsyncMock(return_value=expected)

        result = await facade.get_invoices(status="EN_ATTENTE")

        assert result == expected

    @pytest.mark.asyncio
    async def test_get_invoice_statuses_uses_rest_first(self, ais_settings: Settings) -> None:
        """Facade tries REST for get_invoice_statuses()."""
        facade = AISAdapterWithFallback(ais_settings)
        expected = [{"demande_id": "D001", "statut": "PAYEE"}]

        facade._rest.get_invoice_statuses = MagicMock(return_value=expected)

        result = await facade.get_invoice_statuses()

        assert result == expected

    @pytest.mark.asyncio
    async def test_get_invoice_statuses_falls_back(self, ais_settings: Settings) -> None:
        """Facade falls back for get_invoice_statuses()."""
        facade = AISAdapterWithFallback(ais_settings)
        expected = [{"demande_id": "D001", "statut": "PAYEE"}]

        facade._rest.get_invoice_statuses = MagicMock(side_effect=RuntimeError("REST down"))
        facade._playwright.connect = AsyncMock()  # no-op lazy connect
        facade._playwright.get_invoice_statuses = AsyncMock(return_value=expected)

        result = await facade.get_invoice_statuses()

        assert result == expected

    @pytest.mark.asyncio
    async def test_get_invoice_status_uses_rest_first(self, ais_settings: Settings) -> None:
        """Facade tries REST for get_invoice_status()."""
        facade = AISAdapterWithFallback(ais_settings)

        facade._rest.get_invoice_status = MagicMock(return_value="PAYEE")

        result = await facade.get_invoice_status("DEM-001")

        assert result == "PAYEE"

    @pytest.mark.asyncio
    async def test_get_invoice_status_falls_back(self, ais_settings: Settings) -> None:
        """Facade falls back for get_invoice_status()."""
        facade = AISAdapterWithFallback(ais_settings)

        facade._rest.get_invoice_status = MagicMock(side_effect=RuntimeError("REST down"))
        facade._playwright.connect = AsyncMock()  # no-op lazy connect
        facade._playwright.get_invoice_status = AsyncMock(return_value="EN_ATTENTE")

        result = await facade.get_invoice_status("DEM-001")

        assert result == "EN_ATTENTE"

    @pytest.mark.asyncio
    async def test_get_pending_reminders_uses_rest_first(self, ais_settings: Settings) -> None:
        """Facade tries REST for get_pending_reminders()."""
        facade = AISAdapterWithFallback(ais_settings)
        expected = [{"demande_id": "D001", "hours_waiting": 40}]

        facade._rest.get_pending_reminders = MagicMock(return_value=expected)

        result = await facade.get_pending_reminders(hours_threshold=36)

        assert result == expected

    @pytest.mark.asyncio
    async def test_get_pending_reminders_falls_back(self, ais_settings: Settings) -> None:
        """Facade falls back for get_pending_reminders()."""
        facade = AISAdapterWithFallback(ais_settings)
        expected = [{"demande_id": "D001", "hours_waiting": 40}]

        facade._rest.get_pending_reminders = MagicMock(side_effect=RuntimeError("REST down"))
        facade._playwright.connect = AsyncMock()  # no-op lazy connect
        facade._playwright.get_pending_reminders = AsyncMock(return_value=expected)

        result = await facade.get_pending_reminders(hours_threshold=36)

        assert result == expected

    @pytest.mark.asyncio
    async def test_connect_connects_rest_only(self, ais_settings: Settings) -> None:
        """connect() connects REST adapter; Playwright connects lazily."""
        facade = AISAdapterWithFallback(ais_settings)
        facade._rest.connect = MagicMock()

        await facade.connect()

        facade._rest.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_closes_both_adapters(self, ais_settings: Settings) -> None:
        """close() closes both REST and Playwright adapters."""
        facade = AISAdapterWithFallback(ais_settings)
        facade._rest.close = MagicMock()
        facade._playwright.close = AsyncMock()

        await facade.close()

        facade._rest.close.assert_called_once()
        facade._playwright.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_playwright_fallback_connects_lazily(self, ais_settings: Settings) -> None:
        """When fallback is triggered, Playwright connect() is called first."""
        facade = AISAdapterWithFallback(ais_settings)
        facade._rest.get_clients = MagicMock(side_effect=RuntimeError("REST down"))
        facade._playwright._page = None
        facade._playwright.connect = AsyncMock()
        facade._playwright.get_clients = AsyncMock(return_value=[])

        await facade.get_clients()

        facade._playwright.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_both_fail_raises_last_error(self, ais_settings: Settings) -> None:
        """When both REST and Playwright fail, the Playwright error is raised."""
        facade = AISAdapterWithFallback(ais_settings)
        facade._rest.get_clients = MagicMock(side_effect=RuntimeError("REST down"))
        facade._playwright._page = AsyncMock()  # skip lazy connect
        facade._playwright.get_clients = AsyncMock(side_effect=RuntimeError("Playwright also down"))

        with pytest.raises(RuntimeError, match="Playwright also down"):
            await facade.get_clients()
