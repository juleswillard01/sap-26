"""Modele Facture avec machine a etats."""

from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum as StrEnum  # type: ignore

from pydantic import BaseModel


class InvoiceStatus(StrEnum):
    """Etats possibles d'une facture — CDC §2.1."""

    BROUILLON = "BROUILLON"
    SOUMIS = "SOUMIS"
    CREE = "CREE"
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE = "VALIDE"
    PAYE = "PAYE"
    RAPPROCHE = "RAPPROCHE"
    ERREUR = "ERREUR"
    EXPIRE = "EXPIRE"
    REJETE = "REJETE"
    ANNULE = "ANNULE"


class InvalidTransitionError(ValueError):
    """Transition d'etat invalide — CDC §2.2."""


# Transitions valides : {etat_source: [etats_destination]}
VALID_TRANSITIONS: dict[InvoiceStatus, list[InvoiceStatus]] = {
    InvoiceStatus.BROUILLON: [InvoiceStatus.SOUMIS, InvoiceStatus.ANNULE],
    InvoiceStatus.SOUMIS: [InvoiceStatus.CREE, InvoiceStatus.ERREUR],
    InvoiceStatus.CREE: [InvoiceStatus.EN_ATTENTE],
    InvoiceStatus.EN_ATTENTE: [InvoiceStatus.VALIDE, InvoiceStatus.EXPIRE, InvoiceStatus.REJETE],
    InvoiceStatus.VALIDE: [InvoiceStatus.PAYE],
    InvoiceStatus.PAYE: [InvoiceStatus.RAPPROCHE],
    InvoiceStatus.ERREUR: [InvoiceStatus.BROUILLON],
    InvoiceStatus.EXPIRE: [InvoiceStatus.BROUILLON],
    InvoiceStatus.REJETE: [InvoiceStatus.BROUILLON],
    InvoiceStatus.RAPPROCHE: [],
    InvoiceStatus.ANNULE: [],
}


class Invoice(BaseModel):
    """Represente une facture SAP."""

    facture_id: str
    client_id: str
    nature_code: str = ""
    quantite: float = 0.0
    montant_unitaire: float = 0.0
    statut: InvoiceStatus = InvoiceStatus.BROUILLON
    description: str = ""
    urssaf_demande_id: str | None = None

    @property
    def montant_total(self) -> float:
        """Montant total = quantite x prix unitaire."""
        return self.quantite * self.montant_unitaire

    def can_transition_to(self, new_status: InvoiceStatus) -> bool:
        """Verifie si la transition est valide — CDC §2.2."""
        allowed = VALID_TRANSITIONS.get(self.statut, [])
        return new_status in allowed

    def transition_to(self, new_status: InvoiceStatus) -> None:
        """Effectue la transition d'etat.

        Raises:
            InvalidTransitionError: Si la transition est invalide.
        """
        if not self.can_transition_to(new_status):
            msg = f"Transition invalide : {self.statut} -> {new_status}"
            raise InvalidTransitionError(msg)
        self.statut = new_status
