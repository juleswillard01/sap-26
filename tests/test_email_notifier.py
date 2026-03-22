"""Tests RED — EmailNotifier SMTP Gmail adapter.

Tests pour src/adapters/email_notifier.py (CDC §10 Notifications).

Coverage: Send email via SMTP Gmail, retry logic, error handling.
"""

from __future__ import annotations

import smtplib
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.email_notifier import EmailNotifier
from src.config import Settings


class TestEmailNotifierInit:
    """Tests for EmailNotifier initialization."""

    def test_init_with_valid_settings(self) -> None:
        """EmailNotifier initializes with Settings."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="test@gmail.com",
            smtp_password="app_password_xyz",
            notification_email="admin@example.com",
        )
        notifier = EmailNotifier(settings)
        assert notifier.settings == settings

    def test_init_stores_smtp_host(self) -> None:
        """EmailNotifier stores smtp_host from settings."""
        settings = Settings(smtp_host="smtp.gmail.com")
        notifier = EmailNotifier(settings)
        assert notifier.smtp_host == "smtp.gmail.com"

    def test_init_stores_smtp_port(self) -> None:
        """EmailNotifier stores smtp_port from settings."""
        settings = Settings(smtp_port=587)
        notifier = EmailNotifier(settings)
        assert notifier.smtp_port == 587

    def test_init_stores_smtp_user(self) -> None:
        """EmailNotifier stores smtp_user from settings."""
        settings = Settings(smtp_user="noreply@example.com")
        notifier = EmailNotifier(settings)
        assert notifier.smtp_user == "noreply@example.com"

    def test_init_stores_notification_email(self) -> None:
        """EmailNotifier stores notification_email from settings."""
        settings = Settings(notification_email="admin@example.com")
        notifier = EmailNotifier(settings)
        assert notifier.notification_email == "admin@example.com"


class TestEmailNotifierSendEmail:
    """Tests for EmailNotifier.send_email() method."""

    def test_send_email_calls_smtp_connection(self) -> None:
        """send_email establishes SMTP connection."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance
            mock_instance.send_message = MagicMock()

            notifier.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                body_text="Test body",
            )

            mock_smtp.assert_called_once_with("smtp.gmail.com", 587)

    def test_send_email_uses_starttls(self) -> None:
        """send_email calls starttls() for TLS encryption."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                body_text="Test body",
            )

            mock_instance.starttls.assert_called_once()

    def test_send_email_authenticates_with_smtp(self) -> None:
        """send_email calls login() with smtp_user and smtp_password."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password_secret",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_email(
                to="recipient@example.com",
                subject="Test Subject",
                body_text="Test body",
            )

            mock_instance.login.assert_called_once_with("noreply@gmail.com", "app_password_secret")

    def test_send_email_with_subject_and_text_body(self) -> None:
        """send_email sends message with correct subject and text body."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_email(
                to="recipient@example.com",
                subject="Invoice Reminder",
                body_text="Payment pending for 36+ hours",
            )

            # Verify send_message was called
            mock_instance.send_message.assert_called_once()
            # Extract the message object
            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert message["Subject"] == "Invoice Reminder"
            assert "Payment pending for 36+ hours" in message.as_string()

    def test_send_email_sends_to_correct_recipient(self) -> None:
        """send_email sends to provided 'to' address."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_email(
                to="customer@example.com",
                subject="Test",
                body_text="Test",
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert message["To"] == "customer@example.com"

    def test_send_email_sets_from_address(self) -> None:
        """send_email sets From header to smtp_user."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_email(
                to="recipient@example.com",
                subject="Test",
                body_text="Test",
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert message["From"] == "noreply@gmail.com"

    def test_send_email_closes_connection(self) -> None:
        """send_email calls quit() to close SMTP connection."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_email(
                to="recipient@example.com",
                subject="Test",
                body_text="Test",
            )

            mock_instance.quit.assert_called_once()

    def test_send_email_with_html_body(self) -> None:
        """send_email sends HTML body when provided."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_email(
                to="recipient@example.com",
                subject="Invoice",
                body_text="Plain text version",
                body_html="<html><body>HTML version</body></html>",
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert "<html><body>HTML version</body></html>" in message.as_string()

    def test_send_email_without_html_body(self) -> None:
        """send_email works without HTML body (text only)."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_email(
                to="recipient@example.com",
                subject="Test",
                body_text="Plain text only",
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert "Plain text only" in message.as_string()


