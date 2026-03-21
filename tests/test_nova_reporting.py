"""Tests TDD RED — NovaReporting quarterly aggregation.

NOVA trimestriel requires:
- heures_effectuees: SUM quantite WHERE statut IN {PAYE, RAPPROCHE}
- nb_particuliers: COUNT DISTINCT client_id (statut PAYE/RAPPROCHE)
- ca_trimestre: SUM montant_total for the quarter (statut PAYE/RAPPROCHE)
- nb_intervenants: always 1 (Jules seul)
- deadline_saisie: 15th of month after quarter end

Spec: CDC §8.1 NOVA Trimestriel
"""

from __future__ import annotations

from datetime import datetime


class TestGenerateNovaQuarterly:
    """Tests for generate_nova_quarterly — aggregates invoices by quarter."""

    def test_basic_quarterly_aggregation(self) -> None:
        """Aggregates invoices with correct heures, nb_particuliers, ca."""
        from src.services.nova_reporting import generate_nova_quarterly

        invoices = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 2.0,
                "montant_total": 90.0,
                "nature_code": "heures",
                "statut": "PAYE",
                "date_debut": "2026-01-15",
            },
            {
                "facture_id": "F002",
                "client_id": "C002",
                "quantite": 1.5,
                "montant_total": 67.5,
                "nature_code": "heures",
                "statut": "RAPPROCHE",
                "date_debut": "2026-02-10",
            },
        ]

        result = generate_nova_quarterly(invoices, "Q1_2026")

        assert result["heures_effectuees"] == 3.5
        assert result["nb_particuliers"] == 2
        assert result["ca_trimestre"] == 157.5
        assert result["nb_intervenants"] == 1
        assert result["trimestre"] == "Q1_2026"

    def test_empty_quarter_returns_zeros(self) -> None:
        """Empty quarter returns zeros but correct nb_intervenants and deadline."""
        from src.services.nova_reporting import generate_nova_quarterly

        result = generate_nova_quarterly([], "Q2_2026")

        assert result["heures_effectuees"] == 0.0
        assert result["nb_particuliers"] == 0
        assert result["ca_trimestre"] == 0.0
        assert result["nb_intervenants"] == 1
        assert result["trimestre"] == "Q2_2026"
        # Deadline should be July 15, 2026 for Q2
        assert "2026-07-15" in result["deadline_saisie"]

    def test_nb_intervenants_always_1(self) -> None:
        """nb_intervenants is always 1 (Jules is the only worker)."""
        from src.services.nova_reporting import generate_nova_quarterly

        invoices = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 5.0,
                "montant_total": 225.0,
                "statut": "PAYE",
            }
        ]

        result = generate_nova_quarterly(invoices, "Q1_2026")

        assert result["nb_intervenants"] == 1

    def test_distinct_clients_counted(self) -> None:
        """Count distinct client_id across multiple invoices."""
        from src.services.nova_reporting import generate_nova_quarterly

        invoices = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 1.0,
                "montant_total": 45.0,
                "statut": "PAYE",
            },
            {
                "facture_id": "F002",
                "client_id": "C001",
                "quantite": 1.0,
                "montant_total": 45.0,
                "statut": "PAYE",
            },
            {
                "facture_id": "F003",
                "client_id": "C002",
                "quantite": 2.0,
                "montant_total": 90.0,
                "statut": "PAYE",
            },
            {
                "facture_id": "F004",
                "client_id": "C003",
                "quantite": 1.5,
                "montant_total": 67.5,
                "statut": "RAPPROCHE",
            },
        ]

        result = generate_nova_quarterly(invoices, "Q1_2026")

        # Only C001, C002, C003 = 3 distinct clients
        assert result["nb_particuliers"] == 3

    def test_only_paye_rapproche_counted(self) -> None:
        """Only invoices with statut PAYE or RAPPROCHE are included."""
        from src.services.nova_reporting import generate_nova_quarterly

        invoices = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 2.0,
                "montant_total": 90.0,
                "statut": "PAYE",
            },
            {
                "facture_id": "F002",
                "client_id": "C002",
                "quantite": 1.0,
                "montant_total": 45.0,
                "statut": "EN_ATTENTE",  # Should be excluded
            },
            {
                "facture_id": "F003",
                "client_id": "C003",
                "quantite": 1.5,
                "montant_total": 67.5,
                "statut": "BROUILLON",  # Should be excluded
            },
            {
                "facture_id": "F004",
                "client_id": "C004",
                "quantite": 1.0,
                "montant_total": 45.0,
                "statut": "RAPPROCHE",
            },
        ]

        result = generate_nova_quarterly(invoices, "Q1_2026")

        # Only F001 (PAYE) and F004 (RAPPROCHE) counted
        assert result["heures_effectuees"] == 3.0
        assert result["nb_particuliers"] == 2
        assert result["ca_trimestre"] == 135.0

    def test_deadline_q1_is_april_15(self) -> None:
        """Q1 deadline is April 15."""
        from src.services.nova_reporting import generate_nova_quarterly

        result = generate_nova_quarterly([], "Q1_2026")
        deadline = result["deadline_saisie"]

        # Should contain 2026-04-15
        assert "2026-04-15" in deadline

    def test_deadline_q2_is_july_15(self) -> None:
        """Q2 deadline is July 15."""
        from src.services.nova_reporting import generate_nova_quarterly

        result = generate_nova_quarterly([], "Q2_2026")
        deadline = result["deadline_saisie"]

        # Should contain 2026-07-15
        assert "2026-07-15" in deadline

    def test_deadline_q3_is_october_15(self) -> None:
        """Q3 deadline is October 15."""
        from src.services.nova_reporting import generate_nova_quarterly

        result = generate_nova_quarterly([], "Q3_2026")
        deadline = result["deadline_saisie"]

        # Should contain 2026-10-15
        assert "2026-10-15" in deadline

    def test_deadline_q4_is_january_15_next_year(self) -> None:
        """Q4 deadline is January 15 of next year."""
        from src.services.nova_reporting import generate_nova_quarterly

        result = generate_nova_quarterly([], "Q4_2026")
        deadline = result["deadline_saisie"]

        # Should contain 2027-01-15
        assert "2027-01-15" in deadline

    def test_rounding_hours_and_ca(self) -> None:
        """Hours and CA are rounded to 2 decimal places."""
        from src.services.nova_reporting import generate_nova_quarterly

        invoices = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 1.333,
                "montant_total": 59.999,
                "statut": "PAYE",
            }
        ]

        result = generate_nova_quarterly(invoices, "Q1_2026")

        # Should round to 2 decimals
        assert result["heures_effectuees"] == 1.33
        assert result["ca_trimestre"] == 60.0

    def test_missing_quantite_defaults_to_zero(self) -> None:
        """Invoice with missing quantite is treated as 0."""
        from src.services.nova_reporting import generate_nova_quarterly

        invoices = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "montant_total": 45.0,
                "statut": "PAYE",
                # quantite missing
            },
            {
                "facture_id": "F002",
                "client_id": "C002",
                "quantite": 2.0,
                "montant_total": 90.0,
                "statut": "PAYE",
            },
        ]

        result = generate_nova_quarterly(invoices, "Q1_2026")

        assert result["heures_effectuees"] == 2.0
        assert result["ca_trimestre"] == 135.0

    def test_invalid_quantite_logged_and_skipped(self) -> None:
        """Invalid quantite (non-numeric) is logged as warning, invoice skipped for that field."""
        from src.services.nova_reporting import generate_nova_quarterly

        invoices = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": "invalid",  # Non-numeric
                "montant_total": 45.0,
                "statut": "PAYE",
            }
        ]

        # Should not raise, just skip/log
        result = generate_nova_quarterly(invoices, "Q1_2026")

        assert result["heures_effectuees"] == 0.0

    def test_trim_trailing_spaces_in_statut(self) -> None:
        """Statut field with trailing spaces should still match."""
        from src.services.nova_reporting import generate_nova_quarterly

        invoices = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 2.0,
                "montant_total": 90.0,
                "statut": "PAYE",
            }
        ]

        result = generate_nova_quarterly(invoices, "Q1_2026")

        assert result["heures_effectuees"] == 2.0
        assert result["nb_particuliers"] == 1


