"""Suivi des paiements — sync AIS → Google Sheets.

SAP-Facture scrape les statuts depuis AIS et met à jour Sheets.
Phase 4 du workflow : toutes les 4 heures (cron), Playwright scrape
les statuts des demandes, compare avec Sheets, et enregistre les
changements (CREE → EN_ATTENTE → VALIDE → PAYE → RAPPROCHE).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

import polars as pl

from src.models.invoice import VALID_TRANSITIONS

if TYPE_CHECKING:
    from src.adapters.ais_adapter import AISAdapter
    from src.adapters.sheets_adapter import SheetsAdapter

logger = logging.getLogger(__name__)


class PaymentTracker:
    """Service tracking invoice payment status changes from AIS to Sheets."""

    def __init__(self, ais_adapter: AISAdapter, sheets_adapter: SheetsAdapter) -> None:
        """Initialize PaymentTracker with adapters.

        Args:
            ais_adapter: AIS adapter to fetch invoice statuses
            sheets_adapter: Sheets adapter to read/write invoice data
        """
        self._ais_adapter = ais_adapter
        self._sheets_adapter = sheets_adapter

    def sync_statuses_from_ais(self) -> list[dict[str, Any]]:
        """Synchronize invoice statuses from AIS to Sheets.

        Compare AIS statuses with current Sheets invoices and detect changes.

        Returns:
            List of changes: {facture_id, ancien_statut, nouveau_statut}
        """
        ais_statuses = self._ais_adapter.get_invoice_statuses()
        sheets_df = self._sheets_adapter.get_all_invoices()

        if not ais_statuses:
            logger.debug("No AIS statuses to sync")
            return []

        # Convert Sheets DataFrame to dict index by facture_id
        sheets_invoices = sheets_df.to_dicts() if isinstance(sheets_df, pl.DataFrame) else []
        sheets_index: dict[str, dict[str, Any]] = {
            inv["facture_id"]: inv for inv in sheets_invoices if "facture_id" in inv
        }

        changes: list[dict[str, Any]] = []

        for ais_inv in ais_statuses:
            facture_id = ais_inv.get("facture_id", "")
            if not facture_id:
                continue

            new_status = ais_inv.get("statut_ais", "")
            if not new_status:
                continue

            # Skip unknown facture IDs (not in Sheets)
            old_record = sheets_index.get(facture_id)
            if not old_record:
                logger.debug(f"Skipping unknown facture_id: {facture_id}")
                continue

            old_status = old_record.get("statut", "")

            # Detect change
            if old_status != new_status:
                change = {
                    "facture_id": facture_id,
                    "ancien_statut": old_status,
                    "nouveau_statut": new_status,
                }
                changes.append(change)
                logger.info(
                    "Status change detected",
                    extra={
                        "facture_id": facture_id,
                        "ancien": old_status,
                        "nouveau": new_status,
                    },
                )

        return changes

    def detect_overdue_invoices(self, threshold_hours: int = 36) -> list[dict[str, Any]]:
        """Detect invoices in EN_ATTENTE status older than threshold.

        Args:
            threshold_hours: Hours after which EN_ATTENTE invoices are overdue

        Returns:
            List of overdue invoices
        """
        sheets_df = self._sheets_adapter.get_all_invoices()
        if not isinstance(sheets_df, pl.DataFrame) or len(sheets_df) == 0:
            return []

        sheets_invoices = sheets_df.to_dicts()
        now = datetime.now(ZoneInfo("UTC"))
        overdue_list: list[dict[str, Any]] = []

        for invoice in sheets_invoices:
            statut = invoice.get("statut", "")
            if statut != "EN_ATTENTE":
                continue

            # Try to get submission date
            date_str = invoice.get("date_soumission", "")
            if not date_str:
                continue

            try:
                # Parse ISO format datetime
                if isinstance(date_str, str):
                    # Handle both ISO string and native datetime
                    if "T" in date_str:
                        submission_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        continue
                else:
                    submission_date = date_str

                # Ensure UTC timezone
                if submission_date.tzinfo is None:
                    submission_date = submission_date.replace(tzinfo=ZoneInfo("UTC"))

                # Calculate age
                age = now - submission_date
                if age.total_seconds() > threshold_hours * 3600:
                    overdue_list.append(invoice)
                    logger.info(
                        "Overdue invoice detected",
                        extra={
                            "facture_id": invoice.get("facture_id"),
                            "age_hours": age.total_seconds() / 3600,
                        },
                    )
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Failed to parse date",
                    extra={
                        "facture_id": invoice.get("facture_id"),
                        "error": str(e),
                    },
                )
                continue

        return overdue_list

    def is_valid_transition(self, old_status: str, new_status: str) -> bool:
        """Validate if a status transition is allowed.

        Args:
            old_status: Current status
            new_status: Target status

        Returns:
            True if transition is valid, False otherwise
        """
        # Use VALID_TRANSITIONS from models
        allowed = VALID_TRANSITIONS.get(old_status, [])
        return new_status in allowed

    def write_status_change_to_sheets(self, change: dict[str, Any]) -> None:
        """Write a single status change to Sheets.

        Args:
            change: Change dict with facture_id and nouveau_statut
        """
        facture_id = change.get("facture_id", "")
        new_status = change.get("nouveau_statut", "")

        if not facture_id or not new_status:
            logger.warning("Invalid change dict, skipping")
            return

        self._sheets_adapter.update_invoice(facture_id, {"statut": new_status})
        logger.info(
            "Invoice status updated in Sheets",
            extra={"facture_id": facture_id, "nouveau_statut": new_status},
        )

    def write_status_changes_batch(self, changes: list[dict[str, Any]]) -> None:
        """Write multiple status changes to Sheets using batch API.

        Args:
            changes: List of change dicts with facture_id and nouveau_statut
        """
        if not changes:
            return

        # Convert changes to format expected by update_invoices_batch
        updates = [
            {"facture_id": change["facture_id"], "statut": change["nouveau_statut"]}
            for change in changes
            if change.get("facture_id") and change.get("nouveau_statut")
        ]

        if updates:
            count = self._sheets_adapter.update_invoices_batch(updates)
            logger.info(
                "Status changes batch written to Sheets",
                extra={"count": count, "updates_count": len(updates)},
            )


def sync_statuses_from_ais(
    ais_statuses: list[dict[str, str]],
    sheets_invoices: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Synchronise les statuts depuis AIS vers Google Sheets.

    Argument:
        ais_statuses: liste des demandes depuis Playwright (scrape AIS)
                      {facture_id, urssaf_demande_id, statut_ais, date_maj}
        sheets_invoices: état actuel onglet Factures
                        {facture_id, statut, urssaf_demande_id}

    Retourne:
        Liste des changements: {facture_id, ancien_statut, nouveau_statut}
    """
    if not ais_statuses or not sheets_invoices:
        logger.debug("sync_statuses_from_ais: pas de données")
        return []

    # Construire index Sheets
    sheets_index: dict[str, dict[str, str]] = {
        inv["facture_id"]: inv for inv in sheets_invoices if "facture_id" in inv
    }

    changes: list[dict[str, str]] = []

    for ais_inv in ais_statuses:
        facture_id = ais_inv.get("facture_id", "")
        if not facture_id:
            continue

        new_status = ais_inv.get("statut_ais", "")
        if not new_status:
            continue

        old_record = sheets_index.get(facture_id)
        old_status = old_record.get("statut", "") if old_record else ""

        # Détect changement
        if old_status != new_status:
            change = {
                "facture_id": facture_id,
                "ancien_statut": old_status or "N/A",
                "nouveau_statut": new_status,
                "urssaf_demande_id": ais_inv.get("urssaf_demande_id", ""),
            }
            changes.append(change)
            logger.info(
                "Changement statut détecté",
                extra={
                    "facture_id": facture_id,
                    "ancien": old_status,
                    "nouveau": new_status,
                },
            )

    return changes


