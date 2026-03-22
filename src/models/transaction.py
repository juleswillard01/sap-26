"""Modele Transaction bancaire et scoring de lettrage."""

from __future__ import annotations

from datetime import date  # noqa: TC003

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum as StrEnum  # type: ignore

from pydantic import BaseModel, computed_field


class LettrageStatus(StrEnum):
    """Statut de lettrage — CDC §3.2."""

    NON_LETTRE = "NON_LETTRE"
    LETTRE_AUTO = "LETTRE_AUTO"
    A_VERIFIER = "A_VERIFIER"
    PAS_DE_MATCH = "PAS_DE_MATCH"


class Transaction(BaseModel):
    """Represente une transaction bancaire Indy."""

    transaction_id: str
    indy_id: str = ""
    date_valeur: date | None = None
    montant: float = 0.0
    libelle: str = ""
    type: str = ""
    source: str = "indy"
    facture_id: str | None = None
    statut_lettrage: LettrageStatus = LettrageStatus.NON_LETTRE
    date_import: date | None = None


class LettrageResult(BaseModel):
    """Resultat du scoring de lettrage — CDC §3.2."""

    facture_id: str
    transaction_id: str | None = None
    score: int = 0
    montant_exact: bool = False
    date_proche: bool = False
    libelle_urssaf: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def statut(self) -> LettrageStatus:
        """Determine le statut selon le score — CDC §3.2."""
        if self.transaction_id is None:
            return LettrageStatus.PAS_DE_MATCH
        if self.score >= 80:
            return LettrageStatus.LETTRE_AUTO
        return LettrageStatus.A_VERIFIER


def compute_matching_score(
    invoice_amount: float,
    transaction_amount: float,
    invoice_payment_date: date,
    transaction_date: date,
    transaction_label: str,
) -> int:
    """Calcule le score de confiance pour le lettrage — CDC §3.2.

    Fenêtre ±5 jours : transactions hors cette fenêtre retournent 0.
    """
    delta_days = abs((transaction_date - invoice_payment_date).days)

    # Fenêtre ±5 jours — CDC §3.2
    if delta_days > 5:
        return 0

    score = 0

    if abs(invoice_amount - transaction_amount) < 0.01:
        score += 50

    if delta_days <= 3:
        score += 30

    if "urssaf" in transaction_label.lower():
        score += 20

    return score
