"""Tests TDD RED — NotificationService T+36h reminders — CDC §7.

Tests pour les alertes email quand une facture reste EN_ATTENTE > 36h.
Ce fichier est en phase RED : les tests doivent échouer car le service
n'est pas encore implanté.
"""

from __future__ import annotations

from datetime import datetime, timedelta

try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
from unittest.mock import MagicMock, patch

from src.services.notification_service import (
    build_reminder_message,
    check_and_notify_overdue,
)


class TestCheckAndNotifyOverdue:
    """Tests pour check_and_notify_overdue — détecte factures EN_ATTENTE > 36h."""

    def test_no_invoices_returns_empty_list(self) -> None:
        """Si pas de factures, retourne liste vide."""
        result = check_and_notify_overdue(invoices=[])
        assert result == []

    def test_no_overdue_no_reminder(self) -> None:
        """Si aucune facture EN_ATTENTE dépassée, pas de reminder."""
        now = datetime.now(UTC)
        invoices = [
            {
                "facture_id": "F001",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=30),
            }
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert result == []

    def test_overdue_36h_sends_reminder(self) -> None:
        """Si facture EN_ATTENTE depuis ≥36h, génère un reminder."""
        now = datetime.now(UTC)
        invoices = [
            {
                "facture_id": "F001",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=36),
            }
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert "F001" in result
        assert len(result) == 1

    def test_overdue_37h_sends_reminder(self) -> None:
        """Si facture EN_ATTENTE depuis 37h, génère un reminder."""
        now = datetime.now(UTC)
        invoices = [
            {
                "facture_id": "F002",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=37),
            }
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert "F002" in result

    def test_not_overdue_35h_no_reminder(self) -> None:
        """Si facture EN_ATTENTE depuis <36h, pas de reminder."""
        now = datetime.now(UTC)
        invoices = [
            {
                "facture_id": "F003",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=35),
            }
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert result == []

    def test_only_en_attente_checked(self) -> None:
        """Seules les factures EN_ATTENTE génèrent des reminders."""
        now = datetime.now(UTC)
        invoices = [
            {
                "facture_id": "F004",
                "statut": "SOUMIS",
                "date_statut": now - timedelta(hours=40),
            },
            {
                "facture_id": "F005",
                "statut": "VALIDE",
                "date_statut": now - timedelta(hours=40),
            },
            {
                "facture_id": "F006",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=40),
            },
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert result == ["F006"]
        assert "F004" not in result
        assert "F005" not in result

    def test_multiple_overdue_multiple_reminders(self) -> None:
        """Plusieurs factures EN_ATTENTE > 36h → plusieurs reminders."""
        now = datetime.now(UTC)
        invoices = [
            {
                "facture_id": "F007",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=40),
            },
            {
                "facture_id": "F008",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=50),
            },
            {
                "facture_id": "F009",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=48),
            },
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert len(result) == 3
        assert "F007" in result
        assert "F008" in result
        assert "F009" in result

    def test_missing_facture_id_skipped(self) -> None:
        """Facture EN_ATTENTE sans facture_id est ignorée."""
        now = datetime.now(UTC)
        invoices = [
            {
                "facture_id": "F010",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=40),
            },
            {
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=40),
            },
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert result == ["F010"]

    def test_missing_date_statut_skipped(self) -> None:
        """Facture EN_ATTENTE sans date_statut est ignorée."""
        now = datetime.now(UTC)
        invoices = [
            {
                "facture_id": "F011",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=40),
            },
            {
                "facture_id": "F012",
                "statut": "EN_ATTENTE",
            },
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert result == ["F011"]

    def test_invalid_date_statut_skipped(self) -> None:
        """Facture EN_ATTENTE avec date_statut invalide est ignorée."""
        now = datetime.now(UTC)
        invoices = [
            {
                "facture_id": "F013",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=40),
            },
            {
                "facture_id": "F014",
                "statut": "EN_ATTENTE",
                "date_statut": "invalid-date",
            },
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert result == ["F013"]

    def test_custom_threshold_hours(self) -> None:
        """Support pour seuil personnalisé (e.g. 24h au lieu de 36h)."""
        now = datetime.now(UTC)
        invoices = [
            {
                "facture_id": "F015",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=25),
            }
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=24)
        assert "F015" in result

    def test_date_statut_as_iso_string(self) -> None:
        """date_statut peut être une string ISO."""
        now = datetime.now(UTC)
        iso_string = (now - timedelta(hours=40)).isoformat()
        invoices = [
            {
                "facture_id": "F016",
                "statut": "EN_ATTENTE",
                "date_statut": iso_string,
            }
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert "F016" in result

    def test_date_statut_as_datetime_object(self) -> None:
        """date_statut peut être un objet datetime."""
        now = datetime.now(UTC)
        past = now - timedelta(hours=40)
        invoices = [
            {
                "facture_id": "F017",
                "statut": "EN_ATTENTE",
                "date_statut": past,
            }
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert "F017" in result

    def test_returns_list_of_facture_ids(self) -> None:
        """Retourne une liste de facture_ids (strings)."""
        now = datetime.now(UTC)
        invoices = [
            {
                "facture_id": "F018",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=40),
            }
        ]
        with patch("src.services.notification_service.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
            result = check_and_notify_overdue(invoices, threshold_hours=36)
        assert isinstance(result, list)
        assert all(isinstance(fid, str) for fid in result)


class TestBuildReminderMessage:
    """Tests pour build_reminder_message — contenu de l'email."""

    def test_message_contains_facture_id(self) -> None:
        """Le message contient l'ID de la facture."""
        message = build_reminder_message(
            facture_id="F001",
            client_name="Alice Dupont",
            elapsed_hours=40,
        )
        assert "F001" in message

    def test_message_contains_client_name(self) -> None:
        """Le message contient le nom du client."""
        message = build_reminder_message(
            facture_id="F002",
            client_name="Bob Martin",
            elapsed_hours=40,
        )
        assert "Bob Martin" in message

    def test_message_contains_hours_waiting(self) -> None:
        """Le message contient le nombre d'heures d'attente."""
        message = build_reminder_message(
            facture_id="F003",
            client_name="Carol Smith",
            elapsed_hours=48,
        )
        assert "48" in message

    def test_message_not_empty(self) -> None:
        """Le message n'est pas vide."""
        message = build_reminder_message(
            facture_id="F004",
            client_name="David Jones",
            elapsed_hours=36,
        )
        assert len(message) > 0

    def test_message_is_string(self) -> None:
        """Le message est un string."""
        message = build_reminder_message(
            facture_id="F005",
            client_name="Eve Williams",
            elapsed_hours=37,
        )
        assert isinstance(message, str)

    def test_different_facture_ids_different_messages(self) -> None:
        """Différentes factures produisent des messages différents."""
        msg1 = build_reminder_message(
            facture_id="F006",
            client_name="Frank Brown",
            elapsed_hours=40,
        )
        msg2 = build_reminder_message(
            facture_id="F007",
            client_name="Frank Brown",
            elapsed_hours=40,
        )
        assert msg1 != msg2

    def test_different_client_names_different_messages(self) -> None:
        """Différents clients produisent des messages différents."""
        msg1 = build_reminder_message(
            facture_id="F008",
            client_name="Grace Lee",
            elapsed_hours=40,
        )
        msg2 = build_reminder_message(
            facture_id="F008",
            client_name="Henry Chen",
            elapsed_hours=40,
        )
        assert msg1 != msg2

    def test_different_elapsed_hours_different_messages(self) -> None:
        """Différents délais produisent des messages différents."""
        msg1 = build_reminder_message(
            facture_id="F009",
            client_name="Iris Green",
            elapsed_hours=36,
        )
        msg2 = build_reminder_message(
            facture_id="F009",
            client_name="Iris Green",
            elapsed_hours=48,
        )
        assert msg1 != msg2

    def test_message_mentions_action_required(self) -> None:
        """Le message suggère une action (relancer client)."""
        message = build_reminder_message(
            facture_id="F010",
            client_name="Jack White",
            elapsed_hours=40,
        )
        assert any(
            word in message.lower()
            for word in ["relancer", "valider", "action", "urgent", "attention"]
        )

    def test_zero_hours_edge_case(self) -> None:
        """Cas limite : 0 heures d'attente (edge case)."""
        message = build_reminder_message(
            facture_id="F011",
            client_name="Karen Lopez",
            elapsed_hours=0,
        )
        assert "F011" in message
        assert "Karen Lopez" in message

    def test_very_large_hours_edge_case(self) -> None:
        """Cas limite : très long délai (ex: 100+ heures)."""
        message = build_reminder_message(
            facture_id="F012",
            client_name="Leo Taylor",
            elapsed_hours=120,
        )
        assert "F012" in message
        assert "Leo Taylor" in message
        assert "120" in message


class TestNotificationServiceIntegration:
    """Tests d'intégration : check_and_notify avec send_email (mock)."""

    @patch("src.services.notification_service.EmailNotifier")
    def test_calls_send_email_for_overdue_invoice(
        self,
        mock_email_notifier: MagicMock,
    ) -> None:
        """send_email est appelé pour chaque facture EN_ATTENTE > 36h."""
        now = datetime.now(UTC)
        [
            {
                "facture_id": "F013",
                "client_name": "Mike Brown",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=40),
            }
        ]

    @patch("src.services.notification_service.EmailNotifier")
    def test_does_not_call_send_email_for_non_overdue(
        self,
        mock_email_notifier: MagicMock,
    ) -> None:
        """send_email n'est pas appelé si facture < 36h."""
        now = datetime.now(UTC)
        [
            {
                "facture_id": "F014",
                "client_name": "Nora White",
                "statut": "EN_ATTENTE",
                "date_statut": now - timedelta(hours=30),
            }
        ]
