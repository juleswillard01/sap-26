"""Patito models bridging Pydantic and Polars for Google Sheets tabs.

All 8 sheets from SCHEMAS.html section 5:
- 3 data writable: ClientSheet, FactureSheet, TransactionSheet
- 5 calculated read-only: LettrageSheet, BalancesSheet, MetricsNovaSheet,
  CotisationsSheet, FiscalIRSheet
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum as StrEnum  # type: ignore

import patito as pt  # type: ignore[import-untyped]
from pydantic import Field

# ============================================================================
# ENUMS — statuts et types recurrents
# ============================================================================


class ClientStatutURSSAF(StrEnum):
    """Statut URSSAF du client — CDC §1.1."""

    EN_ATTENTE = "EN_ATTENTE"
    INSCRIT = "INSCRIT"
    ERREUR = "ERREUR"
    INACTIF = "INACTIF"


class FactureStatut(StrEnum):
    """Statut facture machine a etats — CDC §7."""

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


class LettrageStatut(StrEnum):
    """Statut lettrage facture/transaction — CDC §6."""

    LETTRE = "LETTRE"
    A_VERIFIER = "A_VERIFIER"
    PAS_DE_MATCH = "PAS_DE_MATCH"


class TransactionType(StrEnum):
    """Type transaction bancaire."""

    VIREMENT_ENTRANT = "VIREMENT_ENTRANT"
    VIREMENT_SORTANT = "VIREMENT_SORTANT"
    PRELEVEMENT = "PRELEVEMENT"
    AUTRE = "AUTRE"


# ============================================================================
# SHEET 1: CLIENTS (writable) — 13 champs
# ============================================================================


class ClientSheet(pt.Model):
    """Onglet Clients — data brute, editables par Jules.

    Client (parent d'eleve) : inscription URSSAF, coordonnees.
    """

    client_id: str = Field(description="ID technique client, ex. CL_20260101_DUPONT")
    nom: str = Field(min_length=1, description="Nom famille")
    prenom: str = Field(min_length=1, description="Prenom")
    email: str = Field(description="Email contact principal")
    telephone: str = Field(default="", description="Tel contact, opt")
    adresse: str = Field(default="", description="Adresse postale")
    code_postal: str = Field(default="", description="Code postal FR")
    ville: str = Field(default="", description="Ville")
    urssaf_id: str | None = Field(default=None, description="ID technique URSSAF si inscrit")
    statut_urssaf: ClientStatutURSSAF = Field(
        default=ClientStatutURSSAF.EN_ATTENTE,
        description="EN_ATTENTE | INSCRIT | ERREUR | INACTIF",
    )
    date_inscription: date | None = Field(
        default=None, description="Date inscription URSSAF, auto-remplissage"
    )
    actif: bool = Field(default=True, description="Client actif oui/non")


# ============================================================================
# SHEET 2: FACTURES (writable) — 15 champs
# ============================================================================


class FactureSheet(pt.Model):
    """Onglet Factures — data brute, editables (BROUILLON uniquement).

    Facture SAP : heures/tarif, statut URSSAF, suivi paiement.
    """

    facture_id: str = Field(description="ID facture, ex. FAC_20260101_001")
    client_id: str = Field(description="Ref Client (FK)")
    type_unite: str = Field(
        default="HEURE", description="Unité de facturation : HEURE, FORFAIT, SEANCE"
    )
    nature_code: str = Field(
        default="COURS_PARTICULIERS",
        description="Nature URSSAF : COURS_PARTICULIERS, etc.",
    )
    quantite: Annotated[float, Field(gt=0)] = Field(description="Nombre heures ou unites")
    montant_unitaire: Annotated[float, Field(ge=0)] = Field(description="Tarif/heure")
    montant_total: Annotated[float, Field(ge=0)] = Field(
        description="Total = quantite x tarif (formule)"
    )
    date_debut: date = Field(description="Date premiere heure")
    date_fin: date = Field(description="Date derniere heure")
    description: str = Field(default="", description="Details libres")
    statut: FactureStatut = Field(
        default=FactureStatut.BROUILLON,
        description="État machine a etats — CDC §7",
    )
    urssaf_demande_id: str | None = Field(default=None, description="ID demande URSSAF si soumis")
    date_soumission: date | None = Field(default=None, description="Date POST /demandes-paiement")
    date_validation: date | None = Field(
        default=None, description="Date client valide sur portail URSSAF"
    )
    date_paiement: date | None = Field(default=None, description="Date URSSAF effectue le virement")
    date_rapprochement: date | None = Field(
        default=None, description="Date lettrage auto avec transaction Indy"
    )
    pdf_drive_id: str | None = Field(default=None, description="Google Drive ID PDF genere")


# ============================================================================
# SHEET 3: TRANSACTIONS (writable) — 10 champs
# ============================================================================


class TransactionSheet(pt.Model):
    """Onglet Transactions — data brute, importees via Indy Playwright.

    Transaction Indy : virements, prelevements, imports manuels.
    """

    transaction_id: str = Field(description="ID unique transaction locale")
    indy_id: str = Field(default="", description="ID transaction Indy si importe")
    date_valeur: date = Field(description="Date valeur comptable")
    montant: Annotated[float, Field(json_schema_extra={"ne": 0})] = Field(
        description="Montant signe"
    )
    libelle: str = Field(description="Libelle transaction")
    type: TransactionType = Field(default=TransactionType.AUTRE, description="Type transaction")
    source: str = Field(default="indy", description="Source : indy, manual, etc.")
    facture_id: str | None = Field(default=None, description="FK Facture si lettree manuellement")
    statut_lettrage: LettrageStatut = Field(
        default=LettrageStatut.PAS_DE_MATCH,
        description="LETTRE | A_VERIFIER | PAS_DE_MATCH — CDC §6",
    )
    date_import: date = Field(description="Date import dans SAP-Facture")


# ============================================================================
# SHEET 4: LETTRAGE (calculated, read-only) — 7 champs
# ============================================================================


class LettrageSheet(pt.Model):
    """Onglet Lettrage — calcule, lecture seule (formules matching).

    Lettrage factures/transactions : matching auto + scoring confiance.
    """

    facture_id: str = Field(description="FK Facture")
    montant_facture: Annotated[float, Field(ge=0)] = Field(description="Montant total facture")
    txn_id: str | None = Field(default=None, description="FK Transaction matchee")
    txn_montant: Annotated[float, Field(ge=0)] | None = Field(
        default=None, description="Montant transaction si match"
    )
    ecart: Annotated[float, Field(ge=0)] | None = Field(
        default=None, description="Ecart montant si match"
    )
    score_confiance: Annotated[int, Field(ge=0, le=100)] = Field(
        default=0,
        description="Score lettrage 0-100 (exact=+50, date=+30, libelle=+20) — CDC §6",
    )
    statut: LettrageStatut = Field(
        default=LettrageStatut.PAS_DE_MATCH,
        description="AUTO (score >= 80) | A_VERIFIER (score < 80) | PAS_DE_MATCH",
    )


# ============================================================================
# SHEET 5: BALANCES (calculated, read-only) — 6 champs
# ============================================================================


class BalancesSheet(pt.Model):
    """Onglet Balances — calcule, lecture seule (soldes mensuels).

    Soldes mensuels : CA, recu URSSAF, lettrage status.
    """

    mois: str = Field(description="Mois YYYY-MM")
    nb_factures: Annotated[int, Field(ge=0)] = Field(description="Nombre factures creees")
    ca_total: Annotated[float, Field(ge=0)] = Field(
        description="CA total factures PAYE ou RAPPROCHE"
    )
    recu_urssaf: Annotated[float, Field(ge=0)] = Field(
        description="Somme transactions URSSAF lettrees"
    )
    solde: Annotated[float, Field(le=0)] = Field(description="Ecart CA vs recu (solde a recevoir)")
    nb_non_lettrees: Annotated[int, Field(ge=0)] = Field(description="Factures PAYE non lettrees")
    nb_en_attente: Annotated[int, Field(ge=0)] = Field(description="Factures EN_ATTENTE ou VALIDE")


# ============================================================================
# SHEET 6: METRICS NOVA (calculated, read-only) — 6 champs
# ============================================================================


class MetricsNovaSheet(pt.Model):
    """Onglet Metrics NOVA — calcule, lecture seule (reporting trimestriel).

    Metriques trimestrielles pour attestations fiscales.
    """

    trimestre: str = Field(description="Trimestre YYYY-Q1/Q2/Q3/Q4")
    nb_intervenants: Annotated[int, Field(ge=1)] = Field(
        default=1, description="Nombre intervenants (toujours 1 pour Jules MVP)"
    )
    heures_effectuees: Annotated[float, Field(ge=0)] = Field(
        description="Heures cumulees facturees"
    )
    nb_particuliers: Annotated[int, Field(ge=0)] = Field(
        description="Nombre clients uniques factures"
    )
    ca_trimestre: Annotated[float, Field(ge=0)] = Field(description="CA trimestre tous statuts")
    deadline_saisie: date = Field(description="Deadline declaration NOVA (J+30 fin Q)")


# ============================================================================
# SHEET 7: COTISATIONS (calculated, read-only) — 7 champs
# ============================================================================


class CotisationsSheet(pt.Model):
    """Onglet Cotisations — calcule, lecture seule (charges mensuelles).

    Cotisations micro-entrepreneur : 25.8% CA encaisse (regimen BNC).
    """

    mois: str = Field(description="Mois YYYY-MM")
    ca_encaisse: Annotated[float, Field(ge=0)] = Field(description="CA paye/rapproche le mois")
    taux_charges: float = Field(default=25.8, description="Taux URSSAF micro-entreprise BNC (%)")
    montant_charges: Annotated[float, Field(ge=0)] = Field(
        description="Montant charges = CA * taux / 100"
    )
    date_limite: date = Field(description="Date limite paiement cotisations")
    cumul_ca: Annotated[float, Field(ge=0)] = Field(description="CA cumule annee a date")
    net_apres_charges: Annotated[float, Field(ge=0)] = Field(
        description="Net = CA encaisse - charges"
    )


# ============================================================================
# SHEET 8: FISCAL IR (calculated, read-only) — 8 champs
# ============================================================================


class FiscalIRSheet(pt.Model):
    """Onglet Fiscal IR — calcule, lecture seule (simulation impot annuel).

    Simulation IR : abattement 34% BNC, tranches progressives, VL.
    """

    revenu_apprentissage: Annotated[float, Field(ge=0)] = Field(
        description="Revenu cotisation apprentissage (0.28% CA si dépassement)"
    )
    seuil_exo: float = Field(
        default=5000.0,
        description="Seuil exo apprentissage (5000 EUR 2026)",
    )
    ca_micro: Annotated[float, Field(ge=0)] = Field(description="CA micro-entreprise annee")
    abattement: Annotated[float, Field(ge=0)] = Field(
        default=0.34,
        description="Taux abattement BNC (34% 2026)",
    )
    revenu_imposable: Annotated[float, Field(ge=0)] = Field(
        description="Revenu = CA * (1 - abattement)"
    )
    tranches_ir: str = Field(
        default="0",
        description="Tranches IR applicables, texte libre (ex: T1@11% + T2@30%)",
    )
    taux_marginal: Annotated[float, Field(ge=0, le=100)] = Field(
        default=0.0, description="Taux marginal IR en vigueur (%)"
    )
    simulation_vl: Annotated[float, Field(ge=0)] = Field(
        description="Simulation impôt VL à titre personnel (taux 2.2% 2026)",
    )


# ============================================================================
# CONSTANTS — Mapping feuilles et classification
# ============================================================================

SHEET_NAMES: dict[type[pt.Model], str] = {
    ClientSheet: "Clients",
    FactureSheet: "Factures",
    TransactionSheet: "Transactions",
    LettrageSheet: "Lettrage",
    BalancesSheet: "Balances",
    MetricsNovaSheet: "Metrics NOVA",
    CotisationsSheet: "Cotisations",
    FiscalIRSheet: "Fiscal IR",
}
"""Mapping classe Patito -> nom onglet Google Sheets."""

DATA_MODELS: list[type[pt.Model]] = [
    ClientSheet,
    FactureSheet,
    TransactionSheet,
]
"""3 onglets data brute editables (sous conditions)."""

CALC_MODELS: list[type[pt.Model]] = [
    LettrageSheet,
    BalancesSheet,
    MetricsNovaSheet,
    CotisationsSheet,
    FiscalIRSheet,
]
"""5 onglets calcules lecture seule (formules Excel/Sheets)."""


# ============================================================================
# MODEL REBUILD — Resolve deferred annotations from __future__
# ============================================================================

_local_namespace = {"date": date}
for model in [
    ClientSheet,
    FactureSheet,
    TransactionSheet,
    LettrageSheet,
    BalancesSheet,
    MetricsNovaSheet,
    CotisationsSheet,
    FiscalIRSheet,
]:
    model.model_rebuild(_types_namespace=_local_namespace)