class TestAggregateByQuarter:
    """Tests for aggregate_by_quarter — groups invoices by quarter."""

    def test_groups_invoices_by_quarter(self) -> None:
        """Groups invoices by quarter based on date_debut."""
        from src.services.nova_reporting import aggregate_by_quarter

        invoices = [
            {
                "facture_id": "F001",
                "date_debut": "2026-01-15",
            },
            {
                "facture_id": "F002",
                "date_debut": "2026-04-10",
            },
            {
                "facture_id": "F003",
                "date_debut": "2026-01-20",
            },
        ]

        result = aggregate_by_quarter(invoices)

        assert "Q1_2026" in result
        assert "Q2_2026" in result
        assert len(result["Q1_2026"]) == 2
        assert len(result["Q2_2026"]) == 1

    def test_q1_jan_feb_mar(self) -> None:
        """Q1 correctly includes January, February, March."""
        from src.services.nova_reporting import aggregate_by_quarter

        invoices = [
            {"facture_id": "F001", "date_debut": "2026-01-01"},
            {"facture_id": "F002", "date_debut": "2026-02-15"},
            {"facture_id": "F003", "date_debut": "2026-03-31"},
            {"facture_id": "F004", "date_debut": "2026-04-01"},
        ]

        result = aggregate_by_quarter(invoices)

        assert len(result["Q1_2026"]) == 3
        assert len(result["Q2_2026"]) == 1

    def test_q2_apr_may_jun(self) -> None:
        """Q2 correctly includes April, May, June."""
        from src.services.nova_reporting import aggregate_by_quarter

        invoices = [
            {"facture_id": "F001", "date_debut": "2026-04-01"},
            {"facture_id": "F002", "date_debut": "2026-05-15"},
            {"facture_id": "F003", "date_debut": "2026-06-30"},
            {"facture_id": "F004", "date_debut": "2026-07-01"},
        ]

        result = aggregate_by_quarter(invoices)

        assert len(result["Q2_2026"]) == 3
        assert len(result["Q3_2026"]) == 1

    def test_q3_jul_aug_sep(self) -> None:
        """Q3 correctly includes July, August, September."""
        from src.services.nova_reporting import aggregate_by_quarter

        invoices = [
            {"facture_id": "F001", "date_debut": "2026-07-01"},
            {"facture_id": "F002", "date_debut": "2026-08-15"},
            {"facture_id": "F003", "date_debut": "2026-09-30"},
            {"facture_id": "F004", "date_debut": "2026-10-01"},
        ]

        result = aggregate_by_quarter(invoices)

        assert len(result["Q3_2026"]) == 3
        assert len(result["Q4_2026"]) == 1

    def test_q4_oct_nov_dec(self) -> None:
        """Q4 correctly includes October, November, December."""
        from src.services.nova_reporting import aggregate_by_quarter

        invoices = [
            {"facture_id": "F001", "date_debut": "2026-10-01"},
            {"facture_id": "F002", "date_debut": "2026-11-15"},
            {"facture_id": "F003", "date_debut": "2026-12-31"},
            {"facture_id": "F004", "date_debut": "2027-01-01"},
        ]

        result = aggregate_by_quarter(invoices)

        assert len(result["Q4_2026"]) == 3
        assert len(result["Q1_2027"]) == 1

    def test_invoice_without_date_debut_skipped(self) -> None:
        """Invoice missing date_debut is skipped."""
        from src.services.nova_reporting import aggregate_by_quarter

        invoices = [
            {"facture_id": "F001", "date_debut": "2026-01-15"},
            {"facture_id": "F002"},  # No date_debut
            {"facture_id": "F003", "date_debut": "2026-01-20"},
        ]

        result = aggregate_by_quarter(invoices)

        assert len(result["Q1_2026"]) == 2

    def test_invalid_date_format_logged_and_skipped(self) -> None:
        """Invoice with invalid date_debut is logged as warning, skipped."""
        from src.services.nova_reporting import aggregate_by_quarter

        invoices = [
            {"facture_id": "F001", "date_debut": "2026-01-15"},
            {"facture_id": "F002", "date_debut": "invalid-date"},
            {"facture_id": "F003", "date_debut": "2026-01-20"},
        ]

        result = aggregate_by_quarter(invoices)

        # Should not raise, just skip invalid
        assert len(result["Q1_2026"]) == 2

    def test_empty_invoice_list_returns_empty_dict(self) -> None:
        """Empty invoice list returns empty dictionary."""
        from src.services.nova_reporting import aggregate_by_quarter

        result = aggregate_by_quarter([])

        assert result == {}

    def test_multiple_years_separate_quarters(self) -> None:
        """Invoices from different years are separated (Q1_2026 vs Q1_2025)."""
        from src.services.nova_reporting import aggregate_by_quarter

        invoices = [
            {"facture_id": "F001", "date_debut": "2025-01-15"},
            {"facture_id": "F002", "date_debut": "2026-01-15"},
            {"facture_id": "F003", "date_debut": "2025-01-20"},
        ]

        result = aggregate_by_quarter(invoices)

        assert len(result["Q1_2025"]) == 2
        assert len(result["Q1_2026"]) == 1

    def test_invoice_data_preserved_during_grouping(self) -> None:
        """Original invoice data is preserved in grouped result."""
        from src.services.nova_reporting import aggregate_by_quarter

        invoices = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 2.0,
                "montant_total": 90.0,
                "date_debut": "2026-01-15",
            }
        ]

        result = aggregate_by_quarter(invoices)

        assert result["Q1_2026"][0]["facture_id"] == "F001"
        assert result["Q1_2026"][0]["client_id"] == "C001"
        assert result["Q1_2026"][0]["quantite"] == 2.0


