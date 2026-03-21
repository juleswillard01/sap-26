"""Notifications email SMTP — CDC §10."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)


class EmailNotifier:
    """SMTP email notifier for SAP-Facture — CDC §10."""

    def __init__(self, settings: Settings) -> None:
        """Initialize EmailNotifier with settings.

        Args:
            settings: Settings instance with SMTP configuration.
        """
        self.settings = settings
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.notification_email = settings.notification_email

    def send_email(
        self, to: str, subject: str, body_text: str, body_html: str | None = None
    ) -> None:
        """Send email via SMTP with retry logic.

        Args:
            to: Recipient email address.
            subject: Email subject.
            body_text: Plain text body.
            body_html: Optional HTML body.

        Raises:
            smtplib.SMTPException: If email fails after 3 retries.
        """
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                self._send_message_via_smtp(to, subject, body_text, body_html)
                return
            except smtplib.SMTPServerDisconnected as e:
                last_error = e
                logger.warning(f"Transient SMTP error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
            except smtplib.SMTPException:
                raise
            except Exception as e:
                logger.error(f"Unexpected error sending email: {e}")
                raise

        if last_error:
            raise last_error

    def send_reminder_email(
        self,
        invoice_id: str,
        client_name: str,
        amount_due: float,
        due_date: str,
        days_pending: int,
    ) -> None:
        """Send payment reminder email.

        Args:
            invoice_id: Invoice identifier.
            client_name: Client name.
            amount_due: Amount due in EUR.
            due_date: Due date string.
            days_pending: Number of days payment is pending.
        """
        subject = f"Relance de paiement — Facture {invoice_id}"

        body_text = (
            f"Rappel de paiement\n"
            f"\n"
            f"Client: {client_name}\n"
            f"Facture: {invoice_id}\n"
            f"Montant: {amount_due}€\n"
            f"Date d'échéance: {due_date}\n"
            f"Jours en attente: {days_pending}\n"
        )

        body_html = (
            f"<html><body>"
            f"<h2>Rappel de paiement</h2>"
            f"<p><strong>Client:</strong> {client_name}</p>"
            f"<p><strong>Facture:</strong> {invoice_id}</p>"
            f"<p><strong>Montant:</strong> {amount_due}€</p>"
            f"<p><strong>Date d'échéance:</strong> {due_date}</p>"
            f"<p><strong>Jours en attente:</strong> {days_pending}</p>"
            f"</body></html>"
        )

        self.send_email(
            to=self.notification_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

    def send_sync_failed_email(self, sync_type: str, error_message: str) -> None:
        """Send sync failure alert email.

        Args:
            sync_type: Type of sync (ais, indy, etc.).
            error_message: Error details.
        """
        subject = f"Error: Sync failed — {sync_type.upper()}"

        body_text = f"Synchronization error\n\nType: {sync_type}\nError: {error_message}\n"

        body_html = (
            f"<html><body>"
            f"<h2>Synchronization error</h2>"
            f"<p><strong>Type:</strong> {sync_type}</p>"
            f"<p><strong>Error:</strong> {error_message}</p>"
            f"</body></html>"
        )

        self.send_email(
            to=self.notification_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

    def _send_message_via_smtp(
        self, to: str, subject: str, body_text: str, body_html: str | None
    ) -> None:
        """Internal method to send message via SMTP.

        Args:
            to: Recipient email.
            subject: Subject line.
            body_text: Plain text body.
            body_html: Optional HTML body.

        Raises:
            smtplib.SMTPException: On SMTP errors.
        """
        server = smtplib.SMTP(self.smtp_host, self.smtp_port)
        try:
            server.starttls()
            server.login(self.smtp_user, self.settings.smtp_password)

            # Build message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = to

            # Create plain text part using set_payload to avoid encoding
            part_text = MIMEText("")
            part_text.set_type("text/plain")
            part_text.set_param("charset", "utf-8")
            part_text.set_payload(body_text)
            msg.attach(part_text)

            # Create HTML part using set_payload to avoid encoding
            if body_html:
                part_html = MIMEText("")
                part_html.set_type("text/html")
                part_html.set_param("charset", "utf-8")
                part_html.set_payload(body_html)
                msg.attach(part_html)

            server.send_message(msg)
        finally:
            server.quit()
