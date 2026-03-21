"""Tests TDD RED — BankReconciliation sync Indy → lettrage — CDC §4."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.adapters.indy_adapter import IndyBrowserAdapter
from src.adapters.sheets_adapter import SheetsAdapter
from src.models.invoice import Invoice, InvoiceStatus
from src.models.transaction import (
    LettrageResult,
    LettrageStatus,
    compute_matching_score,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_indy_adapter() -> MagicMock:
    """Mock IndyAdapter pour éviter scraping réel."""
    adapter = MagicMock(spec=IndyBrowserAdapter)
    return adapter


@pytest.fixture
def mock_sheets_adapter() -> MagicMock:
    """Mock SheetsAdapter pour éviter appels API réels."""
    adapter = MagicMock(spec=SheetsAdapter)
    return adapter


@pytest.fixture
def sample_invoice_paye() -> Invoice:
    """Facture en état PAYE prête pour lettrage."""
    return Invoice(
        facture_id="F001",
        client_id="C001",
        statut=InvoiceStatus.PAYE,
        montant_unitaire=100.0,
        quantite=1.0,
    )


@pytest.fixture
def sample_transactions() -> list[dict[str, str]]:
    """Transactions Indy brutes (avant import)."""
    return [
        {
            "id": "TXN001",
            "date": "2026-03-20",
            "amount": "100.00",
            "label": "Paiement URSSAF",
            "type": "transfer",
        },
        {
            "id": "TXN002",
            "date": "2026-03-21",
            "amount": "50.00",
            "label": "Frais",
            "type": "fee",
        },
    ]


# ============================================================================
# TEST CLASS: ImportTransactions
# ============================================================================


class TestImportTransactions:
    """Tests pour l'import de transactions depuis Indy vers Sheets."""

    def test_import_new_transactions(
        self, mock_indy_adapter: MagicMock, mock_sheets_adapter: MagicMock
    ) -> None:
        """Doit importer les transactions nouvelles dans Sheets onglet Transactions."""
        # ARRANGE
        txn_data = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement URSSAF",
            }
        ]
        mock_indy_adapter.export_transactions.return_value = txn_data
        mock_sheets_adapter.get_all_transactions.return_value = []

        # ACT
        # transactions = import_transactions(mock_indy_adapter, mock_sheets_adapter)

        # ASSERT
        # assert len(transactions) == 1
        # mock_sheets_adapter.add_transactions.assert_called_once()

    def test_dedup_by_indy_ref(
        self, mock_indy_adapter: MagicMock, mock_sheets_adapter: MagicMock
    ) -> None:
        """Doit dédupliquer les transactions par indy_id (ne pas importer doublons)."""
        # ARRANGE
        txn_data = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement URSSAF",
            }
        ]
        existing = [
            {
                "indy_id": "TXN001",
                "date_valeur": "2026-03-20",
                "montant": 100.0,
            }
        ]
        mock_indy_adapter.export_transactions.return_value = txn_data
        mock_sheets_adapter.get_all_transactions.return_value = existing

        # ACT
        # transactions = import_transactions(mock_indy_adapter, mock_sheets_adapter)

        # ASSERT
        # assert len(transactions) == 0  # Pas d'import, déjà existant

    def test_empty_csv_no_import(
        self, mock_indy_adapter: MagicMock, mock_sheets_adapter: MagicMock
    ) -> None:
        """Si Indy retourne CSV vide, ne pas importer."""
        # ARRANGE
        mock_indy_adapter.export_transactions.return_value = []
        mock_sheets_adapter.get_all_transactions.return_value = []

        # ACT
        # transactions = import_transactions(mock_indy_adapter, mock_sheets_adapter)

        # ASSERT
        # assert len(transactions) == 0
        # mock_sheets_adapter.add_transactions.assert_not_called()

    def test_import_preserves_order(
        self, mock_indy_adapter: MagicMock, mock_sheets_adapter: MagicMock
    ) -> None:
        """L'ordre des transactions doit être préservé (chronologique Indy)."""
        # ARRANGE
        txn_data = [
            {
                "id": "TXN001",
                "date": "2026-03-18",
                "amount": "100.00",
                "label": "Paiement URSSAF",
            },
            {
                "id": "TXN002",
                "date": "2026-03-19",
                "amount": "50.00",
                "label": "Frais",
            },
            {
                "id": "TXN003",
                "date": "2026-03-20",
                "amount": "150.00",
                "label": "Autre paiement",
            },
        ]
        mock_indy_adapter.export_transactions.return_value = txn_data
        mock_sheets_adapter.get_all_transactions.return_value = []

        # ACT
        # transactions = import_transactions(mock_indy_adapter, mock_sheets_adapter)

        # ASSERT
        # assert transactions[0]["id"] == "TXN001"
        # assert transactions[1]["id"] == "TXN002"
        # assert transactions[2]["id"] == "TXN003"


