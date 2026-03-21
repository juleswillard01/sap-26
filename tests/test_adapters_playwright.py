"""Tests TDD pour adapters Playwright — IndyBrowserAdapter et AISAdapter.

Mock Playwright complètement (sync_playwright, Browser, Page, Context).
Tests pour:
- Initialisation avec credentials
- Connection et login (mock)
- Retry avec tenacity
- Screenshots d'erreur
- Export transactions (Indy)
- Clients, factures, statuts (AIS)
- Fermeture propre du navigateur
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from tenacity import RetryError

from src.adapters.ais_adapter import AISAdapter
from src.adapters.indy_adapter import IndyBrowserAdapter
from src.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Configuration de test avec credentials Indy et AIS."""
    return Settings(
        indy_email="test@indy.fr",
        indy_password="secret123",
        ais_email="test@avance.fr",
        ais_password="secret456",
    )


@pytest.fixture
def mock_indy_page() -> MagicMock:
    """Mock pour page Indy."""
    return MagicMock()


@pytest.fixture
def mock_indy_browser(mock_indy_page: MagicMock) -> MagicMock:
    """Mock pour browser Indy."""
    browser = MagicMock()
    context = MagicMock()
    browser.new_context.return_value = context
    context.new_page.return_value = mock_indy_page
    return browser


@pytest.fixture
def mock_indy_pw(mock_indy_browser: MagicMock) -> MagicMock:
    """Mock pour sync_playwright Indy."""
    with patch("src.adapters.indy_adapter.sync_playwright") as mock:
        pw_instance = MagicMock()
        mock.return_value.start.return_value = pw_instance
        pw_instance.chromium.launch.return_value = mock_indy_browser
        yield mock


@pytest.fixture
def mock_avance_page() -> MagicMock:
    """Mock pour page AIS."""
    return MagicMock()


@pytest.fixture
def mock_avance_browser(mock_avance_page: MagicMock) -> MagicMock:
    """Mock pour browser AIS."""
    browser = MagicMock()
    context = MagicMock()
    browser.new_context.return_value = context
    context.new_page.return_value = mock_avance_page
    return browser


@pytest.fixture
def mock_avance_pw(mock_avance_browser: MagicMock) -> MagicMock:
    """Mock pour sync_playwright AIS."""
    with patch("src.adapters.ais_adapter.sync_playwright") as mock:
        pw_instance = MagicMock()
        mock.return_value.start.return_value = pw_instance
        pw_instance.chromium.launch.return_value = mock_avance_browser
        yield mock


# ============================================================================
# Tests IndyBrowserAdapter
# ============================================================================


class TestIndyBrowserAdapterInit:
    """Tests pour l'initialisation de IndyBrowserAdapter."""

    def test_init_with_valid_credentials(self, settings: Settings) -> None:
        """Vérifie que __init__ accepte des credentials valides."""
        adapter = IndyBrowserAdapter(settings)
        assert adapter._settings == settings
        assert adapter._browser is None
        assert adapter._page is None

    def test_init_missing_indy_email_raises_valueerror(self) -> None:
        """Vérifie que __init__ lève ValueError si indy_email manque."""
        settings = Settings(indy_password="secret")
        with pytest.raises(ValueError, match="indy_email et indy_password requis"):
            IndyBrowserAdapter(settings)

    def test_init_missing_indy_password_raises_valueerror(self) -> None:
        """Vérifie que __init__ lève ValueError si indy_password manque."""
        settings = Settings(indy_email="test@indy.fr")
        with pytest.raises(ValueError, match="indy_email et indy_password requis"):
            IndyBrowserAdapter(settings)

    def test_init_empty_indy_email_raises_valueerror(self) -> None:
        """Vérifie que __init__ lève ValueError si indy_email est vide."""
        settings = Settings(indy_email="", indy_password="secret")
        with pytest.raises(ValueError, match="indy_email et indy_password requis"):
            IndyBrowserAdapter(settings)