class TestEmailNotifierErrorHandling:
    """Tests for error handling in EmailNotifier."""

    def test_send_email_smtp_connection_error_raises(self) -> None:
        """send_email raises when SMTP connection fails."""
        settings = Settings(
            smtp_host="invalid.host",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = smtplib.SMTPException("Connection failed")

            with pytest.raises(smtplib.SMTPException):
                notifier.send_email(
                    to="recipient@example.com",
                    subject="Test",
                    body_text="Test",
                )

    def test_send_email_authentication_error_raises(self) -> None:
        """send_email raises when SMTP authentication fails."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="wrong_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance
            mock_instance.login.side_effect = smtplib.SMTPAuthenticationError(
                535, "Authentication failed"
            )

            with pytest.raises(smtplib.SMTPAuthenticationError):
                notifier.send_email(
                    to="recipient@example.com",
                    subject="Test",
                    body_text="Test",
                )

    def test_send_email_retry_on_transient_error(self) -> None:
        """send_email retries on transient SMTP errors (max 3 retries)."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance
            # First call fails, second succeeds
            mock_instance.send_message.side_effect = [
                smtplib.SMTPServerDisconnected("Disconnected"),
                None,
            ]

            notifier.send_email(
                to="recipient@example.com",
                subject="Test",
                body_text="Test",
            )

            # Verify retry happened (send_message called twice)
            assert mock_instance.send_message.call_count == 2

    def test_send_email_fails_after_max_retries(self) -> None:
        """send_email raises after 3 failed retries."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance
            # Always fail
            mock_instance.send_message.side_effect = smtplib.SMTPServerDisconnected("Disconnected")

            with pytest.raises(smtplib.SMTPServerDisconnected):
                notifier.send_email(
                    to="recipient@example.com",
                    subject="Test",
                    body_text="Test",
                )

    def test_send_email_quit_called_on_error(self) -> None:
        """send_email calls quit() even if send fails."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance
            mock_instance.send_message.side_effect = smtplib.SMTPException("Error")

            with pytest.raises(smtplib.SMTPException):
                notifier.send_email(
                    to="recipient@example.com",
                    subject="Test",
                    body_text="Test",
                )

            # quit() should still be called (in finally block)
            mock_instance.quit.assert_called()


class TestEmailNotifierSendReminderEmail:
    """Tests for EmailNotifier.send_reminder_email() method."""

    def test_send_reminder_email_sends_formatted_message(self) -> None:
        """send_reminder_email sends email with formatted reminder content."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_reminder_email(
                invoice_id="INV-001",
                client_name="Client ABC",
                amount_due=1500.00,
                due_date="2026-03-24",
                days_pending=36,
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            message_str = message.as_string()

            # Verify reminder content
            assert "INV-001" in message_str or "INV-001" in message["Subject"]
            assert "1500" in message_str
            assert "36" in message_str

    def test_send_reminder_email_subject_contains_invoice_id(self) -> None:
        """send_reminder_email subject includes invoice_id."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_reminder_email(
                invoice_id="INV-12345",
                client_name="Test Client",
                amount_due=500.00,
                due_date="2026-03-24",
                days_pending=36,
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert "INV-12345" in message["Subject"]

    def test_send_reminder_email_body_contains_client_name(self) -> None:
        """send_reminder_email body includes client_name."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_reminder_email(
                invoice_id="INV-001",
                client_name="Jean Dupont",
                amount_due=1500.00,
                due_date="2026-03-24",
                days_pending=36,
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert "Jean Dupont" in message.as_string()

    def test_send_reminder_email_body_contains_amount(self) -> None:
        """send_reminder_email body includes amount_due."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_reminder_email(
                invoice_id="INV-001",
                client_name="Client ABC",
                amount_due=2750.50,
                due_date="2026-03-24",
                days_pending=36,
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert "2750.50" in message.as_string() or "2750" in message.as_string()

    def test_send_reminder_email_body_contains_days_pending(self) -> None:
        """send_reminder_email body indicates days_pending."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_reminder_email(
                invoice_id="INV-001",
                client_name="Client ABC",
                amount_due=1500.00,
                due_date="2026-03-24",
                days_pending=45,
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert "45" in message.as_string()

    def test_send_reminder_email_sends_to_notification_email(self) -> None:
        """send_reminder_email sends to notification_email from settings."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="admin@company.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_reminder_email(
                invoice_id="INV-001",
                client_name="Client ABC",
                amount_due=1500.00,
                due_date="2026-03-24",
                days_pending=36,
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert message["To"] == "admin@company.com"

    def test_send_reminder_email_with_html_formatting(self) -> None:
        """send_reminder_email includes HTML formatted body."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_reminder_email(
                invoice_id="INV-001",
                client_name="Client ABC",
                amount_due=1500.00,
                due_date="2026-03-24",
                days_pending=36,
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            message_str = message.as_string()
            # Should have some HTML structure
            assert "<" in message_str and ">" in message_str


class TestEmailNotifierSyncFailedNotification:
    """Tests for EmailNotifier.send_sync_failed_email() method."""

    def test_send_sync_failed_email_sends_alert(self) -> None:
        """send_sync_failed_email sends error notification."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_sync_failed_email(
                error_message="Connection timeout to AIS",
                sync_type="ais",
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert "error" in message["Subject"].lower()
            assert "Connection timeout to AIS" in message.as_string()

    def test_send_sync_failed_email_includes_error_message(self) -> None:
        """send_sync_failed_email body contains error_message."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_sync_failed_email(
                error_message="Failed to parse Indy CSV",
                sync_type="indy",
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert "Failed to parse Indy CSV" in message.as_string()

    def test_send_sync_failed_email_includes_sync_type(self) -> None:
        """send_sync_failed_email indicates which sync failed (ais/indy)."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_sync_failed_email(
                error_message="Error",
                sync_type="ais",
            )

            call_args = mock_instance.send_message.call_args
            message = call_args[0][0]
            assert "ais" in message.as_string().lower()


class TestEmailNotifierIntegration:
    """Integration tests for EmailNotifier."""

    def test_multiple_emails_in_sequence(self) -> None:
        """EmailNotifier can send multiple emails sequentially."""
        settings = Settings(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@gmail.com",
            smtp_password="app_password",
            notification_email="jules@example.com",
        )
        notifier = EmailNotifier(settings)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value = mock_instance

            notifier.send_email(
                to="recipient1@example.com",
                subject="Test 1",
                body_text="Body 1",
            )
            notifier.send_email(
                to="recipient2@example.com",
                subject="Test 2",
                body_text="Body 2",
            )

            # Verify SMTP was used twice
            assert mock_smtp.call_count == 2
            assert mock_instance.send_message.call_count == 2