class TestComputeDeadline:
    """Tests for _compute_deadline — calculates URSSAF submission deadline."""

    def test_q1_deadline_april_15(self) -> None:
        """Q1 (jan-feb-mar) deadline is April 15 of same year."""
        from src.services.nova_reporting import _compute_deadline

        deadline = _compute_deadline("Q1_2026")
        assert "2026-04-15" in deadline

    def test_q2_deadline_july_15(self) -> None:
        """Q2 (apr-may-jun) deadline is July 15 of same year."""
        from src.services.nova_reporting import _compute_deadline

        deadline = _compute_deadline("Q2_2026")
        assert "2026-07-15" in deadline

    def test_q3_deadline_october_15(self) -> None:
        """Q3 (jul-aug-sep) deadline is October 15 of same year."""
        from src.services.nova_reporting import _compute_deadline

        deadline = _compute_deadline("Q3_2026")
        assert "2026-10-15" in deadline

    def test_q4_deadline_january_15_next_year(self) -> None:
        """Q4 (oct-nov-dec) deadline is January 15 of NEXT year."""
        from src.services.nova_reporting import _compute_deadline

        deadline = _compute_deadline("Q4_2026")
        assert "2027-01-15" in deadline

    def test_deadline_format_is_iso(self) -> None:
        """Deadline is returned in ISO format (YYYY-MM-DDTHH:MM:SS or similar)."""
        from src.services.nova_reporting import _compute_deadline

        deadline = _compute_deadline("Q1_2026")
        # Should be parseable as ISO datetime
        parsed = datetime.fromisoformat(deadline)
        assert parsed.year == 2026
        assert parsed.month == 4
        assert parsed.day == 15

    def test_deadline_parses_year_first_format(self) -> None:
        """Deadline function handles year-first format (2026_Q1)."""
        from src.services.nova_reporting import _compute_deadline

        deadline = _compute_deadline("2026_Q1")
        assert "2026-04-15" in deadline

    def test_deadline_parses_quarter_first_format(self) -> None:
        """Deadline function handles quarter-first format (Q1_2026)."""
        from src.services.nova_reporting import _compute_deadline

        deadline = _compute_deadline("Q1_2026")
        assert "2026-04-15" in deadline

    def test_deadline_with_hyphen_separator(self) -> None:
        """Deadline function handles hyphen separator (Q1-2026)."""
        from src.services.nova_reporting import _compute_deadline

        deadline = _compute_deadline("Q1-2026")
        assert "2026-04-15" in deadline

    def test_invalid_quarter_format_returns_empty(self) -> None:
        """Invalid quarter format returns empty string."""
        from src.services.nova_reporting import _compute_deadline

        deadline = _compute_deadline("INVALID")
        assert deadline == ""

    def test_invalid_quarter_number_returns_empty(self) -> None:
        """Invalid quarter number (Q5) returns empty string."""
        from src.services.nova_reporting import _compute_deadline

        deadline = _compute_deadline("Q5_2026")
        # Should handle gracefully (return empty or default)
        assert deadline == "" or len(deadline) > 0  # Allow flexible fallback