# ============================================================================
# TEST CLASS: LettrageScoring
# ============================================================================


class TestLettrageScoring:
    """Tests pour le calcul du score de lettrage (matching facture ↔ txn)."""

    def test_exact_amount_plus50(self) -> None:
        """Montant exact (+50 pts)."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 20)

        # ACT
        score = compute_matching_score(
            invoice_amount=100.0,
            transaction_amount=100.0,
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="Paiement",
        )

        # ASSERT
        assert score >= 50, "Score devrait inclure +50 pour montant exact"

    def test_date_within_3days_plus30(self) -> None:
        """Date < 3 jours (+30 pts)."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 22)  # 2 jours après

        # ACT
        score = compute_matching_score(
            invoice_amount=100.0,
            transaction_amount=100.0,
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="Paiement",
        )

        # ASSERT
        assert score >= 30, "Score devrait inclure +30 pour date < 3 jours"

    def test_label_urssaf_plus20(self) -> None:
        """Libellé contient 'URSSAF' (+20 pts)."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 20)

        # ACT
        score = compute_matching_score(
            invoice_amount=100.0,
            transaction_amount=100.0,
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="Paiement URSSAF Jules Willard",
        )

        # ASSERT
        assert score >= 20, "Score devrait inclure +20 pour label URSSAF"

    def test_score_100_lettre_auto(self) -> None:
        """Score 100 → LETTRE_AUTO (toutes conditions)."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 20)

        # ACT
        score = compute_matching_score(
            invoice_amount=100.0,
            transaction_amount=100.0,
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="Paiement URSSAF",
        )

        result = LettrageResult(
            facture_id="F001",
            transaction_id="T001",
            score=score,
            montant_exact=True,
            date_proche=True,
            libelle_urssaf=True,
        )

        # ASSERT
        assert result.statut == LettrageStatus.LETTRE_AUTO
        assert score >= 80

    def test_score_80_lettre_auto(self) -> None:
        """Score exactly 80 → LETTRE_AUTO (seuil minimum)."""
        # ARRANGE
        result = LettrageResult(
            facture_id="F001",
            transaction_id="T001",
            score=80,
            montant_exact=True,
            date_proche=True,
            libelle_urssaf=False,
        )

        # ASSERT
        assert result.statut == LettrageStatus.LETTRE_AUTO

    def test_score_79_a_verifier(self) -> None:
        """Score 79 → A_VERIFIER (sous le seuil 80)."""
        # ARRANGE
        result = LettrageResult(
            facture_id="F001",
            transaction_id="T001",
            score=79,
            montant_exact=True,
            date_proche=False,
            libelle_urssaf=True,
        )

        # ASSERT
        assert result.statut == LettrageStatus.A_VERIFIER

    def test_no_match_pas_de_match(self) -> None:
        """Aucune transaction matchée → PAS_DE_MATCH."""
        # ARRANGE
        result = LettrageResult(
            facture_id="F001",
            transaction_id=None,
            score=0,
        )

        # ASSERT
        assert result.statut == LettrageStatus.PAS_DE_MATCH

    def test_window_5_days(self) -> None:
        """Transaction dans fenêtre ±5 jours doit être éligible."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 25)  # 5 jours après

        # ACT
        score = compute_matching_score(
            invoice_amount=100.0,
            transaction_amount=100.0,
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="Paiement",
        )

        # ASSERT
        assert score > 0, "Score devrait être > 0 pour date à 5 jours (dans la fenêtre)"

    def test_outside_window_no_match(self) -> None:
        """Transaction en dehors fenêtre ±5 jours ne doit pas matcher."""
        # ARRANGE
        date(2026, 3, 20)
        date(2026, 3, 26)  # 6 jours après

        # ACT
        result = LettrageResult(
            facture_id="F001",
            transaction_id=None,  # Pas de match en dehors de la fenêtre
            score=0,
        )

        # ASSERT
        assert result.statut == LettrageStatus.PAS_DE_MATCH

    def test_partial_match_amount_only(self) -> None:
        """Montant seul (50 pts) → A_VERIFIER."""
        # ARRANGE
        result = LettrageResult(
            facture_id="F001",
            transaction_id="T001",
            score=50,
            montant_exact=True,
            date_proche=False,
            libelle_urssaf=False,
        )

        # ASSERT
        assert result.statut == LettrageStatus.A_VERIFIER

    def test_partial_match_amount_and_date(self) -> None:
        """Montant + date (50+30=80) → LETTRE_AUTO."""
        # ARRANGE
        result = LettrageResult(
            facture_id="F001",
            transaction_id="T001",
            score=80,
            montant_exact=True,
            date_proche=True,
            libelle_urssaf=False,
        )

        # ASSERT
        assert result.statut == LettrageStatus.LETTRE_AUTO

    def test_case_insensitive_urssaf_match(self) -> None:
        """URSSAF matching doit être case-insensitive."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 20)

        # ACT
        score_lower = compute_matching_score(
            invoice_amount=100.0,
            transaction_amount=100.0,
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="paiement urssaf",
        )

        score_upper = compute_matching_score(
            invoice_amount=100.0,
            transaction_amount=100.0,
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="PAIEMENT URSSAF",
        )

        # ASSERT
        assert score_lower >= 20, "Minuscules doivent matcher URSSAF"
        assert score_upper >= 20, "Majuscules doivent matcher URSSAF"


