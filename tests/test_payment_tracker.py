"""Tests TDD RED — PaymentTracker sync AIS → Sheets.

PaymentTracker service:
1. Reads statuts from AIS (via AISAdapter.get_invoice_statuses())
2. Reads current data from Sheets (via SheetsAdapter.read_sheet("Factures"))
3. Detects changes (new statuts, updated statuts)
4. Validates status transitions against legal state machine
5. Detects overdue invoices (EN_ATTENTE > 36h)
6. Writes updates to Sheets (via SheetsAdapter)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import polars as pl
import pytest

from src.adapters.ais_adapter import AISAdapter
from src.adapters.sheets_adapter import SheetsAdapter

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_ais_adapter() -> MagicMock:
    """Mock AISAdapter."""
    return MagicMock(spec=AISAdapter)


@pytest.fixture
def mock_sheets_adapter() -> MagicMock:
    """Mock SheetsAdapter."""
    return MagicMock(spec=SheetsAdapter)


@pytest.fixture
def ais_status_cree() -> dict[str, Any]:
    """Status de demande AIS: CREE."""
    return {
        "facture_id": "FAC-001",
        "urssaf_demande_id": "URSSAF-123",
        "statut_ais": "CREE",
        "montant": "500.00",
        "date_maj": "2026-03-21T10:00:00Z",
    }


@pytest.fixture
def ais_status_en_attente() -> dict[str, Any]:
    """Status de demande AIS: EN_ATTENTE."""
    return {
        "facture_id": "FAC-001",
        "urssaf_demande_id": "URSSAF-123",
        "statut_ais": "EN_ATTENTE",
        "montant": "500.00",
        "date_maj": "2026-03-21T12:00:00Z",
    }


@pytest.fixture
def ais_status_valide() -> dict[str, Any]:
    """Status de demande AIS: VALIDE."""
    return {
        "facture_id": "FAC-001",
        "urssaf_demande_id": "URSSAF-123",
        "statut_ais": "VALIDE",
        "montant": "500.00",
        "date_validation": "2026-03-21T14:00:00Z",
        "date_maj": "2026-03-21T14:00:00Z",
    }


@pytest.fixture
def ais_status_paye() -> dict[str, Any]:
    """Status de demande AIS: PAYE."""
    return {
        "facture_id": "FAC-001",
        "urssaf_demande_id": "URSSAF-123",
        "statut_ais": "PAYE",
        "montant": "500.00",
        "date_validation": "2026-03-21T14:00:00Z",
        "date_paiement": "2026-03-22T09:00:00Z",
        "date_maj": "2026-03-22T09:00:00Z",
    }


@pytest.fixture
def sheets_invoice_brouillon() -> dict[str, Any]:
    """Facture Sheets: BROUILLON."""
    return {
        "facture_id": "FAC-001",
        "client_id": "CLI-001",
        "statut": "BROUILLON",
        "montant_total": "500.00",
        "date_creation": "2026-03-20",
    }


@pytest.fixture
def sheets_invoice_soumis() -> dict[str, Any]:
    """Facture Sheets: SOUMIS."""
    return {
        "facture_id": "FAC-001",
        "client_id": "CLI-001",
        "statut": "SOUMIS",
        "montant_total": "500.00",
        "date_soumission": "2026-03-21",
    }


@pytest.fixture
def sheets_invoice_cree() -> dict[str, Any]:
    """Facture Sheets: CREE."""
    return {
        "facture_id": "FAC-001",
        "client_id": "CLI-001",
        "statut": "CREE",
        "montant_total": "500.00",
        "date_soumission": "2026-03-21",
    }


@pytest.fixture
def sheets_invoice_en_attente() -> dict[str, Any]:
    """Facture Sheets: EN_ATTENTE."""
    return {
        "facture_id": "FAC-001",
        "client_id": "CLI-001",
        "statut": "EN_ATTENTE",
        "montant_total": "500.00",
        "date_soumission": "2026-03-21",
    }


@pytest.fixture
def sheets_invoice_valide() -> dict[str, Any]:
    """Facture Sheets: VALIDE."""
    return {
        "facture_id": "FAC-001",
        "client_id": "CLI-001",
        "statut": "VALIDE",
        "montant_total": "500.00",
        "date_validation": "2026-03-21T14:00:00Z",
    }


@pytest.fixture
def sheets_invoice_paye() -> dict[str, Any]:
    """Facture Sheets: PAYE."""
    return {
        "facture_id": "FAC-001",
        "client_id": "CLI-001",
        "statut": "PAYE",
        "montant_total": "500.00",
        "date_paiement": "2026-03-22T09:00:00Z",
    }


# ============================================================================
# Test Class: Sync Status Changes Detection
# ============================================================================


class TestSyncStatusesFromAIS:
    """Test detection des changements de statut AIS → Sheets."""

    def test_no_changes_returns_empty(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
        ais_status_cree: dict[str, Any],
        sheets_invoice_cree: dict[str, Any],
    ) -> None:
        """Pas de changement détecté: ancien statut = nouveau statut."""
        # Arrange
        mock_ais_adapter.get_invoice_statuses.return_value = [ais_status_cree]

        df_invoices = pl.DataFrame([sheets_invoice_cree])
        mock_sheets_adapter.get_all_invoices.return_value = df_invoices

        # Import dans la fonction (RED — elle n'existe pas encore)
        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act
        changes = tracker.sync_statuses_from_ais()

        # Assert
        assert changes == []

    def test_new_status_detected(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
        sheets_invoice_cree: dict[str, Any],
        ais_status_en_attente: dict[str, Any],
    ) -> None:
        """Changement détecté: CREE → EN_ATTENTE."""
        # Arrange
        mock_ais_adapter.get_invoice_statuses.return_value = [ais_status_en_attente]

        df_invoices = pl.DataFrame([sheets_invoice_cree])
        mock_sheets_adapter.get_all_invoices.return_value = df_invoices

        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act
        changes = tracker.sync_statuses_from_ais()

        # Assert
        assert len(changes) == 1
        assert changes[0]["facture_id"] == "FAC-001"
        assert changes[0]["ancien_statut"] == "CREE"
        assert changes[0]["nouveau_statut"] == "EN_ATTENTE"

    def test_status_change_detected(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
        sheets_invoice_en_attente: dict[str, Any],
        ais_status_valide: dict[str, Any],
    ) -> None:
        """Changement détecté: EN_ATTENTE → VALIDE."""
        # Arrange
        mock_ais_adapter.get_invoice_statuses.return_value = [ais_status_valide]

        df_invoices = pl.DataFrame([sheets_invoice_en_attente])
        mock_sheets_adapter.get_all_invoices.return_value = df_invoices

        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act
        changes = tracker.sync_statuses_from_ais()

        # Assert
        assert len(changes) == 1
        assert changes[0]["ancien_statut"] == "EN_ATTENTE"
        assert changes[0]["nouveau_statut"] == "VALIDE"

    def test_multiple_changes_detected(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Plusieurs changements détectés sur des factures différentes."""
        # Arrange
        ais_statuses = [
            {
                "facture_id": "FAC-001",
                "statut_ais": "EN_ATTENTE",
                "date_maj": "2026-03-21T12:00:00Z",
            },
            {
                "facture_id": "FAC-002",
                "statut_ais": "VALIDE",
                "date_maj": "2026-03-21T14:00:00Z",
            },
            {
                "facture_id": "FAC-003",
                "statut_ais": "PAYE",
                "date_maj": "2026-03-22T09:00:00Z",
            },
        ]

        sheets_invoices = [
            {"facture_id": "FAC-001", "statut": "CREE"},
            {"facture_id": "FAC-002", "statut": "EN_ATTENTE"},
            {"facture_id": "FAC-003", "statut": "VALIDE"},
        ]

        mock_ais_adapter.get_invoice_statuses.return_value = ais_statuses

        df_invoices = pl.DataFrame(sheets_invoices)
        mock_sheets_adapter.get_all_invoices.return_value = df_invoices

        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act
        changes = tracker.sync_statuses_from_ais()

        # Assert
        assert len(changes) == 3
        assert changes[0]["facture_id"] == "FAC-001"
        assert changes[1]["facture_id"] == "FAC-002"
        assert changes[2]["facture_id"] == "FAC-003"

    def test_unknown_facture_id_skipped(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Facture ID inconnue (pas dans Sheets) ignorée."""
        # Arrange
        ais_statuses = [
            {
                "facture_id": "FAC-999",  # N'existe pas dans Sheets
                "statut_ais": "EN_ATTENTE",
                "date_maj": "2026-03-21T12:00:00Z",
            },
            {
                "facture_id": "FAC-001",  # Existe dans Sheets
                "statut_ais": "EN_ATTENTE",
                "date_maj": "2026-03-21T12:00:00Z",
            },
        ]

        sheets_invoices = [
            {"facture_id": "FAC-001", "statut": "CREE"},
        ]

        mock_ais_adapter.get_invoice_statuses.return_value = ais_statuses

        df_invoices = pl.DataFrame(sheets_invoices)
        mock_sheets_adapter.get_all_invoices.return_value = df_invoices

        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act
        changes = tracker.sync_statuses_from_ais()

        # Assert
        # Seulement FAC-001 doit être retournée (FAC-999 skip)
        assert len(changes) == 1
        assert changes[0]["facture_id"] == "FAC-001"


# ============================================================================
# Test Class: Overdue Invoice Detection
# ============================================================================


class TestDetectOverdueInvoices:
    """Test détection des factures EN_ATTENTE > 36h (overdue)."""

    def test_no_overdue_returns_empty(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Aucune facture overdue → liste vide."""
        # Arrange
        now = datetime.now(ZoneInfo("UTC"))
        recent_time = (now - timedelta(hours=24)).isoformat()

        sheets_invoices = [
            {
                "facture_id": "FAC-001",
                "statut": "EN_ATTENTE",
                "date_soumission": recent_time,  # 24h ago, not overdue
            },
        ]

        df_invoices = pl.DataFrame(sheets_invoices)
        mock_sheets_adapter.get_all_invoices.return_value = df_invoices

        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act
        overdue = tracker.detect_overdue_invoices()

        # Assert
        assert overdue == []

    def test_overdue_36h_detected(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Facture EN_ATTENTE depuis 37h → détectée comme overdue."""
        # Arrange
        now = datetime.now(ZoneInfo("UTC"))
        old_time = (now - timedelta(hours=37)).isoformat()

        sheets_invoices = [
            {
                "facture_id": "FAC-001",
                "statut": "EN_ATTENTE",
                "date_soumission": old_time,  # 37h ago, overdue
                "montant_total": "500.00",
            },
        ]

        df_invoices = pl.DataFrame(sheets_invoices)
        mock_sheets_adapter.get_all_invoices.return_value = df_invoices

        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act
        overdue = tracker.detect_overdue_invoices()

        # Assert
        assert len(overdue) == 1
        assert overdue[0]["facture_id"] == "FAC-001"
        assert overdue[0]["statut"] == "EN_ATTENTE"

    def test_not_overdue_35h_not_detected(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Facture EN_ATTENTE depuis 35h → PAS overdue (seuil = 36h)."""
        # Arrange
        now = datetime.now(ZoneInfo("UTC"))
        not_quite_old = (now - timedelta(hours=35)).isoformat()

        sheets_invoices = [
            {
                "facture_id": "FAC-001",
                "statut": "EN_ATTENTE",
                "date_soumission": not_quite_old,  # 35h ago, not overdue
            },
        ]

        df_invoices = pl.DataFrame(sheets_invoices)
        mock_sheets_adapter.get_all_invoices.return_value = df_invoices

        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act
        overdue = tracker.detect_overdue_invoices()

        # Assert
        assert overdue == []

    def test_only_en_attente_checked(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Seul le statut EN_ATTENTE est vérifié pour overdue."""
        # Arrange
        now = datetime.now(ZoneInfo("UTC"))
        old_time = (now - timedelta(hours=40)).isoformat()

        sheets_invoices = [
            {
                "facture_id": "FAC-001",
                "statut": "CREE",  # Not EN_ATTENTE
                "date_soumission": old_time,
            },
            {
                "facture_id": "FAC-002",
                "statut": "VALIDE",  # Not EN_ATTENTE
                "date_soumission": old_time,
            },
            {
                "facture_id": "FAC-003",
                "statut": "PAYE",  # Not EN_ATTENTE
                "date_soumission": old_time,
            },
            {
                "facture_id": "FAC-004",
                "statut": "EN_ATTENTE",  # Overdue
                "date_soumission": old_time,
            },
        ]

        df_invoices = pl.DataFrame(sheets_invoices)
        mock_sheets_adapter.get_all_invoices.return_value = df_invoices

        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act
        overdue = tracker.detect_overdue_invoices()

        # Assert
        assert len(overdue) == 1
        assert overdue[0]["facture_id"] == "FAC-004"


# ============================================================================
# Test Class: Status Transition Validation
# ============================================================================


class TestStatusTransitionValidation:
    """Test validation des transitions d'état (état machine)."""

    def test_valid_transition_accepted(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Transition valide acceptée: CREE → EN_ATTENTE."""
        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act & Assert
        assert tracker.is_valid_transition("CREE", "EN_ATTENTE") is True

    def test_invalid_transition_rejected(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Transition invalide rejetée: PAYE → CREE (backward)."""
        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act & Assert
        assert tracker.is_valid_transition("PAYE", "CREE") is False

    def test_terminal_state_no_transition(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """État terminal (RAPPROCHE, ANNULE) n'a pas de transitions."""
        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act & Assert
        assert tracker.is_valid_transition("RAPPROCHE", "PAYE") is False
        assert tracker.is_valid_transition("ANNULE", "BROUILLON") is False

    def test_error_recovery_transition(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Transition de récupération d'erreur: ERREUR → BROUILLON."""
        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act & Assert
        assert tracker.is_valid_transition("ERREUR", "BROUILLON") is True

    def test_expire_recovery_transition(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Transition d'expiration: EN_ATTENTE → EXPIRE → BROUILLON."""
        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act & Assert
        assert tracker.is_valid_transition("EN_ATTENTE", "EXPIRE") is True
        assert tracker.is_valid_transition("EXPIRE", "BROUILLON") is True

    def test_rejection_recovery_transition(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Transition de rejet: EN_ATTENTE → REJETE → BROUILLON."""
        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act & Assert
        assert tracker.is_valid_transition("EN_ATTENTE", "REJETE") is True
        assert tracker.is_valid_transition("REJETE", "BROUILLON") is True


# ============================================================================
# Test Class: Write to Sheets (Integration)
# ============================================================================


class TestWriteChangesToSheets:
    """Test écriture des changements dans Google Sheets."""

    def test_write_status_change_to_sheets(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Changement de statut écrit dans Sheets."""
        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Arrange
        change = {
            "facture_id": "FAC-001",
            "ancien_statut": "CREE",
            "nouveau_statut": "EN_ATTENTE",
        }

        # Act
        tracker.write_status_change_to_sheets(change)

        # Assert
        mock_sheets_adapter.update_invoice.assert_called_once()

    def test_write_multiple_changes_to_sheets(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Plusieurs changements écrits en batch."""
        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Arrange
        mock_sheets_adapter.update_invoices_batch.return_value = 2
        changes = [
            {"facture_id": "FAC-001", "ancien_statut": "CREE", "nouveau_statut": "EN_ATTENTE"},
            {"facture_id": "FAC-002", "ancien_statut": "EN_ATTENTE", "nouveau_statut": "VALIDE"},
        ]

        # Act
        tracker.write_status_changes_batch(changes)

        # Assert
        mock_sheets_adapter.update_invoices_batch.assert_called_once()
        called_updates = mock_sheets_adapter.update_invoices_batch.call_args[0][0]
        assert len(called_updates) == 2
        assert called_updates[0]["facture_id"] == "FAC-001"
        assert called_updates[0]["statut"] == "EN_ATTENTE"
        assert called_updates[1]["facture_id"] == "FAC-002"
        assert called_updates[1]["statut"] == "VALIDE"

    def test_write_empty_batch_is_noop(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Batch vide ne fait aucun appel Sheets."""
        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act
        tracker.write_status_changes_batch([])

        # Assert
        mock_sheets_adapter.update_invoices_batch.assert_not_called()

    def test_write_invalid_change_skipped(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Changement sans facture_id ou statut est ignoré."""
        from src.services.payment_tracker import PaymentTracker

        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        # Act
        change = {"facture_id": "", "nouveau_statut": "EN_ATTENTE"}
        tracker.write_status_change_to_sheets(change)

        # Assert
        mock_sheets_adapter.update_invoice.assert_not_called()


# ============================================================================
# Test Class: Standalone sync_statuses_from_ais function
# ============================================================================


class TestStandaloneSyncStatuses:
    """Test de la fonction standalone sync_statuses_from_ais()."""

    def test_detects_status_change(self) -> None:
        """Détecte un changement CREE → EN_ATTENTE."""
        from src.services.payment_tracker import sync_statuses_from_ais

        ais = [{"facture_id": "F001", "statut_ais": "EN_ATTENTE", "urssaf_demande_id": "U1"}]
        sheets = [{"facture_id": "F001", "statut": "CREE"}]

        # Act
        changes = sync_statuses_from_ais(ais, sheets)

        # Assert
        assert len(changes) == 1
        assert changes[0]["facture_id"] == "F001"
        assert changes[0]["ancien_statut"] == "CREE"
        assert changes[0]["nouveau_statut"] == "EN_ATTENTE"

    def test_empty_ais_returns_empty(self) -> None:
        """Pas de statuts AIS → pas de changements."""
        from src.services.payment_tracker import sync_statuses_from_ais

        changes = sync_statuses_from_ais([], [{"facture_id": "F001", "statut": "CREE"}])

        assert changes == []

    def test_empty_sheets_returns_empty(self) -> None:
        """Pas de factures Sheets → pas de changements."""
        from src.services.payment_tracker import sync_statuses_from_ais

        changes = sync_statuses_from_ais([{"facture_id": "F001", "statut_ais": "EN_ATTENTE"}], [])

        assert changes == []

    def test_no_change_same_status(self) -> None:
        """Même statut AIS et Sheets → pas de changement."""
        from src.services.payment_tracker import sync_statuses_from_ais

        ais = [{"facture_id": "F001", "statut_ais": "CREE"}]
        sheets = [{"facture_id": "F001", "statut": "CREE"}]

        changes = sync_statuses_from_ais(ais, sheets)

        assert changes == []

    def test_unknown_facture_returns_na(self) -> None:
        """Facture AIS inconnue dans Sheets → ancien_statut = N/A."""
        from src.services.payment_tracker import sync_statuses_from_ais

        ais = [{"facture_id": "F999", "statut_ais": "CREE", "urssaf_demande_id": "U1"}]
        sheets = [{"facture_id": "F001", "statut": "CREE"}]

        changes = sync_statuses_from_ais(ais, sheets)

        assert len(changes) == 1
        assert changes[0]["ancien_statut"] == "N/A"

    def test_skips_empty_facture_id(self) -> None:
        """Skip les entrées AIS sans facture_id."""
        from src.services.payment_tracker import sync_statuses_from_ais

        ais = [{"facture_id": "", "statut_ais": "CREE"}]
        sheets = [{"facture_id": "F001", "statut": "CREE"}]

        changes = sync_statuses_from_ais(ais, sheets)

        assert changes == []

    def test_skips_empty_status(self) -> None:
        """Skip les entrées AIS sans statut_ais."""
        from src.services.payment_tracker import sync_statuses_from_ais

        ais = [{"facture_id": "F001", "statut_ais": ""}]
        sheets = [{"facture_id": "F001", "statut": "CREE"}]

        changes = sync_statuses_from_ais(ais, sheets)

        assert changes == []


# ============================================================================
# Test Class: Standalone check_status_transition function
# ============================================================================


class TestStandaloneCheckStatusTransition:
    """Test de la fonction standalone check_status_transition()."""

    def test_valid_forward_transition(self) -> None:
        """Transition valide BROUILLON → SOUMIS."""
        from src.services.payment_tracker import check_status_transition

        assert check_status_transition("BROUILLON", "SOUMIS") is True

    def test_invalid_backward_transition(self) -> None:
        """Transition invalide PAYE → CREE."""
        from src.services.payment_tracker import check_status_transition

        assert check_status_transition("PAYE", "CREE") is False

    def test_terminal_state_blocks_all(self) -> None:
        """État terminal RAPPROCHE bloque toute transition."""
        from src.services.payment_tracker import check_status_transition

        assert check_status_transition("RAPPROCHE", "BROUILLON") is False
        assert check_status_transition("ANNULE", "BROUILLON") is False

    def test_unknown_state_returns_false(self) -> None:
        """État inconnu retourne False."""
        from src.services.payment_tracker import check_status_transition

        assert check_status_transition("INCONNU", "BROUILLON") is False

    def test_all_valid_transitions(self) -> None:
        """Toutes les transitions valides du SCHEMAS.html."""
        from src.services.payment_tracker import check_status_transition

        valid_pairs = [
            ("BROUILLON", "SOUMIS"),
            ("BROUILLON", "ANNULE"),
            ("SOUMIS", "CREE"),
            ("SOUMIS", "ERREUR"),
            ("CREE", "EN_ATTENTE"),
            ("EN_ATTENTE", "VALIDE"),
            ("EN_ATTENTE", "EXPIRE"),
            ("EN_ATTENTE", "REJETE"),
            ("VALIDE", "PAYE"),
            ("PAYE", "RAPPROCHE"),
            ("ERREUR", "BROUILLON"),
            ("EXPIRE", "BROUILLON"),
            ("REJETE", "BROUILLON"),
        ]

        for old, new in valid_pairs:
            assert check_status_transition(old, new) is True, f"{old} → {new} should be valid"


# ============================================================================
# Test Class: Standalone filter_critical_statuses function
# ============================================================================


class TestStandaloneFilterCriticalStatuses:
    """Test de la fonction standalone filter_critical_statuses()."""

    def test_filters_critical_statuses(self) -> None:
        """Filtre ERREUR, EXPIRE, REJETE, EN_ATTENTE."""
        from src.services.payment_tracker import filter_critical_statuses

        changes = [
            {"facture_id": "F001", "nouveau_statut": "ERREUR"},
            {"facture_id": "F002", "nouveau_statut": "PAYE"},
            {"facture_id": "F003", "nouveau_statut": "EXPIRE"},
            {"facture_id": "F004", "nouveau_statut": "VALIDE"},
            {"facture_id": "F005", "nouveau_statut": "REJETE"},
            {"facture_id": "F006", "nouveau_statut": "EN_ATTENTE"},
        ]

        # Act
        critical = filter_critical_statuses(changes)

        # Assert
        assert len(critical) == 4
        critical_ids = {c["facture_id"] for c in critical}
        assert critical_ids == {"F001", "F003", "F005", "F006"}

    def test_empty_changes_returns_empty(self) -> None:
        """Liste vide → résultat vide."""
        from src.services.payment_tracker import filter_critical_statuses

        assert filter_critical_statuses([]) == []

    def test_no_critical_returns_empty(self) -> None:
        """Que des statuts non-critiques → résultat vide."""
        from src.services.payment_tracker import filter_critical_statuses

        changes = [
            {"facture_id": "F001", "nouveau_statut": "PAYE"},
            {"facture_id": "F002", "nouveau_statut": "VALIDE"},
        ]

        assert filter_critical_statuses(changes) == []


# ============================================================================
# Test Class: PaymentTracker edge cases
# ============================================================================


class TestPaymentTrackerEdgeCases:
    """Tests des cas limites du PaymentTracker."""

    def test_sync_empty_ais_returns_empty(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """AIS retourne liste vide → pas de changements."""
        from src.services.payment_tracker import PaymentTracker

        mock_ais_adapter.get_invoice_statuses.return_value = []
        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        changes = tracker.sync_statuses_from_ais()

        assert changes == []

    def test_sync_skips_empty_facture_id(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Entrée AIS sans facture_id est ignorée."""
        from src.services.payment_tracker import PaymentTracker

        mock_ais_adapter.get_invoice_statuses.return_value = [
            {"facture_id": "", "statut_ais": "CREE"}
        ]
        mock_sheets_adapter.get_all_invoices.return_value = pl.DataFrame(
            [{"facture_id": "F001", "statut": "CREE"}]
        )
        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        changes = tracker.sync_statuses_from_ais()

        assert changes == []

    def test_sync_skips_empty_status(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Entrée AIS sans statut_ais est ignorée."""
        from src.services.payment_tracker import PaymentTracker

        mock_ais_adapter.get_invoice_statuses.return_value = [
            {"facture_id": "F001", "statut_ais": ""}
        ]
        mock_sheets_adapter.get_all_invoices.return_value = pl.DataFrame(
            [{"facture_id": "F001", "statut": "CREE"}]
        )
        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        changes = tracker.sync_statuses_from_ais()

        assert changes == []

    def test_detect_overdue_empty_df(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """DataFrame vide → pas d'overdue."""
        from src.services.payment_tracker import PaymentTracker

        mock_sheets_adapter.get_all_invoices.return_value = pl.DataFrame()
        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        overdue = tracker.detect_overdue_invoices()

        assert overdue == []

    def test_detect_overdue_no_date_skipped(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Facture EN_ATTENTE sans date_soumission est ignorée."""
        from src.services.payment_tracker import PaymentTracker

        mock_sheets_adapter.get_all_invoices.return_value = pl.DataFrame(
            [{"facture_id": "F001", "statut": "EN_ATTENTE", "date_soumission": ""}]
        )
        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        overdue = tracker.detect_overdue_invoices()

        assert overdue == []

    def test_detect_overdue_invalid_date_skipped(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Date invalide est ignorée sans crash."""
        from src.services.payment_tracker import PaymentTracker

        mock_sheets_adapter.get_all_invoices.return_value = pl.DataFrame(
            [{"facture_id": "F001", "statut": "EN_ATTENTE", "date_soumission": "not-a-date"}]
        )
        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        overdue = tracker.detect_overdue_invoices()

        assert overdue == []

    def test_detect_overdue_date_without_iso_separator_skipped(
        self,
        mock_ais_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Date sans 'T' (format date only) est ignorée."""
        from src.services.payment_tracker import PaymentTracker

        mock_sheets_adapter.get_all_invoices.return_value = pl.DataFrame(
            [{"facture_id": "F001", "statut": "EN_ATTENTE", "date_soumission": "2026-03-20"}]
        )
        tracker = PaymentTracker(ais_adapter=mock_ais_adapter, sheets_adapter=mock_sheets_adapter)

        overdue = tracker.detect_overdue_invoices()

        assert overdue == []
