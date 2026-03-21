from __future__ import annotations

from typing import Any

import polars as pl

# Sheet names (constants)
SHEET_CLIENTS = "Clients"
SHEET_FACTURES = "Factures"
SHEET_TRANSACTIONS = "Transactions"
SHEET_LETTRAGE = "Lettrage"
SHEET_BALANCES = "Balances"
SHEET_METRICS_NOVA = "Metrics NOVA"
SHEET_COTISATIONS = "Cotisations"
SHEET_FISCAL_IR = "Fiscal IR"

# Data brute (3 editable sheets)
SCHEMA_CLIENTS = {
    "client_id": pl.Utf8,
    "nom": pl.Utf8,
    "prenom": pl.Utf8,
    "email": pl.Utf8,
    "telephone": pl.Utf8,
    "adresse": pl.Utf8,
    "code_postal": pl.Utf8,
    "ville": pl.Utf8,
    "urssaf_id": pl.Utf8,
    "statut_urssaf": pl.Utf8,
    "date_inscription": pl.Date,
    "actif": pl.Boolean,
}

SCHEMA_FACTURES = {
    "facture_id": pl.Utf8,
    "client_id": pl.Utf8,
    "type_unite": pl.Utf8,
    "nature_code": pl.Utf8,
    "quantite": pl.Float64,
    "montant_unitaire": pl.Float64,
    "montant_total": pl.Float64,
    "date_debut": pl.Date,
    "date_fin": pl.Date,
    "description": pl.Utf8,
    "statut": pl.Utf8,
    "urssaf_demande_id": pl.Utf8,
    "date_soumission": pl.Date,
    "date_validation": pl.Date,
    "date_paiement": pl.Date,
    "date_rapprochement": pl.Date,
    "pdf_drive_id": pl.Utf8,
}

SCHEMA_TRANSACTIONS = {
    "transaction_id": pl.Utf8,
    "indy_id": pl.Utf8,
    "date_valeur": pl.Date,
    "montant": pl.Float64,
    "libelle": pl.Utf8,
    "type": pl.Utf8,
    "source": pl.Utf8,
    "facture_id": pl.Utf8,
    "statut_lettrage": pl.Utf8,
    "date_import": pl.Date,
}

# Calcules (5 read-only sheets)
SCHEMA_LETTRAGE = {
    "facture_id": pl.Utf8,
    "montant_facture": pl.Float64,
    "txn_id": pl.Utf8,
    "txn_montant": pl.Float64,
    "ecart": pl.Float64,
    "score_confiance": pl.Int64,
    "statut": pl.Utf8,
}

SCHEMA_BALANCES = {
    "mois": pl.Utf8,
    "nb_factures": pl.Int64,
    "ca_total": pl.Float64,
    "recu_urssaf": pl.Float64,
    "solde": pl.Float64,
    "nb_non_lettrees": pl.Int64,
    "nb_en_attente": pl.Int64,
}

SCHEMA_METRICS_NOVA = {
    "trimestre": pl.Utf8,
    "nb_intervenants": pl.Int64,
    "heures_effectuees": pl.Float64,
    "nb_particuliers": pl.Int64,
    "ca_trimestre": pl.Float64,
    "deadline_saisie": pl.Date,
}

SCHEMA_COTISATIONS = {
    "mois": pl.Utf8,
    "ca_encaisse": pl.Float64,
    "taux_charges": pl.Float64,
    "montant_charges": pl.Float64,
    "date_limite": pl.Date,
    "cumul_ca": pl.Float64,
    "net_apres_charges": pl.Float64,
}

SCHEMA_FISCAL_IR = {
    "revenu_apprentissage": pl.Float64,
    "seuil_exo": pl.Float64,
    "ca_micro": pl.Float64,
    "abattement": pl.Float64,
    "revenu_imposable": pl.Float64,
    "tranches_ir": pl.Utf8,
    "taux_marginal": pl.Float64,
    "simulation_vl": pl.Float64,
}

