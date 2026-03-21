"""Notifications email — alertes T+36h.

Envoie des reminders quand des factures sont EN_ATTENTE trop longtemps.
Phase 4b du workflow : si une facture reste EN_ATTENTE plus de 36h,
SAP-Facture envoie un email à Jules pour qu'il relance le client.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc

# Import real datetime to avoid issues when tests patch the module
from datetime import datetime as real_datetime
from typing import Any

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Stub pour envoyer des emails de reminder."""

    @staticmethod
    def send_email(
        recipient: str,
        subject: str,
        body: str,
    ) -> None:
        """Envoie un email (à implémenter selon le provider)."""
        logger.info(
            "Email envoyé",
            extra={"recipient": recipient, "subject": subject},
        )


def _parse_date_statut(date_statut_raw: Any) -> datetime | None:
    """Parse date_statut from string or datetime object.

    Arguments:
        date_statut_raw: string ISO format or datetime object

    Retourne:
        datetime object or None if parsing fails
    """
    if date_statut_raw is None:
        return None

    # Try to parse as ISO string first (string type is reliable)
    if isinstance(date_statut_raw, str):
        try:
            # Use the real datetime class to avoid mock issues
            return real_datetime.fromisoformat(date_statut_raw)
        except (ValueError, TypeError, AttributeError):
            return None

    # Assume it's already a datetime-like object (duck typing)
    # Verify by checking for timestamp method
    try:
        if hasattr(date_statut_raw, "timestamp"):
            return date_statut_raw
    except (TypeError, AttributeError):
        pass

    return None


def check_and_notify_overdue(
    invoices: list[dict[str, str | int]],
    threshold_hours: int = 36,
) -> list[str]:
    """Détecte les factures EN_ATTENTE depuis plus de threshold_hours.

    Arguments:
        invoices: liste des factures {facture_id, statut, date_statut, ...}
        threshold_hours: seuil en heures (défaut 36)

    Retourne:
        Liste des facture_ids pour lesquels un reminder a été généré.
    """
    if not invoices:
        logger.debug("check_and_notify_overdue: pas de factures")
        return []

    reminders: list[str] = []
    now: datetime = datetime.now(UTC)

    for inv in invoices:
        statut = inv.get("statut", "")
        facture_id = inv.get("facture_id", "")

        if statut != "EN_ATTENTE" or not facture_id:
            continue

        # Parse date_statut (ISO format ou datetime)
        date_statut_raw = inv.get("date_statut")
        date_statut = _parse_date_statut(date_statut_raw)

        if not date_statut_raw:
            logger.warning(
                "Facture EN_ATTENTE sans date_statut",
                extra={"facture_id": facture_id},
            )
            continue

        if date_statut is None:
            logger.error(
                "date_statut invalide",
                extra={"facture_id": facture_id, "value": date_statut_raw},
            )
            continue

        # Calcul délai
        elapsed: timedelta = now - date_statut
        elapsed_hours: float = elapsed.total_seconds() / 3600

        if elapsed_hours >= threshold_hours:
            reminders.append(str(facture_id))
            logger.info(
                "Facture EN_ATTENTE dépassée — reminder nécessaire",
                extra={
                    "facture_id": facture_id,
                    "elapsed_hours": round(elapsed_hours, 1),
                    "threshold": threshold_hours,
                },
            )

    return reminders


def build_reminder_message(
    facture_id: str,
    client_name: str,
    elapsed_hours: int,
) -> str:
    """Construit le corps d'un email de reminder.

    Arguments:
        facture_id: identifiant de la facture
        client_name: nom du client
        elapsed_hours: heures écoulées depuis EN_ATTENTE

    Retourne:
        Texte du message d'email
    """
    return (
        f"Facture {facture_id} pour {client_name} en attente depuis {elapsed_hours}h.\n"
        f"Veuillez relancer le client pour qu'il valide dans le portail URSSAF.\n"
        f"Délai avant expiration : 48h total."
    )