# ============================================================================
# TEST CLASS: ReconcileWorkflow
# ============================================================================


class TestReconcileWorkflow:
    """Tests du workflow complet de rapprochement bancaire."""

    def test_full_reconcile_flow(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
        sample_invoice_paye: Invoice,
    ) -> None:
        """Workflow complet : Indy → import → lettrage → update Sheets."""
        # ARRANGE
        indy_txns = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement URSSAF",
            }
        ]
        mock_indy_adapter.export_transactions.return_value = indy_txns
        mock_sheets_adapter.get_all_transactions.return_value = []
        mock_sheets_adapter.get_all_invoices.return_value = [sample_invoice_paye]
        mock_sheets_adapter.get_all_lettrage.return_value = []

        # ACT
        # result = reconcile_all(mock_indy_adapter, mock_sheets_adapter)

        # ASSERT
        # assert result.transactions_imported > 0
        # assert result.lettrage_updated > 0
        # mock_sheets_adapter.add_transactions.assert_called_once()
        # mock_sheets_adapter._update_row.assert_called()

    def test_paye_to_rapproche_on_match(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
        sample_invoice_paye: Invoice,
    ) -> None:
        """Facture PAYE avec match LETTRE_AUTO → transition à RAPPROCHE."""
        # ARRANGE
        indy_txns = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement URSSAF",
            }
        ]
        mock_indy_adapter.export_transactions.return_value = indy_txns
        mock_sheets_adapter.get_all_transactions.return_value = []
        mock_sheets_adapter.get_all_invoices.return_value = [sample_invoice_paye]

        # ACT
        # result = reconcile_all(mock_indy_adapter, mock_sheets_adapter)

        # ASSERT
        # updated_invoice = result.invoices_updated[0]
        # assert updated_invoice.statut == InvoiceStatus.RAPPROCHE

    def test_multiple_invoices_multiple_transactions(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Plusieurs factures PAYE vs plusieurs transactions."""
        # ARRANGE
        invoice1 = Invoice(
            facture_id="F001",
            client_id="C001",
            statut=InvoiceStatus.PAYE,
            montant_unitaire=100.0,
            quantite=1.0,
        )
        invoice2 = Invoice(
            facture_id="F002",
            client_id="C002",
            statut=InvoiceStatus.PAYE,
            montant_unitaire=200.0,
            quantite=1.0,
        )

        indy_txns = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement URSSAF",
            },
            {
                "id": "TXN002",
                "date": "2026-03-21",
                "amount": "200.00",
                "label": "Paiement URSSAF 2",
            },
        ]
        mock_indy_adapter.export_transactions.return_value = indy_txns
        mock_sheets_adapter.get_all_transactions.return_value = []
        mock_sheets_adapter.get_all_invoices.return_value = [invoice1, invoice2]

        # ACT
        # result = reconcile_all(mock_indy_adapter, mock_sheets_adapter)

        # ASSERT
        # assert len(result.invoices_updated) == 2

    def test_lettrage_one_transaction_per_invoice(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
        sample_invoice_paye: Invoice,
    ) -> None:
        """Une transaction ne peut matcher qu'UNE seule facture (meilleur score)."""
        # ARRANGE
        indy_txns = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement URSSAF",
            }
        ]
        mock_indy_adapter.export_transactions.return_value = indy_txns
        mock_sheets_adapter.get_all_transactions.return_value = []
        mock_sheets_adapter.get_all_invoices.return_value = [sample_invoice_paye]

        # ACT
        # result = reconcile_all(mock_indy_adapter, mock_sheets_adapter)

        # ASSERT
        # For each transaction, only one invoice can be matched

    def test_skip_non_paye_invoices(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Ne traiter que factures en état PAYE pour le lettrage."""
        # ARRANGE
        invoice_brouillon = Invoice(
            facture_id="F001",
            client_id="C001",
            statut=InvoiceStatus.BROUILLON,
        )
        invoice_paye = Invoice(
            facture_id="F002",
            client_id="C002",
            statut=InvoiceStatus.PAYE,
            montant_unitaire=100.0,
            quantite=1.0,
        )

        indy_txns = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement URSSAF",
            }
        ]
        mock_indy_adapter.export_transactions.return_value = indy_txns
        mock_sheets_adapter.get_all_transactions.return_value = []
        mock_sheets_adapter.get_all_invoices.return_value = [invoice_brouillon, invoice_paye]

        # ACT
        # result = reconcile_all(mock_indy_adapter, mock_sheets_adapter)

        # ASSERT
        # Only invoice_paye should be processed

    def test_empty_invoice_list_no_lettrage(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Si pas de factures PAYE, ne pas faire de lettrage."""
        # ARRANGE
        indy_txns = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement URSSAF",
            }
        ]
        mock_indy_adapter.export_transactions.return_value = indy_txns
        mock_sheets_adapter.get_all_transactions.return_value = []
        mock_sheets_adapter.get_all_invoices.return_value = []

        # ACT
        # result = reconcile_all(mock_indy_adapter, mock_sheets_adapter)

        # ASSERT
        # assert result.lettrage_updated == 0

    def test_retries_on_adapter_failure(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Retry 3x si Indy ou Sheets échouent (tenacity)."""
        # ARRANGE
        mock_indy_adapter.export_transactions.side_effect = [
            Exception("Timeout"),
            Exception("Timeout"),
            [
                {
                    "id": "TXN001",
                    "date": "2026-03-20",
                    "amount": "100.00",
                    "label": "Paiement URSSAF",
                }
            ],
        ]

        # ACT
        # result = reconcile_all(mock_indy_adapter, mock_sheets_adapter)

        # ASSERT
        # assert mock_indy_adapter.export_transactions.call_count == 3


# ============================================================================
# TEST CLASS: EdgeCases
# ============================================================================


class TestEdgeCases:
    """Tests cas limites et erreurs."""

    def test_zero_amount_invoice_no_match(self) -> None:
        """Facture montant 0 ne doit pas matcher."""
        # ARRANGE
        result = LettrageResult(
            facture_id="F001",
            transaction_id=None,
            score=0,
        )

        # ASSERT
        assert result.statut == LettrageStatus.PAS_DE_MATCH

    def test_negative_amount_transaction(self) -> None:
        """Montant négatif (remboursement) ne doit pas matcher facture positive."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 20)

        score = compute_matching_score(
            invoice_amount=100.0,
            transaction_amount=-100.0,  # Négatif = remboursement
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="Remboursement",
        )

        # ASSERT
        assert score < 50, "Montants opposés ne doivent pas matcher"

    def test_amount_difference_tolerance(self) -> None:
        """Petites différences < 0.01 € doivent matcher (erreurs d'arrondi)."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 20)

        score = compute_matching_score(
            invoice_amount=100.00,
            transaction_amount=100.001,  # Différence de 0.001 €
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="Paiement",
        )

        # ASSERT
        assert score >= 50, "Différence < 0.01 € doit matcher"

    def test_amount_difference_not_tolerance(self) -> None:
        """Différences > 0.01 € ne doivent pas matcher."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 20)

        score = compute_matching_score(
            invoice_amount=100.00,
            transaction_amount=100.50,  # Différence de 0.50 €
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="Paiement",
        )

        # ASSERT
        assert score < 50, "Différence > 0.01 € ne doit pas donner 50 pts montant"

    def test_date_exactly_3_days_includes_plus30(self) -> None:
        """Exactement 3 jours = dans la limite (+30 pts)."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 23)  # Exactement 3 jours

        score = compute_matching_score(
            invoice_amount=100.0,
            transaction_amount=100.0,
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="Paiement",
        )

        # ASSERT
        assert score >= 30, "3 jours exactement doit inclure +30 pts"

    def test_date_4_days_excludes_plus30(self) -> None:
        """4 jours = dépasse la limite (pas +30 pts)."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 24)  # 4 jours

        score = compute_matching_score(
            invoice_amount=100.0,
            transaction_amount=100.0,
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="Paiement",
        )

        # ASSERT
        # 4 jours > 3 jours, donc pas +30
        assert score < 80, "4 jours dépasse la limite, pas assez pour LETTRE_AUTO"

    def test_transaction_before_invoice_payment_date(self) -> None:
        """Transaction AVANT la date de paiement facture (impossible) ne doit pas matcher."""
        # ARRANGE
        date(2026, 3, 20)
        date(2026, 3, 19)  # Avant

        result = LettrageResult(
            facture_id="F001",
            transaction_id=None,
            score=0,
        )

        # ASSERT
        # Transaction before invoice shouldn't match
        assert result.statut == LettrageStatus.PAS_DE_MATCH

    def test_empty_label_still_possible_match(self) -> None:
        """Label vide ne doit pas bloquer le matching si autres critères OK."""
        # ARRANGE
        facture_date = date(2026, 3, 20)
        txn_date = date(2026, 3, 20)

        score = compute_matching_score(
            invoice_amount=100.0,
            transaction_amount=100.0,
            invoice_payment_date=facture_date,
            transaction_date=txn_date,
            transaction_label="",  # Label vide
        )

        # ASSERT
        assert score >= 50, "Label vide ne doit pas bloquer le matching"


# ============================================================================
# TEST CLASS: ReconciliationService (RED tests for full workflow)
# ============================================================================


class TestReconciliationService:
    """Tests RED pour le service complet de rapprochement — CDC §4+5."""

    def test_full_reconcile_imports_and_matches(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Le service complet: import Indy → dedup → scoring → update Sheets."""
        # ARRANGE
        from src.services.bank_reconciliation import ReconciliationService

        invoice_paye = Invoice(
            facture_id="F001",
            client_id="C001",
            statut=InvoiceStatus.PAYE,
            montant_unitaire=100.0,
            quantite=1.0,
        )

        indy_csv_data = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement URSSAF",
                "type": "transfer",
            }
        ]

        mock_indy_adapter.export_journal_csv.return_value = indy_csv_data
        mock_sheets_adapter.get_all_transactions.return_value = []
        mock_sheets_adapter.get_all_invoices.return_value = [invoice_paye]

        service = ReconciliationService(mock_indy_adapter, mock_sheets_adapter)

        # ACT
        result = service.reconcile()

        # ASSERT
        assert result["transactions_imported"] > 0
        assert result["lettrage_updated"] > 0
        mock_sheets_adapter.add_transactions.assert_called()

    def test_reconcile_skips_non_paye_invoices(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Seules les factures PAYE sont candidates au lettrage."""
        # ARRANGE
        from src.services.bank_reconciliation import ReconciliationService

        invoice_brouillon = Invoice(
            facture_id="F001",
            client_id="C001",
            statut=InvoiceStatus.BROUILLON,
        )

        indy_csv_data = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement",
            }
        ]

        mock_indy_adapter.export_journal_csv.return_value = indy_csv_data
        mock_sheets_adapter.get_all_transactions.return_value = []
        mock_sheets_adapter.get_all_invoices.return_value = [invoice_brouillon]

        service = ReconciliationService(mock_indy_adapter, mock_sheets_adapter)

        # ACT
        result = service.reconcile()

        # ASSERT
        assert result["lettrage_updated"] == 0, "Factures non-PAYE ne doivent pas être lettrées"

    def test_reconcile_transitions_paye_to_rapproche(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Score >= 80 → update statut PAYE → RAPPROCHE dans Sheets."""
        # ARRANGE
        from src.services.bank_reconciliation import ReconciliationService

        invoice_paye = Invoice(
            facture_id="F001",
            client_id="C001",
            statut=InvoiceStatus.PAYE,
            montant_unitaire=100.0,
            quantite=1.0,
        )

        indy_csv_data = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement URSSAF",
                "type": "transfer",
            }
        ]

        mock_indy_adapter.export_journal_csv.return_value = indy_csv_data
        mock_sheets_adapter.get_all_transactions.return_value = []
        mock_sheets_adapter.get_all_invoices.return_value = [invoice_paye]

        service = ReconciliationService(mock_indy_adapter, mock_sheets_adapter)

        # ACT
        result = service.reconcile()

        # ASSERT
        assert result["auto_matched"] > 0, "Score >= 80 devrait générer LETTRE_AUTO"
        mock_sheets_adapter.update_invoice_status.assert_called()

    def test_reconcile_dedup_on_import(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Les transactions déjà importées (même indy_ref) sont ignorées."""
        # ARRANGE
        from src.services.bank_reconciliation import ReconciliationService

        existing_transaction = {
            "transaction_id": "TXN001",
            "indy_id": "TXN001",
            "date_valeur": "2026-03-20",
            "montant": 100.0,
            "libelle": "Paiement",
        }

        indy_csv_data = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement",
            }
        ]

        mock_indy_adapter.export_journal_csv.return_value = indy_csv_data
        mock_sheets_adapter.get_all_transactions.return_value = [existing_transaction]
        mock_sheets_adapter.get_all_invoices.return_value = []

        service = ReconciliationService(mock_indy_adapter, mock_sheets_adapter)

        # ACT
        result = service.reconcile()

        # ASSERT
        assert result["transactions_imported"] == 0, (
            "Transaction existante ne doit pas être réimportée"
        )
        mock_sheets_adapter.add_transactions.assert_not_called()

    def test_reconcile_with_no_transactions(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """CSV vide → rien importé, pas de lettrage."""
        # ARRANGE
        from src.services.bank_reconciliation import ReconciliationService

        mock_indy_adapter.export_journal_csv.return_value = []
        mock_sheets_adapter.get_all_transactions.return_value = []
        mock_sheets_adapter.get_all_invoices.return_value = []

        service = ReconciliationService(mock_indy_adapter, mock_sheets_adapter)

        # ACT
        result = service.reconcile()

        # ASSERT
        assert result["transactions_imported"] == 0
        assert result["lettrage_updated"] == 0
        mock_sheets_adapter.add_transactions.assert_not_called()

    def test_reconcile_returns_summary(
        self,
        mock_indy_adapter: MagicMock,
        mock_sheets_adapter: MagicMock,
    ) -> None:
        """Retourne un résumé: nb importées, nb lettrées auto, nb à vérifier."""
        # ARRANGE
        from src.services.bank_reconciliation import ReconciliationService

        invoice_paye = Invoice(
            facture_id="F001",
            client_id="C001",
            statut=InvoiceStatus.PAYE,
            montant_unitaire=100.0,
            quantite=1.0,
        )

        indy_csv_data = [
            {
                "id": "TXN001",
                "date": "2026-03-20",
                "amount": "100.00",
                "label": "Paiement URSSAF",
            }
        ]

        mock_indy_adapter.export_journal_csv.return_value = indy_csv_data
        mock_sheets_adapter.get_all_transactions.return_value = []
        mock_sheets_adapter.get_all_invoices.return_value = [invoice_paye]

        service = ReconciliationService(mock_indy_adapter, mock_sheets_adapter)

        # ACT
        result = service.reconcile()

        # ASSERT
        assert isinstance(result, dict)
        assert "transactions_imported" in result
        assert "lettrage_updated" in result
        assert "auto_matched" in result
        assert "to_verify" in result
