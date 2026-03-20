"""Lettrage automatique factures ↔ transactions — CDC §5.3."""

from src.models.transaction import LettrageResult


def compute_lettrage_score(
    facture_montant: float,
    facture_date_paiement: str,
    transaction_montant: float,
    transaction_date: str,
    transaction_libelle: str,
) -> LettrageResult:
    """Calcule le score de confiance pour le lettrage.

    Scoring :
    - Montant exact (100% facture) = +50
    - Date < 3 jours = +30
    - Libellé contient 'URSSAF' = +20

    Returns:
        Résultat du scoring avec statut.
    """
    raise NotImplementedError("À implémenter — CDC §5.3")
