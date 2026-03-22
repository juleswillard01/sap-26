"""Service de synchronisation clients — CDC §2.

SAP-Facture ne CREE PAS les clients (Jules le fait dans AIS).
SAP-Facture SYNCHRONISE les données clients depuis AIS vers Google Sheets.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def sync_clients_from_ais(
    ais_clients: list[dict[str, str]],
    sheets_clients: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Compare les clients AIS avec ceux de Google Sheets.

    Retourne la liste des clients nouveaux ou modifiés à mettre à jour.
    """
    raise NotImplementedError("À implémenter — sync clients AIS → Sheets")