class TestIndyBrowserAdapterConnect:
    """Tests pour la connexion et le login Indy."""

    def test_connect_launches_headless_chromium(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_browser: MagicMock
    ) -> None:
        """Vérifie que connect() lance Chromium en headless."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect()

        pw_instance = mock_indy_pw.return_value.start.return_value
        pw_instance.chromium.launch.assert_called_once_with(headless=True)

    def test_connect_creates_context_and_page(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_browser: MagicMock
    ) -> None:
        """Vérifie que connect() crée un contexte et une page."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect()

        mock_indy_browser.new_context.assert_called_once()

    def test_connect_sets_default_timeout(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que connect() définit le timeout de navigation."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect()

        mock_indy_page.set_default_timeout.assert_called_once_with(
            IndyBrowserAdapter.NAVIGATION_TIMEOUT
        )

    def test_connect_fills_login_credentials(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que connect() remplit email et password."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect()

        calls = mock_indy_page.fill.call_args_list
        assert any(call[0][1] == settings.indy_email for call in calls)
        assert any(call[0][1] == settings.indy_password for call in calls)

    def test_connect_navigates_to_login_page(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que connect() navigue à la page de login."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect()

        assert any("login" in str(call[0][0]) for call in mock_indy_page.goto.call_args_list)

    def test_connect_clicks_submit_button(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que connect() clique sur le bouton submit."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect()

        mock_indy_page.click.assert_called()

    def test_connect_waits_for_dashboard(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que connect() attend le dashboard après login."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect()

        assert any(
            "dashboard" in str(call[0][0]) for call in mock_indy_page.wait_for_url.call_args_list
        )

    def test_connect_login_failure_raises_runtimeerror(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que login() échouée lève RuntimeError."""
        mock_indy_page.goto.side_effect = TimeoutError("Login page timeout")
        adapter = IndyBrowserAdapter(settings)

        with pytest.raises(RuntimeError, match="Connexion Indy echouee"):
            adapter.connect()


class TestIndyBrowserAdapterExportTransactions:
    """Tests pour l'export de transactions Indy."""

    def test_export_transactions_returns_list_of_dicts(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que export_transactions() retourne une liste de dicts."""
        csv_content = (
            "Date,Description,Amount\n2024-01-15,Virement,100.50\n2024-01-16,Facture,-25.00"
        )
        mock_download = MagicMock()
        mock_download.path.return_value.read_text.return_value = csv_content
        mock_indy_page.expect_download.return_value.__enter__.return_value.value = mock_download

        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page
        adapter._browser = MagicMock()

        result = adapter.export_transactions("2024-01-01", "2024-01-31")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, dict) for item in result)

    def test_export_transactions_navigates_to_transactions_page(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que export_transactions() navigue à la page transactions."""
        csv_content = "Date,Description\n2024-01-15,Test"
        mock_download = MagicMock()
        mock_download.path.return_value.read_text.return_value = csv_content
        mock_indy_page.expect_download.return_value.__enter__.return_value.value = mock_download

        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page
        adapter._browser = MagicMock()

        adapter.export_transactions("2024-01-01", "2024-01-31")

        assert any("transactions" in str(call[0][0]) for call in mock_indy_page.goto.call_args_list)

    def test_export_transactions_applies_date_filters(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que export_transactions() applique les filtres de date."""
        csv_content = "Date,Description\n2024-01-15,Test"
        mock_download = MagicMock()
        mock_download.path.return_value.read_text.return_value = csv_content
        mock_indy_page.expect_download.return_value.__enter__.return_value.value = mock_download

        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page
        adapter._browser = MagicMock()

        adapter.export_transactions("2024-01-01", "2024-01-31")

        fill_calls = mock_indy_page.fill.call_args_list
        assert any("2024-01-01" in str(call) for call in fill_calls)
        assert any("2024-01-31" in str(call) for call in fill_calls)

    def test_export_transactions_waits_for_table_load(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que export_transactions() attend le chargement du tableau."""
        csv_content = "Date,Description\n2024-01-15,Test"
        mock_download = MagicMock()
        mock_download.path.return_value.read_text.return_value = csv_content
        mock_indy_page.expect_download.return_value.__enter__.return_value.value = mock_download

        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page
        adapter._browser = MagicMock()

        adapter.export_transactions("2024-01-01", "2024-01-31")

        assert mock_indy_page.wait_for_selector.called

    def test_export_transactions_empty_csv_returns_empty_list(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que export_transactions() retourne [] pour un CSV vide."""
        csv_content = "Date,Description\n"
        mock_download = MagicMock()
        mock_download.path.return_value.read_text.return_value = csv_content
        mock_indy_page.expect_download.return_value.__enter__.return_value.value = mock_download

        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page
        adapter._browser = MagicMock()

        result = adapter.export_transactions("2024-01-01", "2024-01-31")

        assert result == []


class TestIndyBrowserAdapterParseCSV:
    """Tests pour le parsing CSV (méthode statique)."""

    def test_parse_csv_returns_list_of_dicts(self) -> None:
        """Vérifie que _parse_csv() retourne une liste de dicts."""
        csv_content = "Date,Description,Amount\n2024-01-15,Test,100.50\n2024-01-16,Facture,-25.00"
        result = IndyBrowserAdapter._parse_csv(csv_content)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, dict) for item in result)

    def test_parse_csv_preserves_column_names(self) -> None:
        """Vérifie que _parse_csv() préserve les noms de colonnes."""
        csv_content = "Date,Description,Amount\n2024-01-15,Test,100.50"
        result = IndyBrowserAdapter._parse_csv(csv_content)

        assert "Date" in result[0]
        assert "Description" in result[0]
        assert "Amount" in result[0]

    def test_parse_csv_empty_raises_valueerror(self) -> None:
        """Vérifie que _parse_csv() lève ValueError pour un CSV vide."""
        csv_content = ""

        with pytest.raises(ValueError, match="CSV invalide ou vide"):
            IndyBrowserAdapter._parse_csv(csv_content)

    def test_parse_csv_no_data_rows_returns_empty_list(self) -> None:
        """Vérifie que _parse_csv() retourne [] si pas de données."""
        csv_content = "Date,Description,Amount\n"
        result = IndyBrowserAdapter._parse_csv(csv_content)

        assert result == []

    def test_parse_csv_handles_multiple_columns(self) -> None:
        """Vérifie que _parse_csv() gère plusieurs colonnes correctement."""
        csv_content = "Date,Description,Amount,Type\n2024-01-15,Test,100.50,Transfer"
        result = IndyBrowserAdapter._parse_csv(csv_content)

        assert len(result) == 1
        assert len(result[0]) == 4


class TestIndyBrowserAdapterGetBalance:
    """Tests pour la récupération du solde."""

    def test_get_balance_returns_float(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que get_balance() retourne un float."""
        mock_indy_page.text_content.return_value = "1 234,56 €"

        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page
        adapter._browser = MagicMock()

        result = adapter.get_balance()

        assert isinstance(result, float)
        assert result == 1234.56

    def test_get_balance_navigates_to_dashboard(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que get_balance() navigue au dashboard."""
        mock_indy_page.text_content.return_value = "1 000,00 €"

        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page
        adapter._browser = MagicMock()

        adapter.get_balance()

        assert any("dashboard" in str(call[0][0]) for call in mock_indy_page.goto.call_args_list)

    def test_get_balance_missing_element_raises_error(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que get_balance() lève RetryError si le solde n'existe pas."""
        mock_indy_page.text_content.return_value = None

        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page
        adapter._browser = MagicMock()

        with pytest.raises(RetryError):
            adapter.get_balance()


class TestIndyBrowserAdapterClose:
    """Tests pour la fermeture du navigateur."""

    def test_close_closes_browser(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_browser: MagicMock
    ) -> None:
        """Vérifie que close() ferme le navigateur."""
        adapter = IndyBrowserAdapter(settings)
        adapter._browser = mock_indy_browser
        adapter._page = MagicMock()

        adapter.close()

        mock_indy_browser.close.assert_called_once()

    def test_close_nullifies_browser_and_page(
        self, settings: Settings, mock_indy_pw: MagicMock
    ) -> None:
        """Vérifie que close() annule _browser et _page."""
        adapter = IndyBrowserAdapter(settings)
        adapter._browser = MagicMock()
        adapter._page = MagicMock()

        adapter.close()

        assert adapter._browser is None
        assert adapter._page is None

    def test_close_idempotent_when_no_browser(self, settings: Settings) -> None:
        """Vérifie que close() est idempotent si pas de navigateur."""
        adapter = IndyBrowserAdapter(settings)
        adapter._browser = None
        adapter._page = None

        adapter.close()

        assert adapter._browser is None


class TestIndyBrowserAdapterScreenshot:
    """Tests pour les screenshots d'erreur."""

    def test_screenshot_on_error_creates_directory(
        self, settings: Settings, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que _screenshot_on_error() crée le répertoire s'il n'existe pas."""
        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page

        with patch("pathlib.Path.mkdir"):
            adapter._screenshot_on_error("test_error")

            mock_indy_page.screenshot.assert_called_once()

    def test_screenshot_on_error_saves_png(
        self, settings: Settings, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que _screenshot_on_error() appelle screenshot."""
        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page

        with patch("pathlib.Path.mkdir"):
            adapter._screenshot_on_error("login_failed")

            mock_indy_page.screenshot.assert_called_once()
            call_kwargs = mock_indy_page.screenshot.call_args[1]
            assert "path" in call_kwargs
            assert "error_indy_login_failed.png" in call_kwargs["path"]

    def test_screenshot_on_error_no_page_does_nothing(self, settings: Settings) -> None:
        """Vérifie que _screenshot_on_error() ne lève pas d'exception sans page."""
        adapter = IndyBrowserAdapter(settings)
        adapter._page = None

        adapter._screenshot_on_error("test")


# ============================================================================
# Tests AISAdapter
# ============================================================================


class TestAISAdapterInit:
    """Tests pour l'initialisation de AISAdapter."""

    def test_init_stores_settings(self, settings: Settings) -> None:
        """Vérifie que __init__ stocke les settings."""
        adapter = AISAdapter(settings)

        assert adapter._settings == settings
        assert adapter._browser is None
        assert adapter._page is None


class TestAISAdapterConnect:
    """Tests pour la connexion AIS."""

    def test_connect_launches_headless_chromium(
        self, settings: Settings, mock_avance_pw: MagicMock, mock_avance_browser: MagicMock
    ) -> None:
        """Vérifie que connect() lance Chromium en headless."""
        adapter = AISAdapter(settings)

        with pytest.raises((NotImplementedError, RetryError)):
            adapter.connect()

        pw_instance = mock_avance_pw.return_value.start.return_value
        pw_instance.chromium.launch.assert_called_once_with(headless=True)

    def test_connect_creates_context_and_page(
        self, settings: Settings, mock_avance_pw: MagicMock, mock_avance_browser: MagicMock
    ) -> None:
        """Vérifie que connect() crée un contexte et une page."""
        adapter = AISAdapter(settings)

        with pytest.raises((NotImplementedError, RetryError)):
            adapter.connect()

        mock_avance_browser.new_context.assert_called_once()


class TestAISAdapterGetClients:
    """Tests pour la récupération des clients."""

    def test_get_clients_raises_notimplementederror(self, settings: Settings) -> None:
        """Vérifie que get_clients() lève NotImplementedError."""
        adapter = AISAdapter(settings)

        with pytest.raises(NotImplementedError, match="À implémenter"):
            adapter.get_clients()

    def test_get_clients_docstring_exists(self, settings: Settings) -> None:
        """Vérifie que get_clients() a une docstring."""
        adapter = AISAdapter(settings)
        assert adapter.get_clients.__doc__ is not None


class TestAISAdapterGetInvoices:
    """Tests pour la récupération des factures."""

    def test_get_invoices_raises_notimplementederror(self, settings: Settings) -> None:
        """Vérifie que get_invoices() lève NotImplementedError."""
        adapter = AISAdapter(settings)

        with pytest.raises(NotImplementedError, match="À implémenter"):
            adapter.get_invoices()

    def test_get_invoices_with_status_filter_raises_notimplementederror(
        self, settings: Settings
    ) -> None:
        """Vérifie que get_invoices(status=...) lève NotImplementedError."""
        adapter = AISAdapter(settings)

        with pytest.raises(NotImplementedError):
            adapter.get_invoices(status="approved")


class TestAISAdapterGetInvoiceStatus:
    """Tests pour la récupération du statut d'une facture."""

    def test_get_invoice_status_raises_notimplementederror(self, settings: Settings) -> None:
        """Vérifie que get_invoice_status() lève NotImplementedError."""
        adapter = AISAdapter(settings)

        with pytest.raises(NotImplementedError, match="À implémenter"):
            adapter.get_invoice_status("demande_123")


class TestAISAdapterSubmitInvoice:
    """Tests pour la soumission d'une facture."""

    def test_submit_invoice_raises_notimplementederror(self, settings: Settings) -> None:
        """Vérifie que submit_invoice() lève NotImplementedError."""
        adapter = AISAdapter(settings)
        invoice_data = {"montant": 1000, "client_id": "C001"}

        with pytest.raises(NotImplementedError, match="À implémenter"):
            adapter.submit_invoice("C001", invoice_data)


class TestAISAdapterRegisterClient:
    """Tests pour l'inscription d'un nouveau client."""

    def test_register_client_raises_notimplementederror(self, settings: Settings) -> None:
        """Vérifie que register_client() lève NotImplementedError."""
        adapter = AISAdapter(settings)
        client_data = {"nom": "Dupont", "email": "dupont@test.fr"}

        with pytest.raises(NotImplementedError, match="À implémenter"):
            adapter.register_client(client_data)


class TestAISAdapterClose:
    """Tests pour la fermeture du navigateur."""

    def test_close_closes_browser(
        self, settings: Settings, mock_avance_pw: MagicMock, mock_avance_browser: MagicMock
    ) -> None:
        """Vérifie que close() ferme le navigateur."""
        adapter = AISAdapter(settings)
        adapter._browser = mock_avance_browser
        adapter._page = MagicMock()

        adapter.close()

        mock_avance_browser.close.assert_called_once()

    def test_close_nullifies_browser_and_page(self, settings: Settings) -> None:
        """Vérifie que close() annule _browser et _page."""
        adapter = AISAdapter(settings)
        adapter._browser = MagicMock()
        adapter._page = MagicMock()

        adapter.close()

        assert adapter._browser is None
        assert adapter._page is None

    def test_close_idempotent_when_no_browser(self, settings: Settings) -> None:
        """Vérifie que close() est idempotent."""
        adapter = AISAdapter(settings)
        adapter._browser = None
        adapter._page = None

        adapter.close()

        assert adapter._browser is None


class TestAISAdapterScreenshot:
    """Tests pour les screenshots d'erreur."""

    def test_screenshot_on_error_saves_file(
        self, settings: Settings, mock_avance_page: MagicMock
    ) -> None:
        """Vérifie que _screenshot_on_error() sauvegarde un fichier."""
        adapter = AISAdapter(settings)
        adapter._page = mock_avance_page

        with patch("pathlib.Path.mkdir"):
            adapter._screenshot_on_error("test_error")

            mock_avance_page.screenshot.assert_called_once()
            call_kwargs = mock_avance_page.screenshot.call_args[1]
            assert "path" in call_kwargs
            assert "error_ais_test_error.png" in call_kwargs["path"]

    def test_screenshot_on_error_no_page_does_nothing(self, settings: Settings) -> None:
        """Vérifie que _screenshot_on_error() ne lève pas sans page."""
        adapter = AISAdapter(settings)
        adapter._page = None

        adapter._screenshot_on_error("test")


class TestAISAdapterLogin:
    """Tests pour la tentative de login (NotImplementedError)."""

    def test_login_raises_notimplementederror(self, settings: Settings) -> None:
        """Vérifie que _login() lève RetryError wrappant NotImplementedError."""
        adapter = AISAdapter(settings)

        with pytest.raises(RetryError):
            adapter._login()
