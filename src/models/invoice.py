"""Modèle Facture avec machine à états."""

from enum import StrEnum

from pydantic import BaseModel


class InvoiceStatus(StrEnum):
    """États possibles d'une facture — CDC §2.1."""

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


# Transitions valides : {état_source: [états_destination]}
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
}


class Invoice(BaseModel):
    """Représente une facture SAP."""

    facture_id: str
    client_id: str
    nature_code: str
    quantite: float
    montant_unitaire: float
    statut: InvoiceStatus = InvoiceStatus.BROUILLON
    description: str = ""
    urssaf_demande_id: str | None = None

    @property
    def montant_total(self) -> float:
        """Montant total = quantité × prix unitaire."""
        return self.quantite * self.montant_unitaire

    def can_transition_to(self, new_status: InvoiceStatus) -> bool:
        """Vérifie si la transition est valide — CDC §2.2."""
        allowed = VALID_TRANSITIONS.get(self.statut, [])
        return new_status in allowed

    def transition_to(self, new_status: InvoiceStatus) -> None:
        """Effectue la transition d'état.

        Raises:
            ValueError: Si la transition est invalide.
        """
        if not self.can_transition_to(new_status):
            msg = f"Transition invalide : {self.statut} → {new_status}"
            raise ValueError(msg)
        self.statut = new_status