def check_status_transition(
    old_status: str,
    new_status: str,
) -> bool:
    """Vérifie si une transition de statut est valide.

    Statuts valides (SCHEMAS.html §7): BROUILLON → SOUMIS → CREE →
    EN_ATTENTE → VALIDE → PAYE → RAPPROCHE (ou ANNULE, ERREUR, EXPIRE,
    REJETE en chemin).
    """
    valid_transitions: dict[str, set[str]] = {
        "BROUILLON": {"SOUMIS", "ANNULE"},
        "SOUMIS": {"CREE", "ERREUR"},
        "ERREUR": {"BROUILLON"},
        "CREE": {"EN_ATTENTE"},
        "EN_ATTENTE": {"VALIDE", "EXPIRE", "REJETE"},
        "EXPIRE": {"BROUILLON"},
        "REJETE": {"BROUILLON"},
        "VALIDE": {"PAYE"},
        "PAYE": {"RAPPROCHE"},
        "RAPPROCHE": set(),  # état terminal
        "ANNULE": set(),  # état terminal
    }
    return new_status in valid_transitions.get(old_status, set())


def filter_critical_statuses(
    changes: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Extrait les statuts critiques (EN_ATTENTE, EXPIRE, REJETE).

    Utilisé pour déclencher des alertes.
    """
    critical = {"EN_ATTENTE", "EXPIRE", "REJETE", "ERREUR"}
    return [c for c in changes if c["nouveau_statut"] in critical]
