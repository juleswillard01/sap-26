"""Service de suivi des factures — CDC §2.

SAP-Facture ne CREE PAS les factures (AIS le fait).
SAP-Facture DETECTE les changements de statut via sync AIS.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def detect_status_changes(
    ais_statuses: list[dict[str, str]],
    sheets_statuses: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Compare les statuts AIS avec ceux de Google Sheets.

    Retourne la liste des factures dont le statut a changé.
    """
    raise NotImplementedError("À implémenter — CDC §2")


def detect_overdue_invoices(
    invoices: list[dict[str, str]],
    threshold_hours: int = 36,
) -> list[dict[str, str]]:
    """Identifie les factures EN_ATTENTE depuis plus de N heures.

    Retourne la liste des factures à relancer.
    """
    raise NotImplementedError("À implémenter — CDC §2.3")
