"""Tests TDD RED — CLI sap status."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import polars as pl
from click.testing import CliRunner

from src.cli import main
from src.models.invoice import InvoiceStatus


class TestStatusShowsInvoiceCounts:
    """Test: sap status displays invoice count by status."""

    def test_status_shows_invoice_counts(self) -> None:
        """Invoice counts displayed for each status present."""
        # Arrange
        runner = CliRunner()
        mock_sheets = MagicMock()

        # Create test data: 3 EN_ATTENTE, 2 PAYE, 1 VALIDE
        invoices_df = pl.DataFrame(
            {
                "facture_id": ["F001", "F002", "F003", "F004", "F005", "F006"],
                "client_id": ["C001", "C001", "C001", "C002", "C002", "C003"],
                "statut": [
                    InvoiceStatus.EN_ATTENTE,
                    InvoiceStatus.EN_ATTENTE,
                    InvoiceStatus.EN_ATTENTE,
                    InvoiceStatus.PAYE,
                    InvoiceStatus.PAYE,
                    InvoiceStatus.VALIDE,
                ],
                "quantite": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
                "montant_unitaire": [50.0] * 6,
                "montant_total": [50.0, 100.0, 150.0, 200.0, 250.0, 300.0],
                "date_debut": ["2026-01-01"] * 6,
                "date_fin": ["2026-01-31"] * 6,
                "date_soumission": ["2026-01-01"] * 6,
                "date_validation": [None] * 6,
                "date_paiement": [None] * 6,
            }
        )
        mock_sheets.get_all_invoices.return_value = invoices_df

        # Balances with balance calculation
        balances_df = pl.DataFrame(
            {
                "mois": ["2026-01"],
                "nb_factures": [6],
                "ca_total": [1050.0],
                "recu_urssaf": [450.0],
                "solde": [600.0],
                "nb_non_lettrees": [0],
                "nb_en_attente": [4],
            }
        )
        mock_sheets.get_all_balances.return_value = balances_df

        mock_sheets.get_cache_stats.return_value = {"hits": 0, "misses": 0}

        # Act
        with patch("src.adapters.sheets_adapter.SheetsAdapter", return_value=mock_sheets):
            result = runner.invoke(main, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "EN_ATTENTE: 3" in result.output
        assert "PAYE: 2" in result.output
        assert "VALIDE: 1" in result.output

    def test_status_with_empty_invoices(self) -> None:
        """Handle empty invoice sheet gracefully."""
        runner = CliRunner()
        mock_sheets = MagicMock()

        # Empty invoices
        invoices_df = pl.DataFrame(
            {
                "facture_id": [],
                "client_id": [],
                "statut": [],
                "quantite": [],
                "montant_unitaire": [],
                "montant_total": [],
                "date_debut": [],
                "date_fin": [],
                "date_soumission": [],
                "date_validation": [],
                "date_paiement": [],
            }
        )
        mock_sheets.get_all_invoices.return_value = invoices_df

        # Empty balances
        balances_df = pl.DataFrame(
            {
                "mois": [],
                "nb_factures": [],
                "ca_total": [],
                "recu_urssaf": [],
                "solde": [],
                "nb_non_lettrees": [],
                "nb_en_attente": [],
            }
        )
        mock_sheets.get_all_balances.return_value = balances_df

        mock_sheets.get_cache_stats.return_value = {"hits": 0, "misses": 0}

        # Act
        with patch("src.adapters.sheets_adapter.SheetsAdapter", return_value=mock_sheets):
            result = runner.invoke(main, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "No invoices found" in result.output or "0 invoices" in result.output.lower()


class TestStatusShowsOverdueAlert:
    """Test: sap status detects invoices EN_ATTENTE > 36h."""

    def test_status_shows_overdue_alert(self) -> None:
        """Invoices EN_ATTENTE submitted > 36h ago trigger alert."""
        runner = CliRunner()
        mock_sheets = MagicMock()

        # Create invoice submitted 48 hours ago (overdue)
        now = datetime.now()
        submitted_48h_ago = (now - timedelta(hours=48)).strftime("%Y-%m-%d")

        invoices_df = pl.DataFrame(
            {
                "facture_id": ["F001"],
                "client_id": ["C001"],
                "statut": [InvoiceStatus.EN_ATTENTE],
                "quantite": [1.0],
                "montant_unitaire": [50.0],
                "montant_total": [50.0],
                "date_debut": ["2026-01-01"],
                "date_fin": ["2026-01-31"],
                "date_soumission": [submitted_48h_ago],
                "date_validation": [None],
                "date_paiement": [None],
            }
        )
        mock_sheets.get_all_invoices.return_value = invoices_df

        balances_df = pl.DataFrame(
            {
                "mois": ["2026-01"],
                "nb_factures": [1],
                "ca_total": [50.0],
                "recu_urssaf": [0.0],
                "solde": [50.0],
                "nb_non_lettrees": [0],
                "nb_en_attente": [1],
            }
        )
        mock_sheets.get_all_balances.return_value = balances_df

        mock_sheets.get_cache_stats.return_value = {"hits": 0, "misses": 0}

        # Act
        with patch("src.adapters.sheets_adapter.SheetsAdapter", return_value=mock_sheets):
            result = runner.invoke(main, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "ALERT" in result.output or "overdue" in result.output.lower()

    def test_status_no_alert_for_recent_en_attente(self) -> None:
        """Invoices EN_ATTENTE submitted < 36h ago do NOT alert."""
        runner = CliRunner()
        mock_sheets = MagicMock()

        # Create invoice submitted 12 hours ago (not overdue)
        now = datetime.now()
        submitted_12h_ago = (now - timedelta(hours=12)).strftime("%Y-%m-%d")

        invoices_df = pl.DataFrame(
            {
                "facture_id": ["F001"],
                "client_id": ["C001"],
                "statut": [InvoiceStatus.EN_ATTENTE],
                "quantite": [1.0],
                "montant_unitaire": [50.0],
                "montant_total": [50.0],
                "date_debut": ["2026-01-01"],
                "date_fin": ["2026-01-31"],
                "date_soumission": [submitted_12h_ago],
                "date_validation": [None],
                "date_paiement": [None],
            }
        )
        mock_sheets.get_all_invoices.return_value = invoices_df

        balances_df = pl.DataFrame(
            {
                "mois": ["2026-01"],
                "nb_factures": [1],
                "ca_total": [50.0],
                "recu_urssaf": [0.0],
                "solde": [50.0],
                "nb_non_lettrees": [0],
                "nb_en_attente": [1],
            }
        )
        mock_sheets.get_all_balances.return_value = balances_df

        mock_sheets.get_cache_stats.return_value = {"hits": 0, "misses": 0}

        # Act
        with patch("src.adapters.sheets_adapter.SheetsAdapter", return_value=mock_sheets):
            result = runner.invoke(main, ["status"])

        # Assert
        assert result.exit_code == 0
        # No alert should be raised
        assert "ALERT" not in result.output or "overdue" not in result.output.lower()


class TestStatusShowsBalance:
    """Test: sap status displays balance (CA - charges)."""

    def test_status_shows_balance(self) -> None:
        """Balance displayed from Balances sheet (solde = CA - recu)."""
        runner = CliRunner()
        mock_sheets = MagicMock()

        invoices_df = pl.DataFrame(
            {
                "facture_id": ["F001"],
                "client_id": ["C001"],
                "statut": [InvoiceStatus.PAYE],
                "quantite": [10.0],
                "montant_unitaire": [100.0],
                "montant_total": [1000.0],
                "date_debut": ["2026-01-01"],
                "date_fin": ["2026-01-31"],
                "date_soumission": ["2026-01-01"],
                "date_validation": ["2026-01-05"],
                "date_paiement": ["2026-01-10"],
            }
        )
        mock_sheets.get_all_invoices.return_value = invoices_df

        # CA: 1000, Received: 600, Balance: 400
        balances_df = pl.DataFrame(
            {
                "mois": ["2026-01"],
                "nb_factures": [1],
                "ca_total": [1000.0],
                "recu_urssaf": [600.0],
                "solde": [400.0],
                "nb_non_lettrees": [0],
                "nb_en_attente": [0],
            }
        )
        mock_sheets.get_all_balances.return_value = balances_df

        mock_sheets.get_cache_stats.return_value = {"hits": 0, "misses": 0}

        # Act
        with patch("src.adapters.sheets_adapter.SheetsAdapter", return_value=mock_sheets):
            result = runner.invoke(main, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "Balance" in result.output or "balance" in result.output
        assert "400" in result.output or "1000" in result.output


class TestStatusShowsLastSync:
    """Test: sap status displays last AIS sync timestamp."""

    def test_status_shows_last_sync_timestamp(self) -> None:
        """Last sync timestamp loaded from cache stats or metadata."""
        runner = CliRunner()
        mock_sheets = MagicMock()

        invoices_df = pl.DataFrame(
            {
                "facture_id": ["F001"],
                "client_id": ["C001"],
                "statut": [InvoiceStatus.PAYE],
                "quantite": [1.0],
                "montant_unitaire": [50.0],
                "montant_total": [50.0],
                "date_debut": ["2026-01-01"],
                "date_fin": ["2026-01-31"],
                "date_soumission": ["2026-01-01"],
                "date_validation": ["2026-01-05"],
                "date_paiement": ["2026-01-10"],
            }
        )
        mock_sheets.get_all_invoices.return_value = invoices_df

        balances_df = pl.DataFrame(
            {
                "mois": ["2026-01"],
                "nb_factures": [1],
                "ca_total": [50.0],
                "recu_urssaf": [0.0],
                "solde": [50.0],
                "nb_non_lettrees": [0],
                "nb_en_attente": [0],
            }
        )
        mock_sheets.get_all_balances.return_value = balances_df

        # Cache stats indicate when last read occurred
        mock_sheets.get_cache_stats.return_value = {"hits": 5, "misses": 2}

        # Act
        with patch("src.adapters.sheets_adapter.SheetsAdapter", return_value=mock_sheets):
            result = runner.invoke(main, ["status"])

        # Assert
        assert result.exit_code == 0
        assert "sync" in result.output.lower() or "last" in result.output.lower()


class TestStatusExitCode:
    """Test: sap status exit code is 0."""

    def test_status_exit_code_0_on_success(self) -> None:
        """Exit code is 0 when status runs successfully."""
        runner = CliRunner()
        mock_sheets = MagicMock()

        invoices_df = pl.DataFrame(
            {
                "facture_id": [],
                "client_id": [],
                "statut": [],
                "quantite": [],
                "montant_unitaire": [],
                "montant_total": [],
                "date_debut": [],
                "date_fin": [],
                "date_soumission": [],
                "date_validation": [],
                "date_paiement": [],
            }
        )
        mock_sheets.get_all_invoices.return_value = invoices_df

        balances_df = pl.DataFrame(
            {
                "mois": [],
                "nb_factures": [],
                "ca_total": [],
                "recu_urssaf": [],
                "solde": [],
                "nb_non_lettrees": [],
                "nb_en_attente": [],
            }
        )
        mock_sheets.get_all_balances.return_value = balances_df

        mock_sheets.get_cache_stats.return_value = {"hits": 0, "misses": 0}

        # Act
        with patch("src.adapters.sheets_adapter.SheetsAdapter", return_value=mock_sheets):
            result = runner.invoke(main, ["status"])

        # Assert
        assert result.exit_code == 0


class TestStatusVerboseMode:
    """Test: sap status respects --verbose flag."""

    def test_status_with_verbose_flag(self) -> None:
        """Verbose mode shows additional details."""
        runner = CliRunner()
        mock_sheets = MagicMock()

        invoices_df = pl.DataFrame(
            {
                "facture_id": ["F001"],
                "client_id": ["C001"],
                "statut": [InvoiceStatus.PAYE],
                "quantite": [1.0],
                "montant_unitaire": [50.0],
                "montant_total": [50.0],
                "date_debut": ["2026-01-01"],
                "date_fin": ["2026-01-31"],
                "date_soumission": ["2026-01-01"],
                "date_validation": ["2026-01-05"],
                "date_paiement": ["2026-01-10"],
            }
        )
        mock_sheets.get_all_invoices.return_value = invoices_df

        balances_df = pl.DataFrame(
            {
                "mois": ["2026-01"],
                "nb_factures": [1],
                "ca_total": [50.0],
                "recu_urssaf": [0.0],
                "solde": [50.0],
                "nb_non_lettrees": [0],
                "nb_en_attente": [0],
            }
        )
        mock_sheets.get_all_balances.return_value = balances_df

        mock_sheets.get_cache_stats.return_value = {"hits": 10, "misses": 3}

        # Act
        with patch("src.adapters.sheets_adapter.SheetsAdapter", return_value=mock_sheets):
            result = runner.invoke(main, ["--verbose", "status"])

        # Assert
        assert result.exit_code == 0
        # In verbose mode, should show cache hits/misses
        assert "cache" in result.output.lower() or "hits" in result.output.lower()


class TestStatusDryRunMode:
    """Test: sap status respects --dry-run flag."""

    def test_status_with_dry_run_flag(self) -> None:
        """Dry-run flag doesn't modify state."""
        runner = CliRunner()
        mock_sheets = MagicMock()

        invoices_df = pl.DataFrame(
            {
                "facture_id": ["F001"],
                "client_id": ["C001"],
                "statut": [InvoiceStatus.PAYE],
                "quantite": [1.0],
                "montant_unitaire": [50.0],
                "montant_total": [50.0],
                "date_debut": ["2026-01-01"],
                "date_fin": ["2026-01-31"],
                "date_soumission": ["2026-01-01"],
                "date_validation": ["2026-01-05"],
                "date_paiement": ["2026-01-10"],
            }
        )
        mock_sheets.get_all_invoices.return_value = invoices_df

        balances_df = pl.DataFrame(
            {
                "mois": ["2026-01"],
                "nb_factures": [1],
                "ca_total": [50.0],
                "recu_urssaf": [0.0],
                "solde": [50.0],
                "nb_non_lettrees": [0],
                "nb_en_attente": [0],
            }
        )
        mock_sheets.get_all_balances.return_value = balances_df

        mock_sheets.get_cache_stats.return_value = {"hits": 0, "misses": 0}

        # Act
        with patch("src.adapters.sheets_adapter.SheetsAdapter", return_value=mock_sheets):
            result = runner.invoke(main, ["--dry-run", "status"])

        # Assert
        assert result.exit_code == 0
        # No modifications should happen
        mock_sheets.add_invoice.assert_not_called()
        mock_sheets.update_invoice.assert_not_called()
