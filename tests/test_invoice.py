"""Tests pour la machine à états Facture — CDC §4."""

import pytest

from src.models.invoice import (
    VALID_TRANSITIONS,
    InvalidTransitionError,
    Invoice,
    InvoiceStatus,
)


class TestInvoiceModel:
    def test_default_status_is_brouillon(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001")
        assert inv.statut == InvoiceStatus.BROUILLON

    def test_montant_total_calcul(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", quantite=2.0, montant_unitaire=45.0)
        assert inv.montant_total == 90.0

    def test_montant_total_zero_par_defaut(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001")
        assert inv.montant_total == 0.0


class TestValidTransitions:
    def test_brouillon_to_soumis(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001")
        inv.transition_to(InvoiceStatus.SOUMIS)
        assert inv.statut == InvoiceStatus.SOUMIS

    def test_brouillon_to_annule(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001")
        inv.transition_to(InvoiceStatus.ANNULE)
        assert inv.statut == InvoiceStatus.ANNULE

    def test_soumis_to_cree(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.SOUMIS)
        inv.transition_to(InvoiceStatus.CREE)
        assert inv.statut == InvoiceStatus.CREE

    def test_soumis_to_erreur(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.SOUMIS)
        inv.transition_to(InvoiceStatus.ERREUR)
        assert inv.statut == InvoiceStatus.ERREUR

    def test_erreur_to_brouillon(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.ERREUR)
        inv.transition_to(InvoiceStatus.BROUILLON)
        assert inv.statut == InvoiceStatus.BROUILLON

    def test_cree_to_en_attente(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.CREE)
        inv.transition_to(InvoiceStatus.EN_ATTENTE)
        assert inv.statut == InvoiceStatus.EN_ATTENTE

    def test_en_attente_to_valide(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.EN_ATTENTE)
        inv.transition_to(InvoiceStatus.VALIDE)
        assert inv.statut == InvoiceStatus.VALIDE

    def test_en_attente_to_expire(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.EN_ATTENTE)
        inv.transition_to(InvoiceStatus.EXPIRE)
        assert inv.statut == InvoiceStatus.EXPIRE

    def test_en_attente_to_rejete(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.EN_ATTENTE)
        inv.transition_to(InvoiceStatus.REJETE)
        assert inv.statut == InvoiceStatus.REJETE

    def test_valide_to_paye(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.VALIDE)
        inv.transition_to(InvoiceStatus.PAYE)
        assert inv.statut == InvoiceStatus.PAYE

    def test_paye_to_rapproche(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.PAYE)
        inv.transition_to(InvoiceStatus.RAPPROCHE)
        assert inv.statut == InvoiceStatus.RAPPROCHE

    def test_expire_to_brouillon(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.EXPIRE)
        inv.transition_to(InvoiceStatus.BROUILLON)
        assert inv.statut == InvoiceStatus.BROUILLON

    def test_rejete_to_brouillon(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.REJETE)
        inv.transition_to(InvoiceStatus.BROUILLON)
        assert inv.statut == InvoiceStatus.BROUILLON


class TestInvalidTransitions:
    def test_brouillon_to_paye_raises(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001")
        with pytest.raises(InvalidTransitionError):
            inv.transition_to(InvoiceStatus.PAYE)

    def test_annule_is_terminal(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.ANNULE)
        with pytest.raises(InvalidTransitionError):
            inv.transition_to(InvoiceStatus.BROUILLON)

    def test_rapproche_is_terminal(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001", statut=InvoiceStatus.RAPPROCHE)
        with pytest.raises(InvalidTransitionError):
            inv.transition_to(InvoiceStatus.BROUILLON)

    def test_can_transition_false_for_invalid(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001")
        assert inv.can_transition_to(InvoiceStatus.PAYE) is False

    def test_can_transition_true_for_valid(self) -> None:
        inv = Invoice(facture_id="F001", client_id="C001")
        assert inv.can_transition_to(InvoiceStatus.SOUMIS) is True


class TestAllTransitionsCovered:
    def test_every_status_in_valid_transitions(self) -> None:
        for status in InvoiceStatus:
            assert status in VALID_TRANSITIONS, f"{status} manquant"
