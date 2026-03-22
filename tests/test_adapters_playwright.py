"""Tests TDD pour adapters — IndyBrowserAdapter (Playwright) et AISAPIAdapter (REST).

Mock Playwright pour IndyBrowserAdapter (sync_playwright, Browser, Page, Context).
Mock httpx pour AISAPIAdapter (client POST/GET).

Tests pour:
- IndyBrowserAdapter: Initialisation, connection, login, export transactions
- AISAPIAdapter: Initialisation, token acquisition, collection reads
- Retry avec tenacity
- Context managers
- Fermeture propre des ressources
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from tenacity import RetryError

from src.adapters.ais_adapter import AISAPIAdapter
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
def mock_httpx_client() -> MagicMock:
    """Mock pour client httpx AIS (REST API)."""
    return MagicMock(spec=httpx.Client)


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
        """Vérifie que connect(session_mode='headed') crée un contexte et une page."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect(session_mode="headed")

        mock_indy_browser.new_context.assert_called_once()

    def test_connect_sets_default_timeout(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que connect(session_mode='headed') définit le timeout de navigation."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect(session_mode="headed")

        mock_indy_page.set_default_timeout.assert_called_once_with(
            IndyBrowserAdapter.NAVIGATION_TIMEOUT
        )

    def test_connect_fills_login_credentials(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que connect(session_mode='headed') remplit email et password."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect(session_mode="headed")

        calls = mock_indy_page.fill.call_args_list
        assert any(call[0][1] == settings.indy_email for call in calls)
        assert any(call[0][1] == settings.indy_password for call in calls)

    def test_connect_navigates_to_login_page(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que connect(session_mode='headed') navigue à la page de login."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect(session_mode="headed")

        assert any("login" in str(call[0][0]) for call in mock_indy_page.goto.call_args_list)

    def test_connect_clicks_submit_button(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que connect(session_mode='headed') clique sur le bouton submit."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect(session_mode="headed")

        mock_indy_page.click.assert_called()

    def test_connect_waits_for_dashboard(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que connect(session_mode='headed') attend le dashboard après login."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect(session_mode="headed")

        assert any(
            "dashboard" in str(call[0][0]) for call in mock_indy_page.wait_for_url.call_args_list
        )

    def test_connect_login_failure_raises_runtimeerror(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que login interactif échoué lève RuntimeError."""
        mock_indy_page.wait_for_url.side_effect = TimeoutError("Login page timeout")
        adapter = IndyBrowserAdapter(settings)

        with pytest.raises(RuntimeError, match="Connexion Indy échouée"):
            adapter.connect(session_mode="headed")

    def test_connect_with_session_mode_headed(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_browser: MagicMock
    ) -> None:
        """Vérifie que session_mode='headed' lance Chromium headed et appelle _login_interactive."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect(session_mode="headed")

        pw_instance = mock_indy_pw.return_value.start.return_value
        pw_instance.chromium.launch.assert_called_once_with(headless=False)

    def test_connect_with_invalid_session_mode_raises_valueerror(self, settings: Settings) -> None:
        """Vérifie que session_mode invalide lève ValueError."""
        adapter = IndyBrowserAdapter(settings)

        with pytest.raises(ValueError, match="session_mode invalide"):
            adapter.connect(session_mode="invalid_mode")

    def test_connect_headless_mode_default(
        self, settings: Settings, mock_indy_pw: MagicMock, mock_indy_browser: MagicMock
    ) -> None:
        """Vérifie que le mode par défaut est headless."""
        adapter = IndyBrowserAdapter(settings)
        adapter.connect()

        pw_instance = mock_indy_pw.return_value.start.return_value
        pw_instance.chromium.launch.assert_called_once_with(headless=True)


class TestIndyBrowserAdapterSessionPersistence:
    """Tests pour la persistance de session et 2FA."""

    def test_verify_session_returns_true_on_success(
        self, settings: Settings, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que _verify_session() retourne True si le dashboard est accessible."""
        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page

        result = adapter._verify_session()

        assert result is True
        mock_indy_page.goto.assert_called()
        mock_indy_page.wait_for_selector.assert_called()

    def test_verify_session_returns_false_on_timeout(
        self, settings: Settings, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que _verify_session() retourne False si timeout."""
        mock_indy_page.wait_for_selector.side_effect = TimeoutError("Selector not found")
        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page

        result = adapter._verify_session()

        assert result is False

    def test_verify_session_returns_false_when_page_is_none(self, settings: Settings) -> None:
        """Vérifie que _verify_session() retourne False quand page est None."""
        adapter = IndyBrowserAdapter(settings)
        adapter._page = None

        result = adapter._verify_session()

        assert result is False

    def test_login_interactive_fills_credentials(
        self, settings: Settings, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que _login_interactive() remplit email et password."""
        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page

        adapter._login_interactive()

        calls = mock_indy_page.fill.call_args_list
        assert any(call[0][1] == settings.indy_email for call in calls)
        assert any(call[0][1] == settings.indy_password for call in calls)

    def test_login_interactive_waits_for_dashboard(
        self, settings: Settings, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que _login_interactive() attend le dashboard."""
        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page

        adapter._login_interactive()

        assert mock_indy_page.wait_for_url.called

    def test_login_interactive_raises_error_if_page_is_none(self, settings: Settings) -> None:
        """Vérifie que _login_interactive() lève RuntimeError si page est None."""
        adapter = IndyBrowserAdapter(settings)
        adapter._page = None

        with pytest.raises(RuntimeError, match="Page non initialisee"):
            adapter._login_interactive()

    def test_login_interactive_timeout_on_2fa(
        self, settings: Settings, mock_indy_page: MagicMock
    ) -> None:
        """Vérifie que _login_interactive() timeout après 2 min sans 2FA."""
        mock_indy_page.wait_for_url.side_effect = TimeoutError("2FA timeout")
        adapter = IndyBrowserAdapter(settings)
        adapter._page = mock_indy_page

        with pytest.raises(TimeoutError):
            adapter._login_interactive()

        # Screenshot on error may be attempted depending on implementation


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
# Tests AISAPIAdapter (REST API)
# ============================================================================


class TestAISAPIAdapterInit:
    """Tests pour l'initialisation de AISAPIAdapter."""

    def test_init_stores_settings(self, settings: Settings) -> None:
        """Vérifie que __init__ stocke les settings et crée un client httpx."""
        adapter = AISAPIAdapter(settings)

        assert adapter._settings == settings
        assert adapter._token is None
        assert adapter._client is not None

    def test_init_sets_timeout(self, settings: Settings) -> None:
        """Vérifie que __init__ configure le timeout httpx."""
        adapter = AISAPIAdapter(settings)
        expected_timeout = float(settings.ais_timeout_sec)
        timeout_dict = adapter._client.timeout.as_dict()
        assert timeout_dict["read"] == expected_timeout


class TestAISAPIAdapterConnect:
    """Tests pour la connexion AIS REST API."""

    def test_connect_calls_get_token_with_retry(self, settings: Settings) -> None:
        """Vérifie que connect() appelle _get_token_with_retry()."""
        adapter = AISAPIAdapter(settings)

        with patch.object(adapter, "_get_token_with_retry", return_value="token123"):
            adapter.connect()

            assert adapter._token == "token123"

    def test_connect_logs_success(self, settings: Settings) -> None:
        """Vérifie que connect() log le succès."""
        adapter = AISAPIAdapter(settings)

        with (
            patch.object(adapter, "_get_token_with_retry", return_value="token123"),
            patch("src.adapters.ais_adapter.logger") as mock_logger,
        ):
            adapter.connect()

            mock_logger.info.assert_called_with("AIS login successful")


class TestAISAPIAdapterGetClients:
    """Tests pour la récupération des clients (REST)."""

    def test_get_clients_returns_list(self, settings: Settings) -> None:
        """Vérifie que get_clients() retourne une liste de dicts mappés."""
        adapter = AISAPIAdapter(settings)
        adapter._token = "token123"

        mock_response_data = [
            {
                "_id": "C001",
                "firstName": "Alice",
                "lastName": "Dupont",
                "email": "alice@test.fr",
                "status": "INSCRIT",
            },
            {
                "_id": "C002",
                "firstName": "Bob",
                "lastName": "Martin",
                "email": "bob@test.fr",
                "status": "EN_ATTENTE",
            },
        ]

        with patch.object(adapter, "_read_collection", return_value=mock_response_data):
            result = adapter.get_clients()

            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]["client_id"] == "C001"
            assert result[0]["nom"] == "Dupont"
            assert result[1]["email"] == "bob@test.fr"

    def test_get_clients_deduplicates_by_id(self, settings: Settings) -> None:
        """Vérifie que get_clients() déduplique par client_id."""
        adapter = AISAPIAdapter(settings)
        adapter._token = "token123"

        mock_response_data = [
            {"_id": "C001", "firstName": "Alice", "lastName": "Dupont", "email": "a@test.fr"},
            {"_id": "C001", "firstName": "Alice", "lastName": "Dupont", "email": "a@test.fr"},
        ]

        with patch.object(adapter, "_read_collection", return_value=mock_response_data):
            result = adapter.get_clients()

            assert len(result) == 1


class TestAISAPIAdapterGetInvoices:
    """Tests pour la récupération des factures (REST)."""

    def test_get_invoices_returns_list(self, settings: Settings) -> None:
        """Vérifie que get_invoices() retourne une liste de dicts."""
        adapter = AISAPIAdapter(settings)
        adapter._token = "token123"

        mock_response_data = [
            {
                "demande_id": "DEMANDE-001",
                "statut": "EN_ATTENTE",
                "client_id": "C001",
                "montant": 500.00,
                "date": "2026-03-21T10:00:00Z",
            },
            {
                "demande_id": "DEMANDE-002",
                "statut": "PAYEE",
                "client_id": "C002",
                "montant": 1000.00,
                "date": "2026-03-20T10:00:00Z",
            },
        ]

        with patch.object(adapter, "get_invoice_statuses", return_value=mock_response_data):
            result = adapter.get_invoices()

            assert isinstance(result, list)
            assert len(result) == 2

    def test_get_invoices_with_status_filter(self, settings: Settings) -> None:
        """Vérifie que get_invoices(status=...) filtre par statut."""
        adapter = AISAPIAdapter(settings)
        adapter._token = "token123"

        mock_response_data = [
            {"demande_id": "DEMANDE-001", "statut": "EN_ATTENTE", "montant": 500.00},
            {"demande_id": "DEMANDE-002", "statut": "PAYEE", "montant": 1000.00},
        ]

        with patch.object(adapter, "get_invoice_statuses", return_value=mock_response_data):
            result = adapter.get_invoices(status="PAYEE")

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["statut"] == "PAYEE"


class TestAISAPIAdapterGetInvoiceStatus:
    """Tests pour la récupération du statut d'une facture (REST)."""

    def test_get_invoice_status_returns_status_string(self, settings: Settings) -> None:
        """Vérifie que get_invoice_status() retourne un string de statut."""
        adapter = AISAPIAdapter(settings)
        adapter._token = "token123"

        mock_invoices = [
            {"demande_id": "DEMANDE-001", "statut": "PAYEE", "montant": 500.00},
            {"demande_id": "DEMANDE-002", "statut": "EN_ATTENTE", "montant": 1000.00},
        ]

        with patch.object(adapter, "get_invoice_statuses", return_value=mock_invoices):
            result = adapter.get_invoice_status("DEMANDE-001")

            assert isinstance(result, str)
            assert result == "PAYEE"

    def test_get_invoice_status_raises_valueerror_if_not_found(self, settings: Settings) -> None:
        """Vérifie que get_invoice_status() lève ValueError si demande_id non trouvée."""
        adapter = AISAPIAdapter(settings)
        adapter._token = "token123"

        mock_invoices = [
            {"demande_id": "DEMANDE-001", "statut": "PAYEE", "montant": 500.00},
        ]

        with (
            patch.object(adapter, "get_invoice_statuses", return_value=mock_invoices),
            pytest.raises(ValueError, match="non trouvée"),
        ):
            adapter.get_invoice_status("INEXISTANT")


class TestAISAPIAdapterSubmitInvoice:
    """Tests pour la soumission d'une facture (INTERDIT)."""

    def test_submit_invoice_raises_notimplementederror(self, settings: Settings) -> None:
        """Vérifie que submit_invoice() lève NotImplementedError (INTERDIT)."""
        adapter = AISAPIAdapter(settings)
        invoice_data = {"montant": 1000, "client_id": "C001"}

        with pytest.raises(NotImplementedError, match="INTERDIT"):
            adapter.submit_invoice("C001", invoice_data)


class TestAISAPIAdapterRegisterClient:
    """Tests pour l'inscription d'un nouveau client (INTERDIT)."""

    def test_register_client_raises_notimplementederror(self, settings: Settings) -> None:
        """Vérifie que register_client() lève NotImplementedError (INTERDIT)."""
        adapter = AISAPIAdapter(settings)
        client_data = {"nom": "Dupont", "email": "dupont@test.fr"}

        with pytest.raises(NotImplementedError, match="INTERDIT"):
            adapter.register_client(client_data)


class TestAISAPIAdapterClose:
    """Tests pour la fermeture de la connexion httpx."""

    def test_close_closes_httpx_client(self, settings: Settings) -> None:
        """Vérifie que close() ferme le client httpx."""
        adapter = AISAPIAdapter(settings)
        adapter._client = MagicMock()
        adapter._token = "token123"

        adapter.close()

        adapter._client.close.assert_called_once()

    def test_close_nullifies_token(self, settings: Settings) -> None:
        """Vérifie que close() annule le token."""
        adapter = AISAPIAdapter(settings)
        adapter._token = "token123"
        adapter._client = MagicMock()

        adapter.close()

        assert adapter._token is None

    def test_close_idempotent_when_no_client(self, settings: Settings) -> None:
        """Vérifie que close() est idempotent."""
        adapter = AISAPIAdapter(settings)
        adapter._client = None
        adapter._token = None

        adapter.close()

        assert adapter._token is None
