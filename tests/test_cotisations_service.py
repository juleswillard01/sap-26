"""Tests RED — CotisationsService charges sociales micro 25.8% + simulation IR.

Cotisations Service calculates:
1. Monthly social charges (cotisations micro-entrepreneur) at 25.8% of CA encaissé (PAYE)
2. Annual cumulative totals (CA, charges, net)
3. Income tax (IR) simulation with:
   - BNC abattement: 34% of CA
   - Progressive tax brackets (2026)
   - Optional versement libératoire: 2.2% of CA

Spec: CDC §8.2 (Cotisations Micro), CDC §8.3 (Fiscal IR), Plan Sprint 9-10
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock


class TestCalculateMonthlyCotisations:
    """Tests for calculate_monthly_charges — charges sociales micro-entrepreneur."""

    def test_charges_25_8_pct_basic(self) -> None:
        """CA 1000€ → charges 258€ (25.8%)."""
        from src.services.cotisations_service import CotisationsService

        # Arrange
        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)

        # Act
        result = service.calculate_monthly_charges(mois=3, annee=2026)

        # Assert
        assert result["ca_encaisse"] == 1000.0
        assert result["montant_charges"] == 258.0
        assert result["net"] == 742.0  # 1000 - 258

    def test_charges_zero_ca_zero_charges(self) -> None:
        """CA 0€ → charges 0€, net 0€."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = []

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_monthly_charges(mois=3, annee=2026)

        assert result["ca_encaisse"] == 0.0
        assert result["montant_charges"] == 0.0
        assert result["net"] == 0.0

    def test_charges_multiple_invoices_sum(self) -> None:
        """Multiple PAYE invoices in month sum correctly."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 500.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-10",
            },
            {
                "facture_id": "F002",
                "montant_total": 300.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-25",
            },
            {
                "facture_id": "F003",
                "montant_total": 200.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-30",
            },
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_monthly_charges(mois=3, annee=2026)

        assert result["ca_encaisse"] == 1000.0
        assert result["montant_charges"] == 258.0

    def test_charges_decimal_precision(self) -> None:
        """CA 123.45€ → charges 31.83€ (rounded to 2 decimals)."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 123.45,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_monthly_charges(mois=3, annee=2026)

        assert result["ca_encaisse"] == 123.45
        # 123.45 * 0.258 = 31.8501 → rounded to 31.85
        assert abs(result["montant_charges"] - 31.85) < 0.01

    def test_date_limite_15_next_month(self) -> None:
        """date_limite is 15th of next month (payment deadline for charges)."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)

        # March charges must be paid by April 15
        result = service.calculate_monthly_charges(mois=3, annee=2026)

        assert result["date_limite"] == date(2026, 4, 15)

    def test_date_limite_december_to_january(self) -> None:
        """December charges due January 15 of next year."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": "2026-12-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_monthly_charges(mois=12, annee=2026)

        assert result["date_limite"] == date(2027, 1, 15)

    def test_returns_dict_with_required_fields(self) -> None:
        """Returns dict with all required fields."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_monthly_charges(mois=3, annee=2026)

        assert "ca_encaisse" in result
        assert "taux_charges" in result
        assert "montant_charges" in result
        assert "net" in result
        assert "date_limite" in result
        assert "mois" in result
        assert "annee" in result

    def test_taux_charges_always_25_8_pct(self) -> None:
        """taux_charges field is always 25.8% for micro-entrepreneur."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 500.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_monthly_charges(mois=3, annee=2026)

        assert result["taux_charges"] == 25.8


class TestGetAnnualSummary:
    """Tests for get_annual_summary — cumulative CA + charges + net."""

    def test_cumul_annuel_single_month(self) -> None:
        """One month: CA 1000€ → cumul 1000€, charges 258€."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_year.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.get_annual_summary(annee=2026)

        assert result["ca_cumul"] == 1000.0
        assert result["charges_cumul"] == 258.0
        assert result["net_cumul"] == 742.0

    def test_cumul_annuel_full_year_12_months(self) -> None:
        """Full year aggregation across all 12 months."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        # 12 months x 1000€ = 12000€ CA
        invoices = [
            {
                "facture_id": f"F{mois:02d}01",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": f"2026-{mois:02d}-15",
            }
            for mois in range(1, 13)
        ]
        mock_sheets.get_paye_invoices_for_year.return_value = invoices

        service = CotisationsService(sheets=mock_sheets)
        result = service.get_annual_summary(annee=2026)

        assert result["ca_cumul"] == 12000.0
        assert result["charges_cumul"] == 3096.0  # 12000 * 0.258
        assert result["net_cumul"] == 8904.0  # 12000 - 3096

    def test_cumul_zero_year_with_no_invoices(self) -> None:
        """Year with no invoices returns zeros."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_year.return_value = []

        service = CotisationsService(sheets=mock_sheets)
        result = service.get_annual_summary(annee=2026)

        assert result["ca_cumul"] == 0.0
        assert result["charges_cumul"] == 0.0
        assert result["net_cumul"] == 0.0

    def test_cumul_mixed_months(self) -> None:
        """Different CA amounts per month aggregate correctly."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_year.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 500.0,
                "statut": "PAYE",
                "date_paiement": "2026-01-15",
            },
            {
                "facture_id": "F002",
                "montant_total": 750.0,
                "statut": "PAYE",
                "date_paiement": "2026-02-15",
            },
            {
                "facture_id": "F003",
                "montant_total": 1200.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            },
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.get_annual_summary(annee=2026)

        ca_total = 500.0 + 750.0 + 1200.0  # 2450
        charges_total = ca_total * 0.258
        assert result["ca_cumul"] == ca_total
        assert abs(result["charges_cumul"] - charges_total) < 0.01


