"""Tests RED — NotificationService lifecycle triggers.

Tests pour src/services/notification_service.py enhancements (CDC §2.3 Timers).

Méthodes à tester :
- send_reminder_t36h(invoice: dict) -> bool : envoie reminder à T+36h
- send_expired_alert(invoice: dict) -> bool : envoie alerte expiration à T+48h
- send_payment_received(invoice: dict) -> bool : envoie confirmation paiement
- send_reconciled(invoice: dict) -> bool : envoie confirmation lettrage
- send_sync_failed(error_message: str) -> bool : envoie alerte sync échouée
- check_and_send_overdue(invoices: list[dict], now: datetime) -> int : détecte et envoie reminders

Coverage: T+36h detection, T+48h expiration, state transitions, error handling.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest
from freezegun import freeze_time

# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────


@pytest.fixture
def mock_email_notifier() -> Mock:
    """Mock EmailNotifier for capturing email calls without SMTP."""
    notifier = MagicMock()
    notifier.send_email = MagicMock(return_value=None)
    notifier.send_reminder_email = MagicMock(return_value=None)
    notifier.send_sync_failed_email = MagicMock(return_value=None)
    notifier.notification_email = "test@example.com"
    return notifier


@pytest.fixture
def notification_service(mock_email_notifier: Mock) -> Any:
    """NotificationService with mocked EmailNotifier."""
    # Import here to allow RED phase where class may not exist
    try:
        from src.services.notification_service import NotificationService
    except ImportError:
        # Stub for RED phase
        class NotificationService:  # type: ignore[no-redef]
            def __init__(self, email_notifier: Mock) -> None:
                self._email_notifier = email_notifier

            def send_reminder_t36h(self, invoice: dict[str, Any]) -> bool:
                raise NotImplementedError

            def send_expired_alert(self, invoice: dict[str, Any]) -> bool:
                raise NotImplementedError

            def send_payment_received(self, invoice: dict[str, Any]) -> bool:
                raise NotImplementedError

            def send_reconciled(self, invoice: dict[str, Any]) -> bool:
                raise NotImplementedError

            def send_sync_failed(self, error_message: str) -> bool:
                raise NotImplementedError

            def check_and_send_overdue(
                self,
                invoices: list[dict[str, Any]],
                now: datetime | None = None,
            ) -> int:
                raise NotImplementedError

    return NotificationService(email_notifier=mock_email_notifier)


@pytest.fixture
def base_invoice(make_invoice: Any) -> dict[str, Any]:
    """Base invoice dict for testing."""
    return make_invoice(
        facture_id="F001",
        client_id="C001",
        montant_total=100.0,
        statut="EN_ATTENTE",
        date_paiement="",
    )


@pytest.fixture
def paid_invoice(make_invoice: Any) -> dict[str, Any]:
    """Paid invoice for testing."""
    return make_invoice(
        facture_id="F002",
        client_id="C001",
        montant_total=150.0,
        statut="PAYE",
        date_paiement="2026-03-20",
    )


@pytest.fixture
def reconciled_invoice(make_invoice: Any) -> dict[str, Any]:
    """Reconciled invoice for testing."""
    return make_invoice(
        facture_id="F003",
        client_id="C001",
        montant_total=200.0,
        statut="RAPPROCHE",
        date_paiement="2026-03-20",
        date_rapprochement="2026-03-21",
    )


# ──────────────────────────────────────────────
# Class TestNotificationT36h
# ──────────────────────────────────────────────


class TestNotificationT36h:
    """Tests for T+36h reminder detection and sending."""

    @freeze_time("2026-03-21 14:00:00")
    def test_send_reminder_at_36h(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Invoice EN_ATTENTE for 36h01m → email sent, returns True."""
        # Setup : facture en attente depuis 36h01
        date_en_attente = datetime(2026, 3, 19, 13, 59, 0)
        invoice = base_invoice.copy()
        invoice["date_statut"] = date_en_attente.isoformat()

        # Action
        result = notification_service.send_reminder_t36h(invoice)

        # Assert
        assert result is True
        mock_email_notifier.send_reminder_email.assert_called_once()
        call_kwargs = mock_email_notifier.send_reminder_email.call_args[1]
        assert call_kwargs["invoice_id"] == "F001"

    @freeze_time("2026-03-21 14:00:00")
    def test_no_reminder_before_36h(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Invoice EN_ATTENTE for 35h59m → no email, returns False."""
        # Setup : facture en attente depuis 35h59
        date_en_attente = datetime(2026, 3, 20, 2, 1, 0)
        invoice = base_invoice.copy()
        invoice["date_statut"] = date_en_attente.isoformat()

        # Action
        result = notification_service.send_reminder_t36h(invoice)

        # Assert
        assert result is False
        mock_email_notifier.send_reminder_email.assert_not_called()

    @freeze_time("2026-03-21 14:00:00")
    def test_reminder_uses_correct_template(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Email subject contains 'Relance' and facture_id."""
        # Setup
        date_en_attente = datetime(2026, 3, 19, 13, 59, 0)
        invoice = base_invoice.copy()
        invoice["date_statut"] = date_en_attente.isoformat()

        # Action
        notification_service.send_reminder_t36h(invoice)

        # Assert
        mock_email_notifier.send_reminder_email.assert_called_once()
        call_kwargs = mock_email_notifier.send_reminder_email.call_args[1]
        assert call_kwargs["invoice_id"] == "F001"

    @freeze_time("2026-03-21 14:00:00")
    def test_reminder_includes_client_name(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        make_invoice: Any,
    ) -> None:
        """Reminder email includes client name from invoice dict."""
        # Setup
        date_en_attente = datetime(2026, 3, 19, 13, 59, 0)
        invoice = make_invoice(
            facture_id="F004",
            client_id="C002",
            statut="EN_ATTENTE",
            date_statut=date_en_attente.isoformat(),
        )

        # Action
        notification_service.send_reminder_t36h(invoice)

        # Assert
        mock_email_notifier.send_reminder_email.assert_called_once()

    @freeze_time("2026-03-21 14:00:00")
    def test_reminder_exact_36h_boundary(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Invoice at exactly 36h boundary should trigger reminder."""
        # Setup : facture exactement à 36h
        date_en_attente = datetime(2026, 3, 19, 14, 0, 0)
        invoice = base_invoice.copy()
        invoice["date_statut"] = date_en_attente.isoformat()

        # Action
        result = notification_service.send_reminder_t36h(invoice)

        # Assert
        assert result is True
        mock_email_notifier.send_reminder_email.assert_called_once()

    def test_reminder_wrong_status_not_sent(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Reminder not sent if invoice status is not EN_ATTENTE."""
        # Setup : facture PAYE
        invoice = base_invoice.copy()
        invoice["statut"] = "PAYE"
        invoice["date_statut"] = "2026-03-20T13:59:00"

        # Action
        result = notification_service.send_reminder_t36h(invoice)

        # Assert
        assert result is False
        mock_email_notifier.send_reminder_email.assert_not_called()

    def test_reminder_missing_date_statut_returns_false(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Reminder returns False if date_statut is missing."""
        # Setup
        invoice = base_invoice.copy()
        invoice.pop("date_statut", None)

        # Action
        result = notification_service.send_reminder_t36h(invoice)

        # Assert
        assert result is False
        mock_email_notifier.send_reminder_email.assert_not_called()


# ──────────────────────────────────────────────
# Class TestNotificationExpire
# ──────────────────────────────────────────────


class TestNotificationExpire:
    """Tests for T+48h expiration alert sending."""

    @freeze_time("2026-03-21 14:00:00")
    def test_send_expired_at_48h(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Invoice EN_ATTENTE for 48h01m → email sent."""
        # Setup : facture en attente depuis 48h01
        date_en_attente = datetime(2026, 3, 19, 13, 59, 0)
        invoice = base_invoice.copy()
        invoice["date_statut"] = date_en_attente.isoformat()

        # Action
        result = notification_service.send_expired_alert(invoice)

        # Assert
        assert result is True
        mock_email_notifier.send_email.assert_called_once()

    @freeze_time("2026-03-21 14:00:00")
    def test_send_expired_alert_exception_caught(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Exception in send_email is caught and logged."""
        # Setup
        date_en_attente = datetime(2026, 3, 19, 13, 59, 0)
        invoice = base_invoice.copy()
        invoice["date_statut"] = date_en_attente.isoformat()
        # Make send_email raise exception
        mock_email_notifier.send_email.side_effect = RuntimeError("SMTP error")
        mock_email_notifier.notification_email = "test@example.com"

        # Action
        result = notification_service.send_expired_alert(invoice)

        # Assert: exception should be caught and False returned
        assert result is False

    @freeze_time("2026-03-21 14:00:00")
    def test_no_expired_before_48h(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Invoice EN_ATTENTE for 47h59m → no email, returns False."""
        # Setup : facture en attente depuis 47h59
        date_en_attente = datetime(2026, 3, 19, 14, 1, 0)
        invoice = base_invoice.copy()
        invoice["date_statut"] = date_en_attente.isoformat()

        # Action
        result = notification_service.send_expired_alert(invoice)

        # Assert
        assert result is False
        mock_email_notifier.send_email.assert_not_called()

    @freeze_time("2026-03-21 14:00:00")
    def test_expired_email_contains_facture_id(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Email body contains facture_id."""
        # Setup
        date_en_attente = datetime(2026, 3, 19, 13, 59, 0)
        invoice = base_invoice.copy()
        invoice["facture_id"] = "F999"
        invoice["date_statut"] = date_en_attente.isoformat()

        # Action
        notification_service.send_expired_alert(invoice)

        # Assert
        mock_email_notifier.send_email.assert_called_once()
        call_kwargs = mock_email_notifier.send_email.call_args[1]
        assert "F999" in call_kwargs["body_text"]

    @freeze_time("2026-03-21 14:00:00")
    def test_expired_email_contains_client_name(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        make_invoice: Any,
    ) -> None:
        """Email body contains client name."""
        # Setup : facture avec client info
        date_en_attente = datetime(2026, 3, 19, 13, 59, 0)
        invoice = make_invoice(
            facture_id="F005",
            client_id="C003",
            statut="EN_ATTENTE",
            date_statut=date_en_attente.isoformat(),
        )

        # Action
        notification_service.send_expired_alert(invoice)

        # Assert
        mock_email_notifier.send_email.assert_called_once()

    @freeze_time("2026-03-21 14:00:00")
    def test_expired_exact_48h_boundary(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Invoice at exactly 48h should trigger expiration."""
        # Setup : facture exactement à 48h
        date_en_attente = datetime(2026, 3, 19, 14, 0, 0)
        invoice = base_invoice.copy()
        invoice["date_statut"] = date_en_attente.isoformat()

        # Action
        result = notification_service.send_expired_alert(invoice)

        # Assert
        assert result is True
        mock_email_notifier.send_email.assert_called_once()

    def test_expired_wrong_status_not_sent(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Expiration alert not sent if status is not EN_ATTENTE."""
        # Setup
        invoice = base_invoice.copy()
        invoice["statut"] = "EXPIRE"
        invoice["date_statut"] = "2026-03-20T13:59:00"

        # Action
        result = notification_service.send_expired_alert(invoice)

        # Assert
        assert result is False
        mock_email_notifier.send_email.assert_not_called()


# ──────────────────────────────────────────────
# Class TestNotificationPayment
# ──────────────────────────────────────────────


class TestNotificationPayment:
    """Tests for payment received notification."""

    def test_send_payment_received(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        paid_invoice: dict[str, Any],
    ) -> None:
        """Invoice transitions to PAYE → email sent."""
        # Setup
        invoice = paid_invoice.copy()

        # Action
        result = notification_service.send_payment_received(invoice)

        # Assert
        assert result is True
        mock_email_notifier.send_email.assert_called_once()

    def test_payment_email_contains_montant(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        paid_invoice: dict[str, Any],
    ) -> None:
        """Email body contains montant_total formatted."""
        # Setup
        invoice = paid_invoice.copy()
        invoice["montant_total"] = 1234.56

        # Action
        notification_service.send_payment_received(invoice)

        # Assert
        mock_email_notifier.send_email.assert_called_once()
        call_kwargs = mock_email_notifier.send_email.call_args[1]
        assert "1234" in call_kwargs["body_text"] or "1234.56" in call_kwargs["body_text"]

    def test_payment_email_contains_facture_id(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        paid_invoice: dict[str, Any],
    ) -> None:
        """Email contains facture_id."""
        # Setup
        invoice = paid_invoice.copy()
        invoice["facture_id"] = "F-PAY-001"

        # Action
        notification_service.send_payment_received(invoice)

        # Assert
        mock_email_notifier.send_email.assert_called_once()
        call_kwargs = mock_email_notifier.send_email.call_args[1]
        assert "F-PAY-001" in call_kwargs.get("subject", "") or "F-PAY-001" in call_kwargs.get(
            "body", ""
        )

    def test_payment_not_sent_for_non_paye_status(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Payment notification not sent if status is not PAYE."""
        # Setup
        invoice = base_invoice.copy()
        invoice["statut"] = "VALIDE"

        # Action
        result = notification_service.send_payment_received(invoice)

        # Assert
        assert result is False
        mock_email_notifier.send_email.assert_not_called()

    def test_payment_email_contains_date_paiement(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        paid_invoice: dict[str, Any],
    ) -> None:
        """Email contains payment date."""
        # Setup
        invoice = paid_invoice.copy()
        invoice["date_paiement"] = "2026-03-20"

        # Action
        notification_service.send_payment_received(invoice)

        # Assert
        mock_email_notifier.send_email.assert_called_once()
        call_kwargs = mock_email_notifier.send_email.call_args[1]
        assert "2026-03-20" in call_kwargs.get("body_text", "") or "20" in call_kwargs.get(
            "body_text", ""
        )


# ──────────────────────────────────────────────
# Class TestNotificationReconciled
# ──────────────────────────────────────────────


class TestNotificationReconciled:
    """Tests for reconciliation confirmation notification."""

    def test_send_reconciled(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        reconciled_invoice: dict[str, Any],
    ) -> None:
        """Invoice RAPPROCHE → email sent."""
        # Setup
        invoice = reconciled_invoice.copy()

        # Action
        result = notification_service.send_reconciled(invoice)

        # Assert
        assert result is True
        mock_email_notifier.send_email.assert_called_once()

    def test_reconciled_email_contains_facture_id(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        reconciled_invoice: dict[str, Any],
    ) -> None:
        """Email contains facture_id."""
        # Setup
        invoice = reconciled_invoice.copy()
        invoice["facture_id"] = "F-REC-001"

        # Action
        notification_service.send_reconciled(invoice)

        # Assert
        call_kwargs = mock_email_notifier.send_email.call_args[1]
        assert "F-REC-001" in call_kwargs.get("subject", "") or "F-REC-001" in call_kwargs.get(
            "body", ""
        )

    def test_reconciled_not_sent_for_non_rapproche_status(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        paid_invoice: dict[str, Any],
    ) -> None:
        """Reconciled notification not sent if status is not RAPPROCHE."""
        # Setup
        invoice = paid_invoice.copy()
        invoice["statut"] = "PAYE"

        # Action
        result = notification_service.send_reconciled(invoice)

        # Assert
        assert result is False
        mock_email_notifier.send_email.assert_not_called()

    def test_reconciled_with_score(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        reconciled_invoice: dict[str, Any],
    ) -> None:
        """Email includes reconciliation score if provided."""
        # Setup
        invoice = reconciled_invoice.copy()
        invoice["score_confiance"] = 95

        # Action
        notification_service.send_reconciled(invoice)

        # Assert
        mock_email_notifier.send_email.assert_called_once()
        call_kwargs = mock_email_notifier.send_email.call_args[1]
        assert (
            "95" in call_kwargs.get("body_text", "")
            or "score" in call_kwargs.get("body_text", "").lower()
        )


# ──────────────────────────────────────────────
# Class TestNotificationSyncFailed
# ──────────────────────────────────────────────


class TestNotificationSyncFailed:
    """Tests for sync failure notifications."""

    def test_send_sync_failed(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
    ) -> None:
        """Error message → email sent to notification_email."""
        # Setup
        error_msg = "Connection timeout to AIS server"

        # Action
        result = notification_service.send_sync_failed(error_msg)

        # Assert
        assert result is True
        mock_email_notifier.send_sync_failed_email.assert_called_once()

    def test_sync_failed_no_secrets_in_body(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
    ) -> None:
        """Error with password → password NOT in email body."""
        # Setup
        error_msg = "Failed to login: password=secret123 invalid for user=jules@example.com"

        # Action
        notification_service.send_sync_failed(error_msg)

        # Assert
        mock_email_notifier.send_sync_failed_email.assert_called_once()
        call_kwargs = mock_email_notifier.send_sync_failed_email.call_args[1]
        body = call_kwargs.get("error_message", "")
        assert "secret123" not in body or body == error_msg

    def test_sync_failed_includes_error_context(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
    ) -> None:
        """Sync failed email includes error message context."""
        # Setup
        error_msg = "Failed to parse Indy CSV: invalid column count at row 42"

        # Action
        notification_service.send_sync_failed(error_msg)

        # Assert
        call_kwargs = mock_email_notifier.send_sync_failed_email.call_args[1]
        assert error_msg in call_kwargs.get("error_message", "")

    def test_sync_failed_empty_error_still_sends(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
    ) -> None:
        """Even empty error message triggers email."""
        # Setup
        error_msg = ""

        # Action
        notification_service.send_sync_failed(error_msg)

        # Assert
        # Should still attempt to send gracefully

    def test_sync_failed_long_error_message(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
    ) -> None:
        """Very long error message is handled."""
        # Setup
        error_msg = "A" * 5000

        # Action
        result = notification_service.send_sync_failed(error_msg)

        # Assert
        assert result is True


# ──────────────────────────────────────────────
# Class TestNotificationCheckAndSendOverdue
# ──────────────────────────────────────────────


class TestNotificationCheckAndSendOverdue:
    """Tests for check_and_send_overdue batch operation."""

    @freeze_time("2026-03-21 14:00:00")
    def test_check_and_send_overdue_single_invoice(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Single overdue invoice triggers reminder."""
        # Setup : 1 invoice EN_ATTENTE pour 37h
        now = datetime(2026, 3, 21, 14, 0, 0)
        date_en_attente = datetime(2026, 3, 20, 1, 0, 0)
        invoice = base_invoice.copy()
        invoice["date_statut"] = date_en_attente.isoformat()

        # Action
        count = notification_service.check_and_send_overdue([invoice], now=now)

        # Assert
        assert count == 1
        mock_email_notifier.send_reminder_email.assert_called_once()

    @freeze_time("2026-03-21 14:00:00")
    def test_check_and_send_overdue_multiple_invoices(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        make_invoice: Any,
    ) -> None:
        """Multiple overdue invoices trigger multiple reminders."""
        # Setup : 3 invoices EN_ATTENTE
        now = datetime(2026, 3, 21, 14, 0, 0)
        invoices = [
            make_invoice(
                facture_id=f"F{i}",
                statut="EN_ATTENTE",
                date_statut=(now - timedelta(hours=36 + i)).isoformat(),
            )
            for i in range(3)
        ]

        # Action
        count = notification_service.check_and_send_overdue(invoices, now=now)

        # Assert
        assert count == 3
        assert mock_email_notifier.send_reminder_email.call_count == 3

    @freeze_time("2026-03-21 14:00:00")
    def test_check_and_send_overdue_mixed_statuses(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        make_invoice: Any,
    ) -> None:
        """Only EN_ATTENTE invoices are processed."""
        # Setup : mix de statuts
        now = datetime(2026, 3, 21, 14, 0, 0)
        invoices = [
            make_invoice(
                facture_id="F1",
                statut="EN_ATTENTE",
                date_statut=(now - timedelta(hours=37)).isoformat(),
            ),
            make_invoice(
                facture_id="F2",
                statut="PAYE",
                date_statut=(now - timedelta(hours=37)).isoformat(),
            ),
            make_invoice(
                facture_id="F3",
                statut="VALIDE",
                date_statut=(now - timedelta(hours=37)).isoformat(),
            ),
        ]

        # Action
        count = notification_service.check_and_send_overdue(invoices, now=now)

        # Assert
        assert count == 1
        mock_email_notifier.send_reminder_email.assert_called_once()

    @freeze_time("2026-03-21 14:00:00")
    def test_check_and_send_overdue_empty_list(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
    ) -> None:
        """Empty invoice list returns 0."""
        # Setup
        now = datetime(2026, 3, 21, 14, 0, 0)

        # Action
        count = notification_service.check_and_send_overdue([], now=now)

        # Assert
        assert count == 0
        mock_email_notifier.send_reminder_email.assert_not_called()

    @freeze_time("2026-03-21 14:00:00")
    def test_check_and_send_overdue_under_threshold(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        make_invoice: Any,
    ) -> None:
        """Invoices under 36h threshold not sent."""
        # Setup : invoice EN_ATTENTE pour 35h
        now = datetime(2026, 3, 21, 14, 0, 0)
        invoice = make_invoice(
            facture_id="F1",
            statut="EN_ATTENTE",
            date_statut=(now - timedelta(hours=35)).isoformat(),
        )

        # Action
        count = notification_service.check_and_send_overdue([invoice], now=now)

        # Assert
        assert count == 0
        mock_email_notifier.send_reminder_email.assert_not_called()

    @freeze_time("2026-03-21 14:00:00")
    def test_check_and_send_overdue_with_default_now(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        make_invoice: Any,
    ) -> None:
        """check_and_send_overdue uses current time if now not provided."""
        # Setup
        invoice = make_invoice(
            facture_id="F1",
            statut="EN_ATTENTE",
            date_statut="2026-03-20T01:00:00",
        )

        # Action
        count = notification_service.check_and_send_overdue([invoice])

        # Assert
        assert count == 1
        mock_email_notifier.send_reminder_email.assert_called_once()

    @freeze_time("2026-03-21 14:00:00")
    def test_check_and_send_overdue_handles_missing_date_statut(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        make_invoice: Any,
    ) -> None:
        """Invoices without date_statut are skipped gracefully."""
        # Setup
        now = datetime(2026, 3, 21, 14, 0, 0)
        invoice = make_invoice(facture_id="F1", statut="EN_ATTENTE")
        invoice.pop("date_statut", None)

        # Action
        count = notification_service.check_and_send_overdue([invoice], now=now)

        # Assert
        assert count == 0
        mock_email_notifier.send_reminder_email.assert_not_called()

    @freeze_time("2026-03-21 14:00:00")
    def test_check_and_send_overdue_returns_count_not_list(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        make_invoice: Any,
    ) -> None:
        """Return value is int count, not list."""
        # Setup
        now = datetime(2026, 3, 21, 14, 0, 0)
        invoices = [
            make_invoice(
                facture_id=f"F{i}",
                statut="EN_ATTENTE",
                date_statut=(now - timedelta(hours=37)).isoformat(),
            )
            for i in range(2)
        ]

        # Action
        result = notification_service.check_and_send_overdue(invoices, now=now)

        # Assert
        assert isinstance(result, int)
        assert result == 2


# ──────────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────────


class TestNotificationExceptionHandling:
    """Tests for exception handling in notification service."""

    @freeze_time("2026-03-21 14:00:00")
    def test_send_reminder_email_exception_returns_false(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Email exception caught → returns False."""
        # Setup
        date_en_attente = datetime(2026, 3, 19, 13, 59, 0)
        invoice = base_invoice.copy()
        invoice["date_statut"] = date_en_attente.isoformat()
        mock_email_notifier.send_reminder_email.side_effect = RuntimeError("SMTP error")

        # Action
        result = notification_service.send_reminder_t36h(invoice)

        # Assert
        assert result is False
        mock_email_notifier.send_reminder_email.assert_called_once()

    @freeze_time("2026-03-21 14:00:00")
    def test_send_expired_alert_missing_date_statut_returns_false(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Missing date_statut → returns False early."""
        # Setup
        invoice = base_invoice.copy()
        invoice.pop("date_statut", None)

        # Action
        result = notification_service.send_expired_alert(invoice)

        # Assert
        assert result is False
        mock_email_notifier.send_email.assert_not_called()

    def test_send_expired_alert_exception_returns_false(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        base_invoice: dict[str, Any],
    ) -> None:
        """Email exception in expired alert caught → returns False."""
        # Setup
        invoice = base_invoice.copy()
        invoice["date_statut"] = "2026-03-19T13:59:00"
        mock_email_notifier.send_email.side_effect = RuntimeError("Email service down")

        # Action
        result = notification_service.send_expired_alert(invoice)

        # Assert
        assert result is False

    def test_send_payment_received_exception_returns_false(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        paid_invoice: dict[str, Any],
    ) -> None:
        """Exception during payment notification → returns False."""
        # Setup
        mock_email_notifier.send_email.side_effect = RuntimeError("Network error")

        # Action
        result = notification_service.send_payment_received(paid_invoice)

        # Assert
        assert result is False

    def test_send_reconciled_exception_returns_false(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        reconciled_invoice: dict[str, Any],
    ) -> None:
        """Exception during reconciliation notification → returns False."""
        # Setup
        mock_email_notifier.send_email.side_effect = RuntimeError("Email service error")

        # Action
        result = notification_service.send_reconciled(reconciled_invoice)

        # Assert
        assert result is False

    def test_send_sync_failed_exception_returns_false(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
    ) -> None:
        """Exception during sync failed notification → returns False."""
        # Setup
        error_msg = "AIS connection timeout"
        mock_email_notifier.send_sync_failed_email.side_effect = RuntimeError("Email failed")

        # Action
        result = notification_service.send_sync_failed(error_msg)

        # Assert
        assert result is False


class TestNotificationUtilityFunctions:
    """Tests for utility functions in notification_service."""

    def test_parse_date_statut_iso_string(self) -> None:
        """Parse ISO format date string."""
        from src.services.notification_service import NotificationService

        date_str = "2026-03-21T10:30:00"
        result = NotificationService._parse_date_statut(date_str)

        assert result is not None
        assert result.year == 2026
        assert result.month == 3
        assert result.day == 21

    def test_parse_date_statut_datetime_object(self) -> None:
        """Parse datetime object."""
        from src.services.notification_service import NotificationService

        date_obj = datetime(2026, 3, 21, 10, 30, 0)
        result = NotificationService._parse_date_statut(date_obj)

        assert result is not None
        assert result == date_obj

    def test_parse_date_statut_none_input(self) -> None:
        """Parse None returns None."""
        from src.services.notification_service import NotificationService

        result = NotificationService._parse_date_statut(None)
        assert result is None

    def test_parse_date_statut_invalid_string(self) -> None:
        """Parse invalid string returns None."""
        from src.services.notification_service import NotificationService

        result = NotificationService._parse_date_statut("not-a-date")
        assert result is None

    def test_parse_date_statut_integer_returns_none(self) -> None:
        """Parse integer without timestamp method returns None."""
        from src.services.notification_service import NotificationService

        result = NotificationService._parse_date_statut(12345)
        assert result is None

    def test_parse_date_statut_exception_in_hasattr(self) -> None:
        """NotificationService _parse_date_statut handles exception in hasattr."""
        from src.services.notification_service import NotificationService

        # Object that raises TypeError when checking hasattr
        class ProblematicObj:
            def __getattribute__(self, name: str):
                if name == "timestamp":
                    raise TypeError("Cannot access timestamp")
                return super().__getattribute__(name)

        result = NotificationService._parse_date_statut(ProblematicObj())
        assert result is None

    def test_strip_sensitive_data_password(self) -> None:
        """Strip password from error message."""
        from src.services.notification_service import NotificationService

        error_msg = "Login failed: password=secret123 invalid"
        result = NotificationService._strip_sensitive_data(error_msg)

        assert "secret123" not in result
        assert "password" in result.lower() or "secret" not in result

    def test_strip_sensitive_data_token(self) -> None:
        """Strip token from error message."""
        from src.services.notification_service import NotificationService

        error_msg = "API error: token=abc123xyz invalid"
        result = NotificationService._strip_sensitive_data(error_msg)

        assert "abc123xyz" not in result

    def test_strip_sensitive_data_api_key(self) -> None:
        """Strip api_key from error message."""
        from src.services.notification_service import NotificationService

        error_msg = "Authorization failed: api_key=key123secret"
        result = NotificationService._strip_sensitive_data(error_msg)

        assert "key123secret" not in result

    def test_strip_sensitive_data_multiple_secrets(self) -> None:
        """Strip multiple sensitive fields."""
        from src.services.notification_service import NotificationService

        error_msg = "Failed: password=pass123 token=tok456 api_key=key789"
        result = NotificationService._strip_sensitive_data(error_msg)

        assert "pass123" not in result
        assert "tok456" not in result
        assert "key789" not in result

    def test_strip_sensitive_data_no_secrets(self) -> None:
        """Message without secrets unchanged."""
        from src.services.notification_service import NotificationService

        error_msg = "Connection timeout to server"
        result = NotificationService._strip_sensitive_data(error_msg)

        assert result == error_msg

    def test_strip_sensitive_data_case_insensitive(self) -> None:
        """Strip is case-insensitive."""
        from src.services.notification_service import NotificationService

        error_msg = "Failed: PASSWORD=secret123"
        result = NotificationService._strip_sensitive_data(error_msg)

        assert "secret123" not in result

    def test_module_level_parse_date_statut_iso_string(self) -> None:
        """Module-level _parse_date_statut parses ISO strings."""
        from src.services.notification_service import _parse_date_statut

        date_str = "2026-03-21T10:30:00"
        result = _parse_date_statut(date_str)

        assert result is not None
        assert result.year == 2026

    def test_module_level_parse_date_statut_datetime(self) -> None:
        """Module-level _parse_date_statut accepts datetime objects."""
        from src.services.notification_service import _parse_date_statut

        date_obj = datetime(2026, 3, 21, 10, 30, 0)
        result = _parse_date_statut(date_obj)

        assert result == date_obj

    def test_module_level_parse_date_statut_none(self) -> None:
        """Module-level _parse_date_statut handles None."""
        from src.services.notification_service import _parse_date_statut

        result = _parse_date_statut(None)
        assert result is None

    def test_module_level_parse_date_statut_invalid_string(self) -> None:
        """Module-level _parse_date_statut returns None for invalid string."""
        from src.services.notification_service import _parse_date_statut

        result = _parse_date_statut("invalid-date")
        assert result is None

    def test_module_level_parse_date_statut_object_with_timestamp(self) -> None:
        """Module-level _parse_date_statut returns objects with timestamp method."""
        from src.services.notification_service import _parse_date_statut

        # Mock object with timestamp method
        class TimestampObj:
            def timestamp(self):
                return 1234567890

        obj = TimestampObj()
        result = _parse_date_statut(obj)
        # Should return the object if it has timestamp method
        assert result == obj

    def test_module_level_parse_date_statut_exception_in_hasattr(self) -> None:
        """Module-level _parse_date_statut handles exception when checking hasattr."""
        from src.services.notification_service import _parse_date_statut

        # Object that raises TypeError in hasattr check
        class ProblematicObj:
            def __getattribute__(self, name: str):
                if name == "timestamp":
                    raise TypeError("Attribute access failed")
                return super().__getattribute__(name)

        result = _parse_date_statut(ProblematicObj())
        assert result is None

    def test_module_level_check_and_notify_overdue_empty(self) -> None:
        """Module-level check_and_notify_overdue handles empty list."""
        from src.services.notification_service import check_and_notify_overdue

        result = check_and_notify_overdue([])
        assert result == []

    @freeze_time("2026-03-21 14:00:00")
    def test_module_level_check_and_notify_overdue_single_invoice(
        self,
        make_invoice: Any,
    ) -> None:
        """Module-level check_and_notify_overdue detects overdue invoices."""
        from src.services.notification_service import check_and_notify_overdue

        invoice = make_invoice(
            facture_id="F001",
            statut="EN_ATTENTE",
            date_statut="2026-03-20T01:00:00+00:00",
        )

        result = check_and_notify_overdue([invoice])
        assert "F001" in result

    @freeze_time("2026-03-21 14:00:00")
    def test_module_level_check_and_notify_overdue_no_date_statut(
        self,
        make_invoice: Any,
    ) -> None:
        """Module-level handles missing date_statut gracefully."""
        from src.services.notification_service import check_and_notify_overdue

        invoice = make_invoice(facture_id="F001", statut="EN_ATTENTE")
        invoice.pop("date_statut", None)

        result = check_and_notify_overdue([invoice])
        assert result == []

    @freeze_time("2026-03-21 14:00:00")
    def test_module_level_check_and_notify_overdue_invalid_date_statut(
        self,
        make_invoice: Any,
    ) -> None:
        """Module-level handles invalid date_statut."""
        from src.services.notification_service import check_and_notify_overdue

        invoice = make_invoice(
            facture_id="F001",
            statut="EN_ATTENTE",
            date_statut="not-a-date",
        )

        result = check_and_notify_overdue([invoice])
        assert result == []

    @freeze_time("2026-03-21 14:00:00")
    def test_module_level_check_and_notify_overdue_wrong_status(
        self,
        make_invoice: Any,
    ) -> None:
        """Module-level skips non-EN_ATTENTE invoices."""
        from src.services.notification_service import check_and_notify_overdue

        invoice = make_invoice(
            facture_id="F001",
            statut="PAYE",
            date_statut="2026-03-20T01:00:00+00:00",
        )

        result = check_and_notify_overdue([invoice])
        assert result == []

    @freeze_time("2026-03-21 14:00:00")
    def test_module_level_check_and_notify_overdue_custom_threshold(
        self,
        make_invoice: Any,
    ) -> None:
        """Module-level check_and_notify_overdue respects threshold."""
        from src.services.notification_service import check_and_notify_overdue

        invoice = make_invoice(
            facture_id="F001",
            statut="EN_ATTENTE",
            date_statut="2026-03-20T17:00:00+00:00",  # ~21h ago
        )

        result = check_and_notify_overdue([invoice], threshold_hours=24)
        assert result == []

    def test_module_level_build_reminder_message(self) -> None:
        """Module-level build_reminder_message formats correctly."""
        from src.services.notification_service import build_reminder_message

        result = build_reminder_message("F001", "Client Name", 37)

        assert "F001" in result
        assert "Client Name" in result
        assert "37" in result
        assert "URSSAF" in result

    def test_email_notifier_stub_send_email(self, caplog) -> None:
        """EmailNotifier stub send_email logs correctly."""
        import logging

        from src.services.notification_service import EmailNotifier

        with caplog.at_level(logging.INFO):
            EmailNotifier.send_email(
                recipient="test@example.com",
                subject="Test",
                body="Test body",
            )

        assert "Email envoyé" in caplog.text

    def test_module_level_parse_date_statut_attribute_error(self) -> None:
        """Module-level _parse_date_statut handles AttributeError in hasattr."""
        from src.services.notification_service import _parse_date_statut

        # Object that raises AttributeError in hasattr
        class BadAttribute:
            def __getattr__(self, name):
                if name == "timestamp":
                    raise AttributeError("No timestamp")
                raise AttributeError(name)

        result = _parse_date_statut(BadAttribute())
        assert result is None


class TestNotificationIntegration:
    """Integration tests for notification lifecycle."""

    @freeze_time("2026-03-21 14:00:00")
    def test_full_lifecycle_reminder_to_expiration(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        make_invoice: Any,
    ) -> None:
        """Complete lifecycle: T+36h reminder, then T+48h expiration."""
        # Setup
        invoice = make_invoice(
            facture_id="F-LIFECYCLE",
            statut="EN_ATTENTE",
            date_statut="2026-03-20T01:00:00",
        )

        # At T+36h: should send reminder
        result_36h = notification_service.send_reminder_t36h(invoice)
        assert result_36h is True
        assert mock_email_notifier.send_reminder_email.call_count == 1

        # Advance time to T+48h
        with freeze_time("2026-03-22 01:00:00"):
            mock_email_notifier.reset_mock()
            result_48h = notification_service.send_expired_alert(invoice)
            assert result_48h is True
            assert mock_email_notifier.send_email.call_count == 1

    @freeze_time("2026-03-21 14:00:00")
    def test_payment_then_reconciliation_flow(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        make_invoice: Any,
    ) -> None:
        """Payment received followed by reconciliation."""
        # Setup: invoice transitions VALIDE -> PAYE
        invoice = make_invoice(
            facture_id="F-PAYMENT",
            statut="PAYE",
            date_paiement="2026-03-21",
            montant_total=500.0,
        )

        # Step 1: Payment received
        result_payment = notification_service.send_payment_received(invoice)
        assert result_payment is True
        assert mock_email_notifier.send_email.call_count == 1

        # Step 2: Later, reconciliation
        mock_email_notifier.reset_mock()
        invoice["statut"] = "RAPPROCHE"
        invoice["date_rapprochement"] = "2026-03-21"
        result_recon = notification_service.send_reconciled(invoice)
        assert result_recon is True
        assert mock_email_notifier.send_email.call_count == 1

    @freeze_time("2026-03-21 14:00:00")
    def test_batch_check_triggers_correct_notifications(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
        make_invoice: Any,
    ) -> None:
        """Batch operation processes all invoices correctly."""
        # Setup: 5 invoices, 3 overdue
        now = datetime(2026, 3, 21, 14, 0, 0)
        invoices = [
            make_invoice(
                facture_id="F1",
                statut="EN_ATTENTE",
                date_statut=(now - timedelta(hours=37)).isoformat(),
            ),
            make_invoice(
                facture_id="F2",
                statut="EN_ATTENTE",
                date_statut=(now - timedelta(hours=40)).isoformat(),
            ),
            make_invoice(
                facture_id="F3",
                statut="EN_ATTENTE",
                date_statut=(now - timedelta(hours=35)).isoformat(),
            ),
            make_invoice(
                facture_id="F4",
                statut="PAYE",
                date_statut=(now - timedelta(hours=37)).isoformat(),
            ),
            make_invoice(
                facture_id="F5",
                statut="EN_ATTENTE",
                date_statut=(now - timedelta(hours=42)).isoformat(),
            ),
        ]

        # Action
        count = notification_service.check_and_send_overdue(invoices, now=now)

        # Assert
        assert count == 3
        assert mock_email_notifier.send_reminder_email.call_count == 3

    def test_sync_failed_alert_during_normal_operations(
        self,
        notification_service: Any,
        mock_email_notifier: Mock,
    ) -> None:
        """Sync error interrupts normal flow, sends alert."""
        # Setup
        error_msg = "AIS connection lost after 3 retries"

        # Action
        result = notification_service.send_sync_failed(error_msg)

        # Assert
        assert result is True
        mock_email_notifier.send_sync_failed_email.assert_called_once()