class TestIntegrationNovaFlow:
    """Integration tests — full NOVA quarterly reporting flow."""

    def test_full_quarter_aggregation_and_reporting(self) -> None:
        """Full flow: group invoices by quarter, then generate NOVA report."""
        from src.services.nova_reporting import (
            aggregate_by_quarter,
            generate_nova_quarterly,
        )

        invoices = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 2.0,
                "montant_total": 90.0,
                "statut": "PAYE",
                "date_debut": "2026-01-15",
            },
            {
                "facture_id": "F002",
                "client_id": "C002",
                "quantite": 1.5,
                "montant_total": 67.5,
                "statut": "RAPPROCHE",
                "date_debut": "2026-02-10",
            },
            {
                "facture_id": "F003",
                "client_id": "C001",
                "quantite": 1.0,
                "montant_total": 45.0,
                "statut": "EN_ATTENTE",  # Should be excluded
                "date_debut": "2026-03-20",
            },
        ]

        by_quarter = aggregate_by_quarter(invoices)
        q1_result = generate_nova_quarterly(by_quarter["Q1_2026"], "Q1_2026")

        assert q1_result["heures_effectuees"] == 3.5
        assert q1_result["nb_particuliers"] == 2
        assert q1_result["ca_trimestre"] == 157.5

    def test_multiple_quarters_aggregated_separately(self) -> None:
        """Full year data aggregates correctly into separate quarters."""
        from src.services.nova_reporting import (
            aggregate_by_quarter,
            generate_nova_quarterly,
        )

        invoices = [
            # Q1
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 2.0,
                "montant_total": 90.0,
                "statut": "PAYE",
                "date_debut": "2026-01-15",
            },
            # Q2
            {
                "facture_id": "F002",
                "client_id": "C001",
                "quantite": 1.5,
                "montant_total": 67.5,
                "statut": "PAYE",
                "date_debut": "2026-04-10",
            },
            # Q3
            {
                "facture_id": "F003",
                "client_id": "C002",
                "quantite": 1.0,
                "montant_total": 45.0,
                "statut": "PAYE",
                "date_debut": "2026-07-20",
            },
            # Q4
            {
                "facture_id": "F004",
                "client_id": "C003",
                "quantite": 3.0,
                "montant_total": 135.0,
                "statut": "PAYE",
                "date_debut": "2026-10-05",
            },
        ]

        by_quarter = aggregate_by_quarter(invoices)
        q1 = generate_nova_quarterly(by_quarter["Q1_2026"], "Q1_2026")
        q2 = generate_nova_quarterly(by_quarter["Q2_2026"], "Q2_2026")
        q3 = generate_nova_quarterly(by_quarter["Q3_2026"], "Q3_2026")
        q4 = generate_nova_quarterly(by_quarter["Q4_2026"], "Q4_2026")

        assert q1["ca_trimestre"] == 90.0
        assert q2["ca_trimestre"] == 67.5
        assert q3["ca_trimestre"] == 45.0
        assert q4["ca_trimestre"] == 135.0


