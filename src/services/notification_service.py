"""Notifications email — alertes T+36h.

Envoie des reminders quand des factures sont EN_ATTENTE trop longtemps.
Phase 4b du workflow : si une facture reste EN_ATTENTE plus de 36h,
SAP-Facture envoie un email à Jules pour qu'il relance le client.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta

# Import real datetime to avoid issues when tests patch the module
from datetime import datetime as real_datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.adapters.email_notifier import EmailNotifier
    from src.config import Settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service de notifications pour le cycle de vie des factures.

    Gère l'envoi d'emails pour :
    - Reminders T+36h (EN_ATTENTE)
    - Alertes expiration T+48h (EN_ATTENTE)
    - Confirmations de paiement (PAYE)
    - Confirmations de lettrage (RAPPROCHE)
    - Alertes erreur de synchronisation
    """

    def __init__(self, email_notifier: EmailNotifier, settings: Settings | None = None) -> None:
        """Initialize NotificationService.

        Args:
            email_notifier: EmailNotifier instance for sending emails.
            settings: Optional Settings instance (for defaults).
        """
        self._email_notifier = email_notifier
        self._settings = settings

    def send_reminder_t36h(self, invoice: dict[str, Any]) -> bool:
        """Send reminder if invoice is EN_ATTENTE for >= 36 hours.

        Args:
            invoice: Invoice dict with status, date_statut, etc.

        Returns:
            True if email was sent, False otherwise.
        """
        # Check status
        if invoice.get("statut") != "EN_ATTENTE":
            return False

        # Parse date_statut
        date_statut = self._parse_date_statut(invoice.get("date_statut"))
        if date_statut is None:
            return False

        # Check if >= 36 hours
        # If date_statut is naive, assume UTC
        if date_statut.tzinfo is None:
            date_statut = date_statut.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        elapsed = now - date_statut
        elapsed_hours = elapsed.total_seconds() / 3600

        if elapsed_hours < 36:
            return False

        # Send reminder
        try:
            self._email_notifier.send_reminder_email(
                invoice_id=invoice.get("facture_id", ""),
                client_name=invoice.get("client_id", ""),
                amount_due=invoice.get("montant_total", 0.0),
                due_date=invoice.get("date_paiement", ""),
                days_pending=int(elapsed_hours / 24),
            )
            logger.info(
                "Reminder sent for invoice",
                extra={"facture_id": invoice.get("facture_id")},
            )
            return True
        except Exception:
            logger.error("Failed to send reminder", exc_info=True)
            return False

    def send_expired_alert(self, invoice: dict[str, Any]) -> bool:
        """Send alert if invoice is EN_ATTENTE for >= 48 hours.

        Args:
            invoice: Invoice dict with status, date_statut, etc.

        Returns:
            True if email was sent, False otherwise.
        """
        # Check status
        if invoice.get("statut") != "EN_ATTENTE":
            return False

        # Parse date_statut
        date_statut = self._parse_date_statut(invoice.get("date_statut"))
        if date_statut is None:
            return False

        # Check if >= 48 hours
        # If date_statut is naive, assume UTC
        if date_statut.tzinfo is None:
            date_statut = date_statut.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        elapsed = now - date_statut
        elapsed_hours = elapsed.total_seconds() / 3600

        if elapsed_hours < 48:
            return False

        # Send expiration alert
        try:
            facture_id = invoice.get("facture_id", "")
            client_id = invoice.get("client_id", "")
            body = f"Invoice {facture_id} for client {client_id} has expired (48h+ EN_ATTENTE)"

            self._email_notifier.send_email(
                to=self._email_notifier.notification_email,
                subject=f"Invoice Expired — {facture_id}",
                body_text=body,
            )
            logger.info(
                "Expiration alert sent for invoice",
                extra={"facture_id": facture_id},
            )
            return True
        except Exception:
            logger.error("Failed to send expiration alert", exc_info=True)
            return False

    def send_payment_received(self, invoice: dict[str, Any]) -> bool:
        """Send notification when payment is received (PAYE status).

        Args:
            invoice: Invoice dict with status, montant_total, date_paiement, etc.

        Returns:
            True if email was sent, False otherwise.
        """
        # Check status
        if invoice.get("statut") != "PAYE":
            return False

        # Send payment confirmation
        try:
            facture_id = invoice.get("facture_id", "")
            montant = invoice.get("montant_total", 0.0)
            date_paiement = invoice.get("date_paiement", "")

            body = (
                f"Payment received\n"
                f"Invoice: {facture_id}\n"
                f"Amount: {montant}€\n"
                f"Payment date: {date_paiement}"
            )

            self._email_notifier.send_email(
                to=self._email_notifier.notification_email,
                subject=f"Payment Received — {facture_id}",
                body_text=body,
            )
            logger.info(
                "Payment notification sent",
                extra={"facture_id": facture_id},
            )
            return True
        except Exception:
            logger.error("Failed to send payment notification", exc_info=True)
            return False

    def send_reconciled(self, invoice: dict[str, Any]) -> bool:
        """Send notification when invoice is reconciled (RAPPROCHE status).

        Args:
            invoice: Invoice dict with status, facture_id, score_confiance, etc.

        Returns:
            True if email was sent, False otherwise.
        """
        # Check status
        if invoice.get("statut") != "RAPPROCHE":
            return False

        # Send reconciliation confirmation
        try:
            facture_id = invoice.get("facture_id", "")
            score = invoice.get("score_confiance", "")

            body = f"Invoice {facture_id} reconciled"
            if score:
                body += f" (confidence score: {score})"

            self._email_notifier.send_email(
                to=self._email_notifier.notification_email,
                subject=f"Reconciliation Complete — {facture_id}",
                body_text=body,
            )
            logger.info(
                "Reconciliation notification sent",
                extra={"facture_id": facture_id},
            )
            return True
        except Exception:
            logger.error("Failed to send reconciliation notification", exc_info=True)
            return False

    def send_sync_failed(self, error_message: str) -> bool:
        """Send alert when sync fails.

        Args:
            error_message: Error message describing the failure.

        Returns:
            True if email was sent, False otherwise.
        """
        # Strip passwords and sensitive data from error message
        sanitized = self._strip_sensitive_data(error_message)

        # Send sync failed alert
        try:
            self._email_notifier.send_sync_failed_email(
                sync_type="unknown",
                error_message=sanitized,
            )
            logger.info("Sync failed alert sent")
            return True
        except Exception:
            logger.error("Failed to send sync failed alert", exc_info=True)
            return False

    def check_and_send_overdue(
        self,
        invoices: list[dict[str, Any]],
        now: datetime | None = None,
    ) -> int:
        """Check invoices for overdue reminders and send them.

        Processes all invoices that are EN_ATTENTE for >= 36 hours
        and sends reminder emails.

        Args:
            invoices: List of invoice dicts.
            now: Optional current datetime (for testing). Defaults to datetime.now(UTC).

        Returns:
            Count of reminder emails sent.
        """
        if now is None:
            now = datetime.now(UTC)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        count = 0
        for invoice in invoices:
            # Only process EN_ATTENTE invoices
            if invoice.get("statut") != "EN_ATTENTE":
                continue

            # Parse date_statut
            date_statut = self._parse_date_statut(invoice.get("date_statut"))
            if date_statut is None:
                continue

            # Check if >= 36 hours
            # If date_statut is naive, assume UTC
            if date_statut.tzinfo is None:
                date_statut = date_statut.replace(tzinfo=UTC)

            elapsed = now - date_statut
            elapsed_hours = elapsed.total_seconds() / 3600

            if elapsed_hours >= 36 and self.send_reminder_t36h(invoice):
                # Send reminder
                count += 1

        return count

    @staticmethod
    def _parse_date_statut(date_statut_raw: Any) -> datetime | None:
        """Parse date_statut from string or datetime object.

        Args:
            date_statut_raw: String (ISO format) or datetime object.

        Returns:
            datetime object or None if parsing fails.
        """
        if date_statut_raw is None:
            return None

        # Try to parse as ISO string first
        if isinstance(date_statut_raw, str):
            try:
                return real_datetime.fromisoformat(date_statut_raw)
            except (ValueError, TypeError, AttributeError):
                return None

        # Assume it's already a datetime-like object
        try:
            if hasattr(date_statut_raw, "timestamp"):
                return date_statut_raw
        except (TypeError, AttributeError):
            pass

        return None

    @staticmethod
    def _strip_sensitive_data(error_message: str) -> str:
        """Remove passwords and tokens from error message.

        Args:
            error_message: Raw error message potentially containing secrets.

        Returns:
            Sanitized error message.
        """
        # Strip password= values
        sanitized = re.sub(
            r"password\s*=\s*[^\s,;]+([\s,;]|$)", r"\1", error_message, flags=re.IGNORECASE
        )
        # Strip token= values
        sanitized = re.sub(r"token\s*=\s*[^\s,;]+([\s,;]|$)", r"\1", sanitized, flags=re.IGNORECASE)
        # Strip api_key= values
        sanitized = re.sub(
            r"api_key\s*=\s*[^\s,;]+([\s,;]|$)", r"\1", sanitized, flags=re.IGNORECASE
        )
        return sanitized


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
