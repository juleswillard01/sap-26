"""Tests pour le lettrage bancaire — CDC §5.3."""

from src.models.transaction import LettrageResult, LettrageStatus


class TestLettrageScoring:
    def test_score_100_is_lettre_auto(self) -> None:
        r = LettrageResult(facture_id="F001", transaction_id="T001", score=100,
                           montant_exact=True, date_proche=True, libelle_urssaf=True)
        assert r.statut == LettrageStatus.LETTRE_AUTO

    def test_score_80_is_lettre_auto(self) -> None:
        r = LettrageResult(facture_id="F001", transaction_id="T001", score=80,
                           montant_exact=True, date_proche=True, libelle_urssaf=False)
        assert r.statut == LettrageStatus.LETTRE_AUTO

    def test_score_79_is_a_verifier(self) -> None:
        r = LettrageResult(facture_id="F001", transaction_id="T001", score=79,
                           montant_exact=True, date_proche=False, libelle_urssaf=True)
        assert r.statut == LettrageStatus.A_VERIFIER

    def test_no_transaction_is_pas_de_match(self) -> None:
        r = LettrageResult(facture_id="F001", transaction_id=None, score=0)
        assert r.statut == LettrageStatus.PAS_DE_MATCH

    def test_score_50_is_a_verifier(self) -> None:
        r = LettrageResult(facture_id="F001", transaction_id="T001", score=50,
                           montant_exact=True, date_proche=False, libelle_urssaf=False)
        assert r.statut == LettrageStatus.A_VERIFIER

    def test_score_0_with_transaction_is_a_verifier(self) -> None:
        r = LettrageResult(facture_id="F001", transaction_id="T001", score=0)
        assert r.statut == LettrageStatus.A_VERIFIER
