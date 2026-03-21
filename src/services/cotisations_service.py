"""CotisationsService — calcul charges sociales micro 25.8% + simulation IR.

Gère le calcul des cotisations micro-entrepreneur (25.8% du CA encaissé)
et la simulation de l'impôt sur le revenu avec abattement BNC 34%.

Spec: CDC §8.2 (Cotisations Micro), §8.3 (Fiscal IR)
Plan: Sprint 9-10
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

# IR 2026 progressive brackets (revenu imposable, taux)
IR_BRACKETS_2026 = [
    (11294, 11),
    (28797, 30),
    (82341, 41),
    (float("inf"), 45),
]


class CotisationsService:
    """Service pour les calculs de cotisations et simulation IR."""

    TAUX_CHARGES = 25.8
    ABATTEMENT_BNC = 34.0
    TAUX_VL = 2.2

    def __init__(self, sheets: Any) -> None:
        """Initialize CotisationsService with SheetsAdapter.

        Arguments:
            sheets: SheetsAdapter instance for reading/writing invoices and cotisations.
        """
        self._sheets = sheets

    def calculate_monthly_charges(self, mois: int, annee: int) -> dict:
        """Calcule les charges sociales pour un mois.

        Arguments:
            mois: Mois (1-12)
            annee: Année (ex: 2026)

        Returns:
            {
                mois: int,
                annee: int,
                ca_encaisse: float (sum montant PAYE),
                taux_charges: 25.8,
                montant_charges: float (CA * 25.8%),
                net: float (CA - charges),
                date_limite: date (15 du mois suivant)
            }
        """
        invoices = self._sheets.get_paye_invoices_for_month(mois=mois, annee=annee)
        ca_encaisse = sum(inv["montant_total"] for inv in invoices)
        montant_charges = round(ca_encaisse * (self.TAUX_CHARGES / 100), 2)
        net = ca_encaisse - montant_charges
        date_limite = self._compute_date_limite(mois, annee)

        return {
            "mois": mois,
            "annee": annee,
            "ca_encaisse": ca_encaisse,
            "taux_charges": self.TAUX_CHARGES,
            "montant_charges": montant_charges,
            "net": net,
            "date_limite": date_limite,
        }

    def get_annual_summary(self, annee: int) -> dict:
        """Agrégation annuelle CA + charges + net.

        Arguments:
            annee: Année (ex: 2026)

        Returns:
            {
                annee: int,
                ca_cumul: float,
                charges_cumul: float,
                net_cumul: float
            }
        """
        invoices = self._sheets.get_paye_invoices_for_year(annee=annee)
        ca_cumul = sum(inv["montant_total"] for inv in invoices)
        charges_cumul = round(ca_cumul * (self.TAUX_CHARGES / 100), 2)
        net_cumul = ca_cumul - charges_cumul

        return {
            "annee": annee,
            "ca_cumul": ca_cumul,
            "charges_cumul": charges_cumul,
            "net_cumul": net_cumul,
        }

    def calculate_ir_simulation(self, annee: int) -> dict:
        """Simule l'impôt sur le revenu avec abattement BNC 34%.

        Arguments:
            annee: Année (ex: 2026)

        Returns:
            {
                annee: int,
                ca_micro: float (sum CA PAYE),
                abattement: float (CA * 34%),
                revenu_imposable: float (CA - abattement),
                taux_marginal: int (% tranche IR),
                impot_total: float,
                simulation_vl: float (CA * 2.2%, optionnel)
            }
        """
        invoices = self._sheets.get_paye_invoices_for_year(annee=annee)
        ca_micro = sum(inv["montant_total"] for inv in invoices)
        abattement = round(ca_micro * (self.ABATTEMENT_BNC / 100), 2)
        revenu_imposable = ca_micro - abattement
        simulation_vl = round(ca_micro * (self.TAUX_VL / 100), 2)

        taux_marginal, impot_total = self._calculate_ir(revenu_imposable)

        return {
            "annee": annee,
            "ca_micro": ca_micro,
            "abattement": abattement,
            "revenu_imposable": revenu_imposable,
            "taux_marginal": taux_marginal,
            "impot_total": impot_total,
            "simulation_vl": simulation_vl,
        }

    def write_to_cotisations_sheet(self, charges_data: dict) -> None:
        """Écrit les charges mensuelles dans l'onglet Cotisations.

        Arguments:
            charges_data: Dict retourné par calculate_monthly_charges()
        """
        rows = [charges_data]
        self._sheets.append_rows(sheet_name="Cotisations", rows=rows)

    def write_to_fiscal_sheet(self, ir_data: dict) -> None:
        """Écrit les données IR dans l'onglet Fiscal IR.

        Arguments:
            ir_data: Dict retourné par calculate_ir_simulation()
        """
        rows = [ir_data]
        self._sheets.append_rows(sheet_name="Fiscal IR", rows=rows)

    def _compute_date_limite(self, mois: int, annee: int) -> date:
        """Compute payment deadline: 15th of next month."""
        if mois == 12:
            return date(annee + 1, 1, 15)
        else:
            return date(annee, mois + 1, 15)

    def _calculate_ir(self, revenu_imposable: float) -> tuple[int, float]:
        """Calculate marginal tax rate and total IR.

        Returns:
            (taux_marginal, impot_total)
        """
        if revenu_imposable <= 0:
            return 0, 0.0

        taux_marginal = 0
        for limite, taux in IR_BRACKETS_2026:
            if revenu_imposable <= limite:
                taux_marginal = taux
                break

        # Simple calculation: total IR = revenu * marginal rate / 100
        impot_total = round(revenu_imposable * (taux_marginal / 100), 2)

        return taux_marginal, impot_total
