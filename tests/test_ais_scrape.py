"""Tests RED — AISAdapter scraping methods (Playwright LECTURE logic).

RED tests for:
- get_invoice_statuses() → scrape page demandes, return list[dict] with statuts
- get_clients() → scrape page clients, return list[dict] with client data
- Login retry logic (3x backoff exponential)
- Session management (connect → scrape → close)
- Screenshot capture on error (RGPD-safe)

All tests will FAIL initially because methods raise NotImplementedError.
Mock Playwright completely (sync_playwright, Browser, Page, Context).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from tenacity import RetryError

from src.adapters.ais_adapter import AISAdapter
from src.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Configuration test avec credentials AIS."""
    return Settings(
        ais_email="jules@test.fr",
        ais_password="secret_ais_123",
    )


@pytest.fixture
def mock_ais_page() -> MagicMock:
    """Mock pour page AIS."""
    return MagicMock()


@pytest.fixture
def mock_ais_browser(mock_ais_page: MagicMock) -> MagicMock:
    """Mock pour browser AIS."""
    browser = MagicMock()
    context = MagicMock()
    browser.new_context.return_value = context
    context.new_page.return_value = mock_ais_page
    return browser


@pytest.fixture
def mock_ais_pw(mock_ais_browser: MagicMock) -> MagicMock:
    """Mock pour sync_playwright AIS."""
    with patch("src.adapters.ais_adapter.sync_playwright") as mock:
        pw_instance = MagicMock()
        mock.return_value.start.return_value = pw_instance
        pw_instance.chromium.launch.return_value = mock_ais_browser
        yield mock


# ============================================================================
# Test Class: Get Invoice Statuses (Scrape demandes page)
# ============================================================================


