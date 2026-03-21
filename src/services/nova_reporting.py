"""Reporting NOVA trimestriel — agrégation données.

Génère les données pour la déclaration NOVA (heures, particuliers, CA).
Phase 2 du produit : onglet Metrics NOVA agrège les factures par
trimestre pour exporter vers la déclaration URSSAF-NOVA.

SCHEMAS.html §5: Metrics NOVA = {trimestre, nb_intervenants (1),
heures_effectuees, nb_particuliers, ca_trimestre, deadline_saisie}
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_nova_quarterly(
    invoices: list[dict[str, str | int | float]],
    quarter: str,
) -> dict[str, float | int | str]:
    """Agrège les données pour un trimestre NOVA.

    Arguments:
        invoices: factures filtrées pour le trimestre
                  {facture_id, client_id, quantite, montant_total, nature_code,
                   date_debut, date_fin, statut, ...}
        quarter: trimestre au format "Q1_2026" ou "2026_Q1"

    Retourne:
        {
            trimestre: str,
            nb_intervenants: int (toujours 1 = Jules),
            heures_effectuees: float,
            nb_particuliers: int,
            ca_trimestre: float,
            deadline_saisie: str (ISO date)
        }
    """
    if not invoices:
        logger.debug("generate_nova_quarterly: pas de factures pour %s", quarter)
        return {
            "trimestre": quarter,
            "nb_intervenants": 1,
            "heures_effectuees": 0.0,
            "nb_particuliers": 0,
            "ca_trimestre": 0.0,
            "deadline_saisie": _compute_deadline(quarter),
        }

    # Agrégation
    total_hours: float = 0.0
    total_ca: float = 0.0
    unique_clients: set[str] = set()
    paid_invoices: int = 0

    for inv in invoices:
        statut = inv.get("statut", "")

        # Compter uniquement les factures payées/rapprochées
        if statut not in {"PAYE", "RAPPROCHE"}:
            logger.debug(
                "Facture %s exclue (statut=%s)",
                inv.get("facture_id"),
                statut,
            )
            continue

        paid_invoices += 1

        # Heures (colonnes "quantite")
        try:
            qty = float(inv.get("quantite", 0))
            total_hours += qty
        except (ValueError, TypeError):
            logger.warning(
                "Quantité invalide pour %s",
                inv.get("facture_id"),
            )

        # CA (montant_total)
        try:
            montant = float(inv.get("montant_total", 0))
            total_ca += montant
        except (ValueError, TypeError):
            logger.warning(
                "Montant invalide pour %s",
                inv.get("facture_id"),
            )

        # Clients uniques
        client_id = inv.get("client_id")
        if client_id:
            unique_clients.add(str(client_id))

    logger.info(
        "NOVA report generated",
        extra={
            "quarter": quarter,
            "invoices_counted": paid_invoices,
            "hours": total_hours,
            "clients": len(unique_clients),
            "ca": total_ca,
        },
    )

    return {
        "trimestre": quarter,
        "nb_intervenants": 1,  # toujours Jules
        "heures_effectuees": round(total_hours, 2),
        "nb_particuliers": len(unique_clients),
        "ca_trimestre": round(total_ca, 2),
        "deadline_saisie": _compute_deadline(quarter),
    }


def _compute_deadline(quarter: str) -> str:
    """Calcule la deadline URSSAF pour saisir la déclaration NOVA.

    Règle : le 15 du mois suivant le trimestre.
    Q1 (jan-fev-mar) → deadline 15 avril
    Q2 (avr-mai-jun) → deadline 15 juillet
    Q3 (jul-aou-sep) → deadline 15 octobre
    Q4 (oct-nov-dec) → deadline 15 janvier année suivante
    """
    # Parser quarter (Q1_2026 ou 2026_Q1)
    parts = quarter.replace("_", "-").split("-")
    if len(parts) != 2:
        logger.warning("Quarter format invalide: %s", quarter)
        return ""

    # Normaliser (prendre année et numéro)
    if parts[0].startswith("Q"):
        q_num = int(parts[0][1])
        year = int(parts[1])
    else:
        year = int(parts[0])
        q_num = int(parts[1][1])

    # Calculer mois de deadline
    deadline_months = {1: (4, year), 2: (7, year), 3: (10, year), 4: (1, year + 1)}
    month, deadline_year = deadline_months.get(q_num, (1, year + 1))

    deadline_date = datetime(deadline_year, month, 15)
    return deadline_date.isoformat()


def aggregate_by_quarter(
    invoices: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    """Groupe les factures par trimestre d'après leur date_debut.

    Retourne: {quarter: [invoices]}
    """
    by_quarter: dict[str, list[dict[str, str]]] = defaultdict(list)

    for inv in invoices:
        date_str = inv.get("date_debut", "")
        if not date_str:
            continue

        try:
            date_obj = datetime.fromisoformat(date_str)
            month = date_obj.month
            year = date_obj.year

            # Déterminer le trimestre
            q = (month - 1) // 3 + 1
            quarter_key = f"Q{q}_{year}"
            by_quarter[quarter_key].append(inv)
        except (ValueError, AttributeError):
            logger.warning("date_debut invalide: %s", date_str)

    return dict(by_quarter)


class NovaService:
    """Orchestrates NOVA quarterly reporting workflow.

    - Reads invoices from SheetsAdapter
    - Aggregates by quarter
    - Generates NOVA metrics
    - Writes to Metrics NOVA sheet
    """

    def __init__(self, sheets: object) -> None:
        """Initialize with SheetsAdapter instance.

        Args:
            sheets: SheetsAdapter for reading/writing invoice data
        """
        self._sheets = sheets

    def generate_from_sheets(self, quarter: str) -> dict[str, float | int | str]:
        """Generate NOVA data for a quarter from sheets.

        Args:
            quarter: Quarter key (e.g., "Q1_2026")

        Returns:
            {trimestre, heures_effectuees, nb_particuliers, ca_trimestre, ...}
        """
        # Fetch all invoices from SheetsAdapter
        all_invoices = self._sheets.get_all_invoices()

        # Group by quarter
        by_quarter = aggregate_by_quarter(all_invoices)

        # Generate NOVA data for requested quarter
        quarter_invoices = by_quarter.get(quarter, [])
        nova_data = generate_nova_quarterly(quarter_invoices, quarter)

        return nova_data

    def write_to_nova_sheet(self, nova_data: dict[str, float | int | str]) -> None:
        """Write NOVA data to Metrics NOVA sheet.

        Args:
            nova_data: Generated NOVA metrics from generate_from_sheets()
        """
        rows = [nova_data]
        self._sheets.append_rows(sheet_name="Metrics NOVA", rows=rows)
