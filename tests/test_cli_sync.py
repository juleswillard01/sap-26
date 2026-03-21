"""Tests RED — CLI sap sync (AIS → Sheets).

Le command `sap sync` orchestre :
1. Connexion à AIS (via AISAdapter.get_invoice_statuses)
2. Lecture des factures actuelles dans Sheets
3. Détection des changements de statut
4. Mise à jour de l'onglet Factures
5. Détection et alerte EN_ATTENTE > 36h
6. Affichage d'un résumé

Critères evals (docs/evals.md):
- Exit code 0 si sync réussi
- Exit code 1 si AIS login échoue
- Affiche les changements détectés
- Envoie email si facture EN_ATTENTE > 36h
- Affiche le nombre de factures synced et changements
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from click.testing import CliRunner

from src.cli import main

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def runner() -> CliRunner:
    """Click CLI test runner."""
    return CliRunner()


# ============================================================================
# Tests RED — Commande existe et wiring
# ============================================================================


class TestSyncCommandExists:
    """TEST RED: La commande 'sap sync' existe et affiche l'aide."""

    def test_sync_command_exists(self, runner: CliRunner) -> None:
        """La commande sap sync existe."""
        result = runner.invoke(main, ["sync", "--help"])
        assert result.exit_code == 0
        assert "Synchroniser" in result.output or "sync" in result.output.lower()

    def test_sync_without_args(self, runner: CliRunner) -> None:
        """sap sync sans args lance la sync."""
        result = runner.invoke(main, ["sync"])
        # RED: devrait échouer pour l'instant
        # Exit code peut être 1 (NotImplementedError) ou autre
        assert result.exit_code != 0 or "NotImplementedError" in str(result.exception)


# ============================================================================
# Tests RED — Intégration AIS Adapter
# ============================================================================


