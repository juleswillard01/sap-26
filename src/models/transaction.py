"""Modèle Transaction bancaire et scoring de lettrage."""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class LettrageStatus(StrEnum):
    """Statut de lettrage — CDC §3.2."""

    NON_LETTRE = "NON_LETTRE"
    AUTO = "AUTO"
    A_VERIFIER = "A_VERIFIER"
    PAS_DE_MATCH = "PAS_DE_MATCH"


class Transaction(BaseModel):
    """Représente une transaction bancaire Indy."""

    transaction_id: str
    indy_id: str
    date_valeur: date
    montant: float
    libelle: str
    type: str = ""
    source: str = "INDY"
    facture_id: str | None = None
    statut_lettrage: LettrageStatus = LettrageStatus.NON_LETTRE


def compute_matching_score(
    invoice_amount: float,
    transaction_amount: float,
    invoice_payment_date: date,
    transaction_date: date,
    transaction_label: str,
) -> int:
    """Calcule le score de confiance pour le lettrage — CDC §3.2.

    Args:
        invoice_amount: Montant de la facture (100%).
        transaction_amount: Montant de la transaction.
        invoice_payment_date: Date de paiement attendue.
        transaction_date: Date de la transaction.
        transaction_label: Libellé de la transaction.

    Returns:
        Score de confiance (0-100).
    """
    score = 0

    # Montant exact = +50
    if abs(invoice_amount - transaction_amount) < 0.01:
        score += 50

    # Date < 3 jours = +30
    delta_days = abs((transaction_date - invoice_payment_date).days)
    if delta_days <= 3:
        score += 30

    # Libellé contient URSSAF = +20
    if "urssaf" in transaction_label.lower():
        score += 20

    return score