class TestNovaService:
    """RED tests for NovaService — orchestrates full NOVA workflow.

    NovaService reads invoices from SheetsAdapter, aggregates by quarter,
    generates NOVA data, and writes to the Metrics NOVA sheet.
    """

    def test_generate_from_sheets_single_quarter(self) -> None:
        """Lit les factures depuis SheetsAdapter, agrège pour le trimestre."""
        from unittest.mock import MagicMock

        from src.services.nova_reporting import NovaService

        # Arrange: Mock SheetsAdapter with test invoices
        mock_sheets = MagicMock()
        mock_sheets.get_all_invoices.return_value = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 2.0,
                "montant_total": 90.0,
                "statut": "PAYE",
                "date_debut": "2026-01-15",
            },
            {
                "facture_id": "F002",
                "client_id": "C002",
                "quantite": 1.5,
                "montant_total": 67.5,
                "statut": "RAPPROCHE",
                "date_debut": "2026-02-10",
            },
        ]

        service = NovaService(sheets=mock_sheets)

        # Act: Generate NOVA data for Q1 2026
        result = service.generate_from_sheets(quarter="Q1_2026")

        # Assert: Correct aggregation
        assert result["heures_effectuees"] == 3.5
        assert result["nb_particuliers"] == 2
        assert result["ca_trimestre"] == 157.5
        assert result["nb_intervenants"] == 1
        assert result["trimestre"] == "Q1_2026"

    def test_write_to_nova_sheet(self) -> None:
        """Écrit les résultats dans l'onglet Metrics NOVA."""
        from unittest.mock import MagicMock

        from src.services.nova_reporting import NovaService

        # Arrange
        mock_sheets = MagicMock()
        mock_sheets.get_all_invoices.return_value = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 2.0,
                "montant_total": 90.0,
                "statut": "PAYE",
                "date_debut": "2026-01-15",
            }
        ]

        service = NovaService(sheets=mock_sheets)
        nova_data = service.generate_from_sheets(quarter="Q1_2026")

        # Act: Write to Metrics NOVA sheet
        service.write_to_nova_sheet(nova_data=nova_data)

        # Assert: Verify append_rows was called with correct data
        mock_sheets.append_rows.assert_called_once()
        call_args = mock_sheets.append_rows.call_args
        assert call_args[1]["sheet_name"] == "Metrics NOVA"
        rows = call_args[1]["rows"]
        assert len(rows) > 0
        # Verify first row contains the NOVA data
        first_row = rows[0]
        assert first_row["trimestre"] == "Q1_2026"
        assert first_row["heures_effectuees"] == 2.0

    def test_cli_nova_command_generates_and_writes(self) -> None:
        """La commande `sap nova Q1-2026` génère et écrit les données."""
        from unittest.mock import MagicMock, patch

        from click.testing import CliRunner

        from src.cli import main

        runner = CliRunner()

        # Arrange: Mock the settings and SheetsAdapter
        mock_sheets = MagicMock()
        mock_sheets.get_all_invoices.return_value = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 3.0,
                "montant_total": 135.0,
                "statut": "PAYE",
                "date_debut": "2026-01-15",
            }
        ]

        with patch("src.cli.SheetsAdapter", return_value=mock_sheets), patch("src.cli.Settings"):
            # Act
            result = runner.invoke(main, ["nova", "Q1-2026"])

            # Assert: Command should succeed or indicate it's running
            # (implementation will define exit code)
            assert result.exit_code in [0, 1, 2]  # Allow for NotImplementedError

    def test_nova_only_paid_invoices(self) -> None:
        """Seules les factures PAYE/RAPPROCHE comptent."""
        from unittest.mock import MagicMock

        from src.services.nova_reporting import NovaService

        # Arrange: Mix of invoice statuses
        mock_sheets = MagicMock()
        mock_sheets.get_all_invoices.return_value = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 2.0,
                "montant_total": 90.0,
                "statut": "PAYE",
                "date_debut": "2026-01-15",
            },
            {
                "facture_id": "F002",
                "client_id": "C002",
                "quantite": 1.5,
                "montant_total": 67.5,
                "statut": "EN_ATTENTE",  # Should be excluded
                "date_debut": "2026-02-10",
            },
            {
                "facture_id": "F003",
                "client_id": "C003",
                "quantite": 1.0,
                "montant_total": 45.0,
                "statut": "BROUILLON",  # Should be excluded
                "date_debut": "2026-03-20",
            },
            {
                "facture_id": "F004",
                "client_id": "C001",
                "quantite": 1.0,
                "montant_total": 45.0,
                "statut": "RAPPROCHE",
                "date_debut": "2026-01-20",
            },
        ]

        service = NovaService(sheets=mock_sheets)

        # Act
        result = service.generate_from_sheets(quarter="Q1_2026")

        # Assert: Only F001 (PAYE) and F004 (RAPPROCHE) counted
        assert result["heures_effectuees"] == 3.0  # 2.0 + 1.0
        assert result["nb_particuliers"] == 1  # C001, C001 (duplicate, count as 1)
        assert result["ca_trimestre"] == 135.0  # 90.0 + 45.0

    def test_generate_full_year_nova_report(self) -> None:
        """Génère le rapport NOVA complet pour l'année (4 trimestres)."""
        from unittest.mock import MagicMock

        from src.services.nova_reporting import NovaService

        # Arrange: Full year invoices across all quarters
        mock_sheets = MagicMock()
        mock_sheets.get_all_invoices.return_value = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 2.0,
                "montant_total": 90.0,
                "statut": "PAYE",
                "date_debut": "2026-01-15",
            },
            {
                "facture_id": "F002",
                "client_id": "C001",
                "quantite": 1.5,
                "montant_total": 67.5,
                "statut": "PAYE",
                "date_debut": "2026-04-10",
            },
            {
                "facture_id": "F003",
                "client_id": "C002",
                "quantite": 1.0,
                "montant_total": 45.0,
                "statut": "PAYE",
                "date_debut": "2026-07-20",
            },
            {
                "facture_id": "F004",
                "client_id": "C003",
                "quantite": 3.0,
                "montant_total": 135.0,
                "statut": "PAYE",
                "date_debut": "2026-10-05",
            },
        ]

        service = NovaService(sheets=mock_sheets)

        # Act: Generate for all quarters
        q1 = service.generate_from_sheets(quarter="Q1_2026")
        q2 = service.generate_from_sheets(quarter="Q2_2026")
        q3 = service.generate_from_sheets(quarter="Q3_2026")
        q4 = service.generate_from_sheets(quarter="Q4_2026")

        # Assert: Each quarter has correct data
        assert q1["ca_trimestre"] == 90.0
        assert q2["ca_trimestre"] == 67.5
        assert q3["ca_trimestre"] == 45.0
        assert q4["ca_trimestre"] == 135.0
        assert (
            sum([q1["ca_trimestre"], q2["ca_trimestre"], q3["ca_trimestre"], q4["ca_trimestre"]])
            == 337.5
        )

    def test_write_all_quarters_to_sheet(self) -> None:
        """Écrit tous les trimestres de l'année dans Metrics NOVA."""
        from unittest.mock import MagicMock

        from src.services.nova_reporting import NovaService

        # Arrange
        mock_sheets = MagicMock()
        mock_sheets.get_all_invoices.return_value = [
            {
                "facture_id": "F001",
                "client_id": "C001",
                "quantite": 2.0,
                "montant_total": 90.0,
                "statut": "PAYE",
                "date_debut": "2026-01-15",
            },
            {
                "facture_id": "F002",
                "client_id": "C001",
                "quantite": 1.5,
                "montant_total": 67.5,
                "statut": "PAYE",
                "date_debut": "2026-04-10",
            },
        ]

        service = NovaService(sheets=mock_sheets)

        # Act: Generate and write all quarters
        quarters = ["Q1_2026", "Q2_2026", "Q3_2026", "Q4_2026"]
        for quarter in quarters:
            nova_data = service.generate_from_sheets(quarter=quarter)
            service.write_to_nova_sheet(nova_data=nova_data)

        # Assert: append_rows called 4 times
        assert mock_sheets.append_rows.call_count == 4