# Master schema mapping
SHEET_SCHEMAS = {
    SHEET_CLIENTS: SCHEMA_CLIENTS,
    SHEET_FACTURES: SCHEMA_FACTURES,
    SHEET_TRANSACTIONS: SCHEMA_TRANSACTIONS,
    SHEET_LETTRAGE: SCHEMA_LETTRAGE,
    SHEET_BALANCES: SCHEMA_BALANCES,
    SHEET_METRICS_NOVA: SCHEMA_METRICS_NOVA,
    SHEET_COTISATIONS: SCHEMA_COTISATIONS,
    SHEET_FISCAL_IR: SCHEMA_FISCAL_IR,
}

# Sheet classification
DATA_SHEETS: list[str] = [SHEET_CLIENTS, SHEET_FACTURES, SHEET_TRANSACTIONS]
CALC_SHEETS: list[str] = [
    SHEET_LETTRAGE,
    SHEET_BALANCES,
    SHEET_METRICS_NOVA,
    SHEET_COTISATIONS,
    SHEET_FISCAL_IR,
]

# Ordered column headers for each sheet
HEADERS: dict[str, list[str]] = {
    SHEET_CLIENTS: [
        "client_id",
        "nom",
        "prenom",
        "email",
        "telephone",
        "adresse",
        "code_postal",
        "ville",
        "urssaf_id",
        "statut_urssaf",
        "date_inscription",
        "actif",
    ],
    SHEET_FACTURES: [
        "facture_id",
        "client_id",
        "type_unite",
        "nature_code",
        "quantite",
        "montant_unitaire",
        "montant_total",
        "date_debut",
        "date_fin",
        "description",
        "statut",
        "urssaf_demande_id",
        "date_soumission",
        "date_validation",
        "date_paiement",
        "date_rapprochement",
        "pdf_drive_id",
    ],
    SHEET_TRANSACTIONS: [
        "transaction_id",
        "indy_id",
        "date_valeur",
        "montant",
        "libelle",
        "type",
        "source",
        "facture_id",
        "statut_lettrage",
        "date_import",
    ],
    SHEET_LETTRAGE: [
        "facture_id",
        "montant_facture",
        "txn_id",
        "txn_montant",
        "ecart",
        "score_confiance",
        "statut",
    ],
    SHEET_BALANCES: [
        "mois",
        "nb_factures",
        "ca_total",
        "recu_urssaf",
        "solde",
        "nb_non_lettrees",
        "nb_en_attente",
    ],
    SHEET_METRICS_NOVA: [
        "trimestre",
        "nb_intervenants",
        "heures_effectuees",
        "nb_particuliers",
        "ca_trimestre",
        "deadline_saisie",
    ],
    SHEET_COTISATIONS: [
        "mois",
        "ca_encaisse",
        "taux_charges",
        "montant_charges",
        "date_limite",
        "cumul_ca",
        "net_apres_charges",
    ],
    SHEET_FISCAL_IR: [
        "revenu_apprentissage",
        "seuil_exo",
        "ca_micro",
        "abattement",
        "revenu_imposable",
        "tranches_ir",
        "taux_marginal",
        "simulation_vl",
    ],
}


def get_schema(sheet_name: str) -> dict[str, Any]:
    """Retrieve Polars schema for a given sheet name.

    Args:
        sheet_name: Name of the sheet (e.g., "Clients", "Factures")

    Returns:
        Dictionary mapping column names to Polars data types

    Raises:
        KeyError: If sheet_name not found in SHEET_SCHEMAS
    """
    return SHEET_SCHEMAS[sheet_name]


def get_headers(sheet_name: str) -> list[str]:
    """Retrieve ordered column headers for a given sheet.

    Args:
        sheet_name: Name of the sheet

    Returns:
        Ordered list of column names

    Raises:
        KeyError: If sheet_name not found in HEADERS
    """
    return HEADERS[sheet_name]


def is_editable_sheet(sheet_name: str) -> bool:
    """Check if sheet is editable (data brute).

    Args:
        sheet_name: Name of the sheet

    Returns:
        True if sheet is in DATA_SHEETS, False otherwise
    """
    return sheet_name in DATA_SHEETS


def is_calculated_sheet(sheet_name: str) -> bool:
    """Check if sheet is calculated (read-only).

    Args:
        sheet_name: Name of the sheet

    Returns:
        True if sheet is in CALC_SHEETS, False otherwise
    """
    return sheet_name in CALC_SHEETS