class TestCalculateIRSimulation:
    """Tests for calculate_ir_simulation — impôt sur le revenu micro-entrepreneur."""

    def test_abattement_bnc_34_pct(self) -> None:
        """CA 10000€ → abattement 3400€ (34% BNC) → imposable 6600€."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_year.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 10000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_ir_simulation(annee=2026)

        assert result["ca_micro"] == 10000.0
        assert result["abattement"] == 3400.0
        assert result["revenu_imposable"] == 6600.0

    def test_abattement_zero_ca_zero_imposable(self) -> None:
        """CA 0€ → abattement 0€ → imposable 0€."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_year.return_value = []

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_ir_simulation(annee=2026)

        assert result["ca_micro"] == 0.0
        assert result["abattement"] == 0.0
        assert result["revenu_imposable"] == 0.0

    def test_versement_liberatoire_2_2_pct(self) -> None:
        """CA 10000€ → VL 220€ (2.2% optional flat tax)."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_year.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 10000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_ir_simulation(annee=2026)

        assert result["simulation_vl"] == 220.0  # 10000 * 0.022

    def test_tranches_ir_2026_basic(self) -> None:
        """Barème IR 2026 applied correctly (progressive brackets)."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        # CA 30000€ → abattement 10200€ → imposable 19800€
        mock_sheets.get_paye_invoices_for_year.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 30000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_ir_simulation(annee=2026)

        # Verify revenu_imposable is correct
        assert result["revenu_imposable"] == 19800.0
        # Should have taux_marginal and impot_total fields
        assert "taux_marginal" in result
        assert "impot_total" in result

    def test_taux_marginal_tranche1_11(self) -> None:
        """Revenu 5000€ (imposable after abattement) is in 11% bracket."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        # CA 7463€ → abattement 2537€ → imposable 4926€ (in 11% bracket)
        mock_sheets.get_paye_invoices_for_year.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 7463.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_ir_simulation(annee=2026)

        # 4926€ is in 11% bracket (0-11,294€)
        assert result["taux_marginal"] == 11

    def test_returns_dict_with_all_fields(self) -> None:
        """Returns dict with all required IR simulation fields."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_year.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 10000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_ir_simulation(annee=2026)

        required_fields = [
            "ca_micro",
            "abattement",
            "revenu_imposable",
            "taux_marginal",
            "impot_total",
            "simulation_vl",
            "annee",
        ]
        for field in required_fields:
            assert field in result

    def test_ir_simulation_ca_12000_full_year(self) -> None:
        """Full year example: CA 12000€ across 12 months."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        # 12 x 1000€ invoices
        invoices = [
            {
                "facture_id": f"F{mois:02d}01",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": f"2026-{mois:02d}-15",
            }
            for mois in range(1, 13)
        ]
        mock_sheets.get_paye_invoices_for_year.return_value = invoices

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_ir_simulation(annee=2026)

        assert result["ca_micro"] == 12000.0
        assert result["abattement"] == 4080.0  # 12000 * 0.34
        assert result["revenu_imposable"] == 7920.0  # 12000 - 4080
        assert result["simulation_vl"] == 264.0  # 12000 * 0.022


class TestCotisationsServiceSheetInteraction:
    """Tests for CotisationsService sheet read/write interactions."""

    def test_compute_from_sheets_monthly(self) -> None:
        """Lit les factures PAYE depuis Sheets, calcule les charges mensuelles."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            },
            {
                "facture_id": "F002",
                "montant_total": 500.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-20",
            },
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.calculate_monthly_charges(mois=3, annee=2026)

        # Verify sheets.get_paye_invoices_for_month was called
        mock_sheets.get_paye_invoices_for_month.assert_called_once_with(mois=3, annee=2026)

        assert result["ca_encaisse"] == 1500.0

    def test_compute_from_sheets_annual(self) -> None:
        """Lit les factures PAYE annuelles depuis Sheets."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_year.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": "2026-01-15",
            },
            {
                "facture_id": "F002",
                "montant_total": 2000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            },
        ]

        service = CotisationsService(sheets=mock_sheets)
        result = service.get_annual_summary(annee=2026)

        mock_sheets.get_paye_invoices_for_year.assert_called_once_with(annee=2026)
        assert result["ca_cumul"] == 3000.0

    def test_write_to_cotisations_sheet(self) -> None:
        """Écrit les résultats mensuels dans l'onglet Cotisations."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        charges_data = service.calculate_monthly_charges(mois=3, annee=2026)

        # Act: Write to Cotisations sheet
        service.write_to_cotisations_sheet(charges_data=charges_data)

        # Assert: Verify append_rows was called with correct sheet name
        mock_sheets.append_rows.assert_called_once()
        call_args = mock_sheets.append_rows.call_args
        assert call_args[1]["sheet_name"] == "Cotisations"

    def test_write_to_fiscal_sheet(self) -> None:
        """Écrit les résultats IR dans l'onglet Fiscal IR."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_year.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 10000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        ir_data = service.calculate_ir_simulation(annee=2026)

        # Act: Write to Fiscal IR sheet
        service.write_to_fiscal_sheet(ir_data=ir_data)

        # Assert: Verify append_rows was called with correct sheet name
        mock_sheets.append_rows.assert_called_once()
        call_args = mock_sheets.append_rows.call_args
        assert call_args[1]["sheet_name"] == "Fiscal IR"

    def test_write_cotisations_row_format(self) -> None:
        """Row format for Cotisations sheet matches expected structure."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        charges_data = service.calculate_monthly_charges(mois=3, annee=2026)
        service.write_to_cotisations_sheet(charges_data=charges_data)

        call_args = mock_sheets.append_rows.call_args
        rows = call_args[1]["rows"]
        first_row = rows[0]

        # Verify expected fields are in the row
        assert "mois" in first_row
        assert "ca_encaisse" in first_row
        assert "montant_charges" in first_row
        assert "net" in first_row

    def test_write_fiscal_row_format(self) -> None:
        """Row format for Fiscal IR sheet matches expected structure."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_year.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 10000.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)
        ir_data = service.calculate_ir_simulation(annee=2026)
        service.write_to_fiscal_sheet(ir_data=ir_data)

        call_args = mock_sheets.append_rows.call_args
        rows = call_args[1]["rows"]
        first_row = rows[0]

        # Verify expected fields
        assert "ca_micro" in first_row
        assert "abattement" in first_row
        assert "revenu_imposable" in first_row
        assert "taux_marginal" in first_row
        assert "simulation_vl" in first_row


class TestCotisationsServiceIntegration:
    """Integration tests — full cotisations and IR workflow."""

    def test_full_monthly_workflow(self) -> None:
        """Full workflow: read invoices, calculate charges, write to sheet."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        mock_sheets.get_paye_invoices_for_month.return_value = [
            {
                "facture_id": "F001",
                "montant_total": 1500.0,
                "statut": "PAYE",
                "date_paiement": "2026-03-15",
            }
        ]

        service = CotisationsService(sheets=mock_sheets)

        # Act: Calculate and write
        charges = service.calculate_monthly_charges(mois=3, annee=2026)
        service.write_to_cotisations_sheet(charges_data=charges)

        # Assert: Both operations completed
        assert charges["ca_encaisse"] == 1500.0
        mock_sheets.append_rows.assert_called_once()

    def test_full_annual_ir_workflow(self) -> None:
        """Full workflow: read year invoices, calculate IR, write to sheet."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()
        invoices = [
            {
                "facture_id": f"F{i:03d}",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": f"2026-{(i % 12) + 1:02d}-15",
            }
            for i in range(12)
        ]
        mock_sheets.get_paye_invoices_for_year.return_value = invoices

        service = CotisationsService(sheets=mock_sheets)

        # Act: Calculate and write
        ir_sim = service.calculate_ir_simulation(annee=2026)
        service.write_to_fiscal_sheet(ir_data=ir_sim)

        # Assert
        assert ir_sim["ca_micro"] == 12000.0
        assert ir_sim["abattement"] == 4080.0
        mock_sheets.append_rows.assert_called_once()

    def test_monthly_and_annual_consistency(self) -> None:
        """Monthly charges sum should equal annual calculation."""
        from src.services.cotisations_service import CotisationsService

        mock_sheets = MagicMock()

        # Setup: 12 months with 1000€ each
        service = CotisationsService(sheets=mock_sheets)

        # Mock monthly calls
        monthly_totals = []
        for mois in range(1, 13):
            mock_sheets.get_paye_invoices_for_month.return_value = [
                {
                    "facture_id": f"F{mois:02d}01",
                    "montant_total": 1000.0,
                    "statut": "PAYE",
                    "date_paiement": f"2026-{mois:02d}-15",
                }
            ]
            charges = service.calculate_monthly_charges(mois=mois, annee=2026)
            monthly_totals.append(charges["montant_charges"])

        # Mock annual call
        invoices = [
            {
                "facture_id": f"F{mois:02d}01",
                "montant_total": 1000.0,
                "statut": "PAYE",
                "date_paiement": f"2026-{mois:02d}-15",
            }
            for mois in range(1, 13)
        ]
        mock_sheets.get_paye_invoices_for_year.return_value = invoices
        annual = service.get_annual_summary(annee=2026)

        # Assert: Sum of monthly == annual
        assert abs(sum(monthly_totals) - annual["charges_cumul"]) < 0.01
