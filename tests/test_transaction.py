"""Tests pour le modèle Transaction — CDC §5."""

from src.models.transaction import LettrageStatus, Transaction


class TestTransactionModel:
    """Tests pour le modèle Transaction."""

    def test_default_statut_lettrage_is_non_lettre(self) -> None:
        txn = Transaction(transaction_id="T001")
        assert txn.statut_lettrage == LettrageStatus.NON_LETTRE

    def test_default_source_is_indy(self) -> None:
        txn = Transaction(transaction_id="T001")
        assert txn.source == "indy"

    def test_facture_id_none_by_default(self) -> None:
        txn = Transaction(transaction_id="T001")
        assert txn.facture_id is None

    def test_full_transaction(self) -> None:
        txn = Transaction(
            transaction_id="T001",
            indy_id="INDY-456",
            date_valeur="2026-03-15",
            montant=90.0,
            libelle="VIREMENT URSSAF SAP",
            type="credit",
            facture_id="F001",
            statut_lettrage=LettrageStatus.LETTRE_AUTO,
            date_import="2026-03-16",
        )
        assert txn.montant == 90.0
        assert txn.statut_lettrage == LettrageStatus.LETTRE_AUTO