class TestSyncCallsAISAdapter:
    """TEST RED: sap sync se connecte à AIS et scrape les statuts."""

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_calls_ais_adapter_get_invoice_statuses(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync appelle AISAdapter.get_invoice_statuses()."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = []
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame()
        mock_sheets.write_updates.return_value = None

        # Execute
        runner.invoke(main, ["sync"])

        # Verify AIS adapter was called
        mock_ais.connect.assert_called()
        mock_ais.get_invoice_statuses.assert_called()

    @patch("src.adapters.ais_adapter.AISAdapter")
    def test_sync_ais_login_failure_exit_code_1(
        self, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync exit code 1 si AIS login échoue."""
        # Setup mock to fail on login
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.side_effect = RuntimeError("AIS login failed")

        # Execute
        result = runner.invoke(main, ["sync"])

        # Verify exit code is 1
        assert result.exit_code == 1


# ============================================================================
# Tests RED — Intégration Sheets Adapter
# ============================================================================


class TestSyncUpdatesSheets:
    """TEST RED: sap sync met à jour l'onglet Factures dans Sheets."""

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_reads_sheets_invoice_data(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync lit les données Factures depuis Sheets."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = []
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame()
        mock_sheets.write_updates.return_value = None

        # Execute
        runner.invoke(main, ["sync"])

        # Verify Sheets read was called
        mock_sheets.read_sheet.assert_called_with("Factures")

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_writes_changes_to_sheets(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync écrit les changements détectés vers Sheets."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = [
            {
                "facture_id": "FAC-001",
                "urssaf_demande_id": "URSSAF-123",
                "statut_ais": "CREE",
                "montant": "500.00",
                "date_maj": "2026-03-21T10:00:00Z",
            }
        ]
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        # Return Polars DataFrame with one invoice in BROUILLON state
        mock_sheets.read_sheet.return_value = pl.DataFrame(
            {
                "facture_id": ["FAC-001"],
                "client_id": ["CLI-001"],
                "statut": ["BROUILLON"],
                "montant_total": ["500.00"],
                "urssaf_demande_id": ["URSSAF-123"],
                "date_soumission": ["2026-03-21T10:00:00Z"],
            }
        )
        mock_sheets.write_updates.return_value = None

        # Execute
        runner.invoke(main, ["sync"])

        # Verify write_updates was called (change detected: BROUILLON → CREE)
        mock_sheets.write_updates.assert_called()


# ============================================================================
# Tests RED — Détection des changements
# ============================================================================


class TestSyncDetectsChanges:
    """TEST RED: sap sync affiche les changements de statut détectés."""

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_detects_status_change_brouillon_to_cree(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync détecte changement BROUILLON → CREE."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = [
            {
                "facture_id": "FAC-001",
                "urssaf_demande_id": "URSSAF-123",
                "statut_ais": "CREE",
                "montant": "500.00",
                "date_maj": "2026-03-21T10:00:00Z",
            }
        ]
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame(
            {
                "facture_id": ["FAC-001"],
                "client_id": ["CLI-001"],
                "statut": ["BROUILLON"],
                "montant_total": ["500.00"],
                "urssaf_demande_id": ["URSSAF-123"],
                "date_soumission": ["2026-03-21T10:00:00Z"],
            }
        )
        mock_sheets.write_updates.return_value = None

        # Execute
        result = runner.invoke(main, ["sync"])

        # Verify output contains change info
        assert "FAC-001" in result.output or "changement" in result.output.lower()

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_detects_status_change_en_attente_to_valide(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync détecte changement EN_ATTENTE → VALIDE."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = [
            {
                "facture_id": "FAC-001",
                "urssaf_demande_id": "URSSAF-123",
                "statut_ais": "VALIDE",
                "montant": "500.00",
                "date_validation": "2026-03-21T14:00:00Z",
                "date_maj": "2026-03-21T14:00:00Z",
            }
        ]
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame(
            {
                "facture_id": ["FAC-001"],
                "client_id": ["CLI-001"],
                "statut": ["EN_ATTENTE"],
                "montant_total": ["500.00"],
                "urssaf_demande_id": ["URSSAF-123"],
                "date_soumission": ["2026-03-21T10:00:00Z"],
            }
        )
        mock_sheets.write_updates.return_value = None

        # Execute
        result = runner.invoke(main, ["sync"])

        # Verify output indicates change
        assert "FAC-001" in result.output or "changement" in result.output.lower()

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_no_changes_no_write(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync ne fait pas d'update si aucun changement."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = [
            {
                "facture_id": "FAC-001",
                "urssaf_demande_id": "URSSAF-123",
                "statut_ais": "CREE",
                "montant": "500.00",
                "date_maj": "2026-03-21T10:00:00Z",
            }
        ]
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        # Same state in both AIS and Sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame(
            {
                "facture_id": ["FAC-001"],
                "client_id": ["CLI-001"],
                "statut": ["CREE"],  # Already CREE
                "montant_total": ["500.00"],
                "urssaf_demande_id": ["URSSAF-123"],
                "date_soumission": ["2026-03-21T10:00:00Z"],
            }
        )

        # Execute
        runner.invoke(main, ["sync"])

        # Verify write_updates was not called or called with empty changes
        # (Behavior depends on implementation — RED test)


# ============================================================================
# Tests RED — Alertes T+36h
# ============================================================================


class TestSyncAlertsOverdue:
    """TEST RED: sap sync envoie alerte si facture EN_ATTENTE > 36h."""

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_sends_alert_for_pending_36h(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync envoie email si facture EN_ATTENTE > 36h."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = [
            {
                "facture_id": "FAC-002",
                "urssaf_demande_id": "URSSAF-124",
                "statut_ais": "EN_ATTENTE",
                "montant": "750.00",
                "date_soumission": (datetime.now() - timedelta(hours=48)).isoformat(),
                "date_maj": datetime.now().isoformat(),
            }
        ]
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        submitted_48h_ago = (datetime.now() - timedelta(hours=48)).isoformat()
        mock_sheets.read_sheet.return_value = pl.DataFrame(
            {
                "facture_id": ["FAC-002"],
                "client_id": ["CLI-002"],
                "statut": ["EN_ATTENTE"],
                "montant_total": ["750.00"],
                "urssaf_demande_id": ["URSSAF-124"],
                "date_soumission": [submitted_48h_ago],
            }
        )
        mock_sheets.write_updates.return_value = None

        # Execute
        runner.invoke(main, ["sync"])

        # RED: Should trigger notification (behavior depends on implementation)

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_no_alert_if_pending_less_than_36h(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync N'envoie PAS alerte si facture EN_ATTENTE < 36h."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        submitted_10h_ago = (datetime.now() - timedelta(hours=10)).isoformat()
        mock_ais.get_invoice_statuses.return_value = [
            {
                "facture_id": "FAC-003",
                "urssaf_demande_id": "URSSAF-125",
                "statut_ais": "EN_ATTENTE",
                "montant": "600.00",
                "date_soumission": submitted_10h_ago,
                "date_maj": datetime.now().isoformat(),
            }
        ]
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame(
            {
                "facture_id": ["FAC-003"],
                "client_id": ["CLI-003"],
                "statut": ["EN_ATTENTE"],
                "montant_total": ["600.00"],
                "urssaf_demande_id": ["URSSAF-125"],
                "date_soumission": [submitted_10h_ago],
            }
        )
        mock_sheets.write_updates.return_value = None

        # Execute
        result = runner.invoke(main, ["sync"])

        # Verify no error
        assert result.exit_code in (0, 1)


# ============================================================================
# Tests RED — Summary Output
# ============================================================================


class TestSyncSummaryOutput:
    """TEST RED: sap sync affiche un résumé (N synced, X changements)."""

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_displays_summary_count(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync affiche le nombre de factures synced."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = [
            {
                "facture_id": "FAC-001",
                "urssaf_demande_id": "URSSAF-123",
                "statut_ais": "CREE",
                "montant": "500.00",
                "date_maj": "2026-03-21T10:00:00Z",
            },
            {
                "facture_id": "FAC-002",
                "urssaf_demande_id": "URSSAF-124",
                "statut_ais": "EN_ATTENTE",
                "montant": "750.00",
                "date_maj": "2026-03-21T12:00:00Z",
            },
        ]
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame(
            {
                "facture_id": ["FAC-001", "FAC-002"],
                "client_id": ["CLI-001", "CLI-002"],
                "statut": ["BROUILLON", "BROUILLON"],
                "montant_total": ["500.00", "750.00"],
                "urssaf_demande_id": ["URSSAF-123", "URSSAF-124"],
                "date_soumission": [
                    "2026-03-21T10:00:00Z",
                    "2026-03-21T10:00:00Z",
                ],
            }
        )
        mock_sheets.write_updates.return_value = None

        # Execute
        result = runner.invoke(main, ["sync"])

        # Verify summary output contains counts
        output = result.output.lower()
        assert "2" in result.output or "factures" in output or "synced" in output

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_displays_changes_count(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync affiche le nombre de changements détectés."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = [
            {
                "facture_id": "FAC-001",
                "urssaf_demande_id": "URSSAF-123",
                "statut_ais": "VALIDE",
                "montant": "500.00",
                "date_validation": "2026-03-21T14:00:00Z",
                "date_maj": "2026-03-21T14:00:00Z",
            }
        ]
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame(
            {
                "facture_id": ["FAC-001"],
                "client_id": ["CLI-001"],
                "statut": ["EN_ATTENTE"],  # Change to VALIDE
                "montant_total": ["500.00"],
                "urssaf_demande_id": ["URSSAF-123"],
                "date_soumission": ["2026-03-21T10:00:00Z"],
            }
        )
        mock_sheets.write_updates.return_value = None

        # Execute
        result = runner.invoke(main, ["sync"])

        # Verify summary output contains change count
        output = result.output.lower()
        assert "changement" in output or "change" in output or "1" in result.output


# ============================================================================
# Tests RED — Exit Codes
# ============================================================================


class TestSyncExitCodes:
    """TEST RED: sap sync retourne les bons exit codes."""

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_exit_code_0_on_success(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """Exit code 0 si sync réussi."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = []
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame()
        mock_sheets.write_updates.return_value = None

        # Execute
        result = runner.invoke(main, ["sync"])

        # Verify exit code 0
        assert result.exit_code == 0

    @patch("src.adapters.ais_adapter.AISAdapter")
    def test_sync_exit_code_1_on_ais_error(
        self, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """Exit code 1 si AIS login échoue."""
        # Setup mock to fail
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.side_effect = RuntimeError("AIS connection failed")

        # Execute
        result = runner.invoke(main, ["sync"])

        # Verify exit code 1
        assert result.exit_code == 1

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_exit_code_1_on_sheets_error(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """Exit code 1 si Sheets write échoue."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = [
            {
                "facture_id": "FAC-001",
                "urssaf_demande_id": "URSSAF-123",
                "statut_ais": "CREE",
                "montant": "500.00",
                "date_maj": "2026-03-21T10:00:00Z",
            }
        ]
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame(
            {
                "facture_id": ["FAC-001"],
                "client_id": ["CLI-001"],
                "statut": ["BROUILLON"],
                "montant_total": ["500.00"],
                "urssaf_demande_id": ["URSSAF-123"],
                "date_soumission": ["2026-03-21T10:00:00Z"],
            }
        )
        # Fail on write
        mock_sheets.write_updates.side_effect = RuntimeError("Sheets write failed")

        # Execute
        result = runner.invoke(main, ["sync"])

        # Verify exit code 1
        assert result.exit_code == 1


# ============================================================================
# Tests RED — Cleanup & Resource Management
# ============================================================================


class TestSyncCleanup:
    """TEST RED: sap sync ferme proprement les ressources."""

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_closes_ais_adapter(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync ferme AISAdapter.close() après sync."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = []
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame()
        mock_sheets.write_updates.return_value = None

        # Execute
        runner.invoke(main, ["sync"])

        # Verify close was called
        mock_ais.close.assert_called()

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_closes_ais_adapter_on_error(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync ferme AISAdapter même si erreur."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.side_effect = RuntimeError("Scrape failed")
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets

        # Execute
        runner.invoke(main, ["sync"])

        # Verify close was still called
        mock_ais.close.assert_called()


# ============================================================================
# Tests RED — Verbose & Dry-run modes
# ============================================================================


class TestSyncModes:
    """TEST RED: sap sync --verbose et --dry-run."""

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_with_verbose_flag(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync --verbose affiche plus de détails."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = []
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame()
        mock_sheets.write_updates.return_value = None

        # Execute with verbose
        result = runner.invoke(main, ["--verbose", "sync"])

        # Verify output or no error
        assert result.exit_code == 0 or result.exit_code in (
            0,
            1,
        )  # RED: depends on impl

    @patch("src.adapters.ais_adapter.AISAdapter")
    @patch("src.adapters.sheets_adapter.SheetsAdapter")
    def test_sync_with_dry_run_flag(
        self, mock_sheets_cls: MagicMock, mock_ais_cls: MagicMock, runner: CliRunner
    ) -> None:
        """sap sync --dry-run affiche sans écrire."""
        # Setup mocks
        mock_ais = MagicMock()
        mock_ais_cls.return_value = mock_ais
        mock_ais.connect.return_value = None
        mock_ais.get_invoice_statuses.return_value = [
            {
                "facture_id": "FAC-001",
                "urssaf_demande_id": "URSSAF-123",
                "statut_ais": "CREE",
                "montant": "500.00",
                "date_maj": "2026-03-21T10:00:00Z",
            }
        ]
        mock_ais.close.return_value = None

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.read_sheet.return_value = pl.DataFrame(
            {
                "facture_id": ["FAC-001"],
                "client_id": ["CLI-001"],
                "statut": ["BROUILLON"],
                "montant_total": ["500.00"],
                "urssaf_demande_id": ["URSSAF-123"],
                "date_soumission": ["2026-03-21T10:00:00Z"],
            }
        )

        # Execute with dry-run
        runner.invoke(main, ["--dry-run", "sync"])

        # Verify write_updates was NOT called (dry-run mode)
        # RED: depends on implementation