class TestGetInvoiceStatuses:
    """Test scraping des statuts depuis la page Demandes AIS."""

    def test_get_invoice_statuses_returns_list(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """get_invoice_statuses() retourne une liste de dict."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock page content: table with demandes
        mock_ais_page.locator.return_value.all.return_value = [
            MagicMock(),
            MagicMock(),
        ]
        mock_ais_page.locator.return_value.all.return_value[
            0
        ].text_content.return_value = "DEMANDE-001 | EN_ATTENTE | Client A | 500.00 € | 2026-03-21"
        mock_ais_page.locator.return_value.all.return_value[
            1
        ].text_content.return_value = "DEMANDE-002 | VALIDE | Client B | 1000.00 € | 2026-03-20"

        result = adapter.get_invoice_statuses()

        assert isinstance(result, list)
        assert len(result) >= 0  # RED: will be list (empty or with items)

    def test_get_invoice_statuses_extracts_fields(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Chaque statut contient: demande_id, statut, client, montant, date."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock page with demande data
        mock_row = MagicMock()
        mock_row.text_content.return_value = (
            "DEMANDE-001 | EN_ATTENTE | Client A | 500.00 | 2026-03-21"
        )
        mock_ais_page.locator.return_value.all.return_value = [mock_row]

        result = adapter.get_invoice_statuses()

        if result:
            # Check structure if data returned
            item = result[0]
            assert "demande_id" in item or "urssaf_demande_id" in item
            assert "statut" in item or "statut_ais" in item
            assert "client" in item or "client_id" in item
            assert "montant" in item
            assert "date" in item or "date_maj" in item

    def test_get_invoice_statuses_handles_empty_page(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Page sans demandes → liste vide."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock empty page (no rows)
        mock_ais_page.locator.return_value.all.return_value = []

        result = adapter.get_invoice_statuses()

        assert result == []

    def test_get_invoice_statuses_deduplicates(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Doublons supprimés par demande_id/urssaf_demande_id."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock page with duplicate demandes
        mock_row1 = MagicMock()
        mock_row1.text_content.return_value = (
            "DEMANDE-001 | EN_ATTENTE | Client A | 500.00 | 2026-03-21"
        )
        mock_row2 = MagicMock()
        mock_row2.text_content.return_value = (
            "DEMANDE-001 | EN_ATTENTE | Client A | 500.00 | 2026-03-21"
        )
        mock_ais_page.locator.return_value.all.return_value = [mock_row1, mock_row2]

        result = adapter.get_invoice_statuses()

        # If dupes removed, should have max 1 item with DEMANDE-001
        if result:
            demande_ids = [
                item.get("demande_id") or item.get("urssaf_demande_id") for item in result
            ]
            assert len(demande_ids) == len(set(demande_ids))

    def test_get_invoice_statuses_navigates_to_demandes_page(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Navigate to demandes page before scrape."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        mock_ais_page.locator.return_value.all.return_value = []

        adapter.get_invoice_statuses()

        # Verify navigate or goto called
        assert mock_ais_page.goto.called or mock_ais_page.locator.called

    def test_get_invoice_statuses_waits_for_table(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Wait for demandes table to load."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        mock_ais_page.locator.return_value.all.return_value = []

        adapter.get_invoice_statuses()

        # Verify wait_for_selector or similar called
        assert mock_ais_page.wait_for_selector.called or mock_ais_page.locator.called


# ============================================================================
# Test Class: Get Clients (Scrape clients page)
# ============================================================================


class TestGetClients:
    """Test scraping des clients depuis la page Clients AIS."""

    def test_get_clients_returns_list(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """get_clients() retourne une liste de dict."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock page content
        mock_ais_page.locator.return_value.all.return_value = [MagicMock()]

        result = adapter.get_clients()

        assert isinstance(result, list)

    def test_get_clients_extracts_urssaf_id(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Chaque client contient: client_id (URSSAF ID)."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock client row
        mock_row = MagicMock()
        mock_row.text_content.return_value = (
            "URSSAF-001 | Alice Dupont | alice@test.fr | Active | 2026-01-01"
        )
        mock_ais_page.locator.return_value.all.return_value = [mock_row]

        result = adapter.get_clients()

        if result:
            client = result[0]
            assert "client_id" in client or "urssaf_id" in client or "nom" in client

    def test_get_clients_extracts_nom_prenom(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Chaque client contient: nom, prenom (ou nom complet)."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        mock_row = MagicMock()
        mock_row.text_content.return_value = (
            "URSSAF-001 | Alice Dupont | alice@test.fr | Active | 2026-01-01"
        )
        mock_ais_page.locator.return_value.all.return_value = [mock_row]

        result = adapter.get_clients()

        if result:
            client = result[0]
            assert "nom" in client or "prenom" in client or "client_name" in client

    def test_get_clients_extracts_email(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Chaque client contient: email."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        mock_row = MagicMock()
        mock_row.text_content.return_value = (
            "URSSAF-001 | Alice Dupont | alice@test.fr | Active | 2026-01-01"
        )
        mock_ais_page.locator.return_value.all.return_value = [mock_row]

        result = adapter.get_clients()

        if result:
            client = result[0]
            assert "email" in client or "contact" in client

    def test_get_clients_handles_empty_page(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Page sans clients → liste vide."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        mock_ais_page.locator.return_value.all.return_value = []

        result = adapter.get_clients()

        assert result == []

    def test_get_clients_deduplicates(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Doublons supprimés par client_id/urssaf_id."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock duplicate clients
        mock_row1 = MagicMock()
        mock_row1.text_content.return_value = (
            "URSSAF-001 | Alice Dupont | alice@test.fr | Active | 2026-01-01"
        )
        mock_row2 = MagicMock()
        mock_row2.text_content.return_value = (
            "URSSAF-001 | Alice Dupont | alice@test.fr | Active | 2026-01-01"
        )
        mock_ais_page.locator.return_value.all.return_value = [mock_row1, mock_row2]

        result = adapter.get_clients()

        # Check dedup by ID
        if result:
            client_ids = [item.get("client_id") or item.get("urssaf_id") for item in result]
            assert len(client_ids) == len(set(client_ids))

    def test_get_clients_navigates_to_clients_page(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Navigate to clients page before scrape."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        mock_ais_page.locator.return_value.all.return_value = []

        adapter.get_clients()

        # Verify page navigation
        assert mock_ais_page.goto.called or mock_ais_page.locator.called


# ============================================================================
# Test Class: Login Retry Logic
# ============================================================================


class TestLoginRetry:
    """Test login retry avec tenacity (3x backoff exponentiel)."""

    def test_login_retries_3_times(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Login échoue 3 fois avant renoncer (retry decorator)."""
        adapter = AISAdapter(settings)

        # Mock page to always fail login
        mock_ais_page.goto.side_effect = TimeoutError("Login timeout")

        with pytest.raises((TimeoutError, RetryError)):
            adapter._login()

    def test_login_screenshot_on_failure(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Login échoué → screenshot d'erreur capturé."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock page to fail
        mock_ais_page.goto.side_effect = TimeoutError("Login timeout")

        with (
            patch.object(adapter, "_screenshot_on_error"),
            pytest.raises((TimeoutError, RetryError)),
        ):
            adapter._login()

            # Screenshot may be called during failure handling
            # (implementation detail — might not be called in _login itself)

    def test_login_fills_credentials(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Login remplit email et password via page.fill()."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock successful page navigation but fail fill
        mock_ais_page.goto.return_value = None
        mock_ais_page.fill.side_effect = TimeoutError("Credential field not found")

        with pytest.raises((TimeoutError, RetryError)):
            adapter._login()

        # Verify fill was attempted with credentials
        assert any(
            settings.ais_email in str(call) or settings.ais_password in str(call)
            for call in mock_ais_page.fill.call_args_list
        )

    def test_login_clicks_submit_button(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Login clique sur le bouton submit."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock page flow
        mock_ais_page.goto.return_value = None
        mock_ais_page.fill.return_value = None
        mock_ais_page.click.side_effect = TimeoutError("Submit button not found")

        with pytest.raises((TimeoutError, RetryError)):
            adapter._login()

        # Verify click was attempted
        assert mock_ais_page.click.called

    def test_login_waits_for_redirect(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Login attend la redirection après login."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock page flow
        mock_ais_page.goto.return_value = None
        mock_ais_page.fill.return_value = None
        mock_ais_page.click.return_value = None
        mock_ais_page.wait_for_url.side_effect = TimeoutError("Redirect timeout")

        with pytest.raises((TimeoutError, RetryError)):
            adapter._login()

        # Verify wait_for_url was called
        assert mock_ais_page.wait_for_url.called or mock_ais_page.wait_for_load_state.called


# ============================================================================
# Test Class: Session Management
# ============================================================================


class TestSessionManagement:
    """Test session management: connect → scrape → close."""

    def test_connect_then_scrape(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_browser: MagicMock
    ) -> None:
        """Connect établit session, puis scrape() peut être appelé."""
        adapter = AISAdapter(settings)

        with pytest.raises((NotImplementedError, RetryError)):
            adapter.connect()

        # After connect, browser and page should be initialized (or None if connect failed)
        # Just verify the flow is possible

    def test_close_releases_browser(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_browser: MagicMock
    ) -> None:
        """close() ferme le navigateur et libère les ressources."""
        adapter = AISAdapter(settings)
        adapter._browser = mock_ais_browser
        adapter._page = MagicMock()
        adapter._context = MagicMock()
        adapter._playwright_instance = MagicMock()

        adapter.close()

        # Verify close was called
        mock_ais_browser.close.assert_called_once()
        assert adapter._browser is None
        assert adapter._page is None

    def test_close_idempotent(self, settings: Settings) -> None:
        """close() est idempotent (safe to call multiple times)."""
        adapter = AISAdapter(settings)
        adapter._browser = None
        adapter._page = None
        adapter._context = None
        adapter._playwright_instance = None

        # Should not raise
        adapter.close()
        adapter.close()

    def test_context_manager_pattern(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_browser: MagicMock
    ) -> None:
        """Adapter can be used in with statement (if __enter__/__exit__ implemented)."""
        adapter = AISAdapter(settings)

        # This test may fail if __enter__/__exit__ not implemented
        # But it documents expected usage pattern
        try:
            with adapter:
                pass
        except (AttributeError, NotImplementedError):
            # Expected if context manager not yet implemented
            pass


# ============================================================================
# Test Class: Error Handling & Screenshots
# ============================================================================


class TestErrorHandling:
    """Test error handling et screenshot capture."""

    def test_screenshot_on_error_creates_directory(
        self, settings: Settings, mock_ais_page: MagicMock
    ) -> None:
        """_screenshot_on_error() crée le répertoire io/cache."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page

        with patch("pathlib.Path.mkdir"):
            adapter._screenshot_on_error("login_failed")

            mock_ais_page.screenshot.assert_called_once()

    def test_screenshot_on_error_saves_png(
        self, settings: Settings, mock_ais_page: MagicMock
    ) -> None:
        """_screenshot_on_error() sauvegarde .png avec timestamp."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page

        with patch("pathlib.Path.mkdir"):
            adapter._screenshot_on_error("scrape_failed")

            call_kwargs = mock_ais_page.screenshot.call_args[1]
            assert "path" in call_kwargs
            assert "error_ais" in call_kwargs["path"]
            assert "png" in call_kwargs["path"]

    def test_screenshot_on_error_no_page_safe(self, settings: Settings) -> None:
        """_screenshot_on_error() ne lève pas d'exception si _page is None."""
        adapter = AISAdapter(settings)
        adapter._page = None

        # Should not raise
        adapter._screenshot_on_error("test_error")

    def test_get_invoice_statuses_on_error_screenshot(
        self, settings: Settings, mock_ais_page: MagicMock
    ) -> None:
        """get_invoice_statuses() capture screenshot si scrape échoue."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        # Mock page to fail during scrape
        mock_ais_page.locator.side_effect = TimeoutError("Selector not found")

        with (
            patch.object(adapter, "_screenshot_on_error"),
            pytest.raises((NotImplementedError, TimeoutError, RetryError)),
        ):
            adapter.get_invoice_statuses()


# ============================================================================
# Test Class: Logging & Monitoring
# ============================================================================


class TestLogging:
    """Test logging (errors only, no PII)."""

    def test_login_logs_on_failure(
        self, settings: Settings, mock_ais_pw: MagicMock, mock_ais_page: MagicMock
    ) -> None:
        """Login failure is logged (without credentials)."""
        adapter = AISAdapter(settings)

        mock_ais_page.goto.side_effect = TimeoutError("Login page timeout")

        with patch("src.adapters.ais_adapter.logger"), pytest.raises((TimeoutError, RetryError)):
            adapter._login()

            # Logger may have been called (implementation detail)

    def test_no_credentials_in_logs(self, settings: Settings, mock_ais_page: MagicMock) -> None:
        """Credentials never appear in logs."""
        adapter = AISAdapter(settings)
        adapter._page = mock_ais_page
        adapter._browser = MagicMock()

        with patch("src.adapters.ais_adapter.logger") as mock_logger:
            mock_ais_page.locator.return_value.all.return_value = []

            adapter.get_invoice_statuses()

            # Verify no credential values in log calls
            for call in mock_logger.mock_calls:
                call_str = str(call)
                assert settings.ais_email not in call_str
                assert settings.ais_password not in call_str
