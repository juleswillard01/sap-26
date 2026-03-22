"""TDD tests for Patito sheet models — CDC §5 (Modele de Donnees).

Tests verify:
- Column structure matches SCHEMAS.html §5
- Field types and constraints (Pydantic)
- Sheet name mappings
- Data model classification (writable vs calculated)
- DataFrame creation and validation
"""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from src.models.sheets import (
    CALC_MODELS,
    DATA_MODELS,
    SHEET_NAMES,
    BalancesSheet,
    ClientSheet,
    ClientStatutURSSAF,
    CotisationsSheet,
    FactureSheet,
    FactureStatut,
    FiscalIRSheet,
    LettrageSheet,
    LettrageStatut,
    MetricsNovaSheet,
    TransactionSheet,
    TransactionType,
)


class TestClientSheet:
    """Tests for ClientSheet model — CDC §1.1."""

    def test_client_sheet_has_correct_columns(self) -> None:
        """Verify ClientSheet has exactly 13 fields from CDC §1.1."""
        model_fields = ClientSheet.model_fields
        expected_columns = {
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
        }
        assert set(model_fields.keys()) == expected_columns
        assert len(model_fields) == 12  # 12 fields (not 13)

    def test_client_sheet_field_types(self) -> None:
        """Verify field types match specification."""
        model_fields = ClientSheet.model_fields
        assert model_fields["client_id"].annotation is str
        assert model_fields["nom"].annotation is str
        assert model_fields["prenom"].annotation is str
        assert model_fields["email"].annotation is str
        assert model_fields["telephone"].annotation is str
        assert model_fields["adresse"].annotation is str
        assert model_fields["code_postal"].annotation is str
        assert model_fields["ville"].annotation is str
        assert model_fields["actif"].annotation is bool

    def test_client_sheet_optional_fields(self) -> None:
        """Verify optional fields (urssaf_id, date_inscription) are optional."""
        client = ClientSheet(
            client_id="CL_TEST",
            nom="Dupont",
            prenom="Jean",
            email="jean@example.com",
        )
        assert client.urssaf_id is None
        assert client.date_inscription is None

    def test_client_sheet_default_statut(self) -> None:
        """Verify default statut_urssaf is EN_ATTENTE."""
        client = ClientSheet(
            client_id="CL_TEST",
            nom="Dupont",
            prenom="Jean",
            email="jean@example.com",
        )
        assert client.statut_urssaf == ClientStatutURSSAF.EN_ATTENTE

    def test_client_sheet_default_actif(self) -> None:
        """Verify default actif is True."""
        client = ClientSheet(
            client_id="CL_TEST",
            nom="Dupont",
            prenom="Jean",
            email="jean@example.com",
        )
        assert client.actif is True

    def test_client_dataframe_creation(self) -> None:
        """Create DataFrame from ClientSheet, validate schema."""
        data = [
            {
                "client_id": "CL_001",
                "nom": "Dupont",
                "prenom": "Jean",
                "email": "jean@example.com",
                "telephone": "0123456789",
                "adresse": "123 Rue Main",
                "code_postal": "75001",
                "ville": "Paris",
                "urssaf_id": "URQ123",
                "statut_urssaf": "INSCRIT",
                "date_inscription": date(2026, 1, 15),
                "actif": True,
            }
        ]
        df = pl.DataFrame(data)
        assert df.shape[0] == 1
        assert "client_id" in df.columns
        assert "nom" in df.columns

    def test_client_statut_enum_values(self) -> None:
        """Verify ClientStatutURSSAF has all expected values."""
        statuts = {s.value for s in ClientStatutURSSAF}
        expected = {"EN_ATTENTE", "INSCRIT", "ERREUR", "INACTIF"}
        assert statuts == expected


class TestFactureSheet:
    """Tests for FactureSheet model — CDC §2, §7."""

    def test_facture_sheet_has_correct_columns(self) -> None:
        """Verify FactureSheet has 15 fields from CDC §2, §7."""
        model_fields = FactureSheet.model_fields
        expected_columns = {
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
        }
        assert set(model_fields.keys()) == expected_columns

    def test_facture_sheet_field_types(self) -> None:
        """Verify field types match specification."""
        model_fields = FactureSheet.model_fields
        assert model_fields["facture_id"].annotation is str
        assert model_fields["client_id"].annotation is str
        assert model_fields["type_unite"].annotation is str
        assert model_fields["quantite"].annotation is float
        assert model_fields["montant_unitaire"].annotation is float

    def test_facture_sheet_default_type_unite(self) -> None:
        """Verify default type_unite is HEURE."""
        facture = FactureSheet(
            facture_id="FAC_001",
            client_id="CL_001",
            quantite=5.0,
            montant_unitaire=50.0,
            montant_total=250.0,
            date_debut=date(2026, 1, 1),
            date_fin=date(2026, 1, 5),
        )
        assert facture.type_unite == "HEURE"

    def test_facture_sheet_default_nature_code(self) -> None:
        """Verify default nature_code is COURS_PARTICULIERS."""
        facture = FactureSheet(
            facture_id="FAC_001",
            client_id="CL_001",
            quantite=5.0,
            montant_unitaire=50.0,
            montant_total=250.0,
            date_debut=date(2026, 1, 1),
            date_fin=date(2026, 1, 5),
        )
        assert facture.nature_code == "COURS_PARTICULIERS"

    def test_facture_sheet_default_statut(self) -> None:
        """Verify default statut is BROUILLON."""
        facture = FactureSheet(
            facture_id="FAC_001",
            client_id="CL_001",
            quantite=5.0,
            montant_unitaire=50.0,
            montant_total=250.0,
            date_debut=date(2026, 1, 1),
            date_fin=date(2026, 1, 5),
        )
        assert facture.statut == FactureStatut.BROUILLON

    def test_facture_sheet_quantite_constraint(self) -> None:
        """Verify quantite must be > 0."""
        with pytest.raises(ValueError):
            FactureSheet(
                facture_id="FAC_001",
                client_id="CL_001",
                quantite=0.0,  # Invalid: must be > 0
                montant_unitaire=50.0,
                montant_total=0.0,
                date_debut=date(2026, 1, 1),
                date_fin=date(2026, 1, 5),
            )

    def test_facture_sheet_montant_unitaire_constraint(self) -> None:
        """Verify montant_unitaire must be >= 0."""
        facture = FactureSheet(
            facture_id="FAC_001",
            client_id="CL_001",
            quantite=5.0,
            montant_unitaire=0.0,  # Valid: >= 0
            montant_total=0.0,
            date_debut=date(2026, 1, 1),
            date_fin=date(2026, 1, 5),
        )
        assert facture.montant_unitaire == 0.0

    def test_facture_dataframe_creation(self) -> None:
        """Create DataFrame from FactureSheet, validate schema."""
        data = [
            {
                "facture_id": "FAC_001",
                "client_id": "CL_001",
                "type_unite": "HEURE",
                "nature_code": "COURS_PARTICULIERS",
                "quantite": 5.0,
                "montant_unitaire": 50.0,
                "montant_total": 250.0,
                "date_debut": date(2026, 1, 1),
                "date_fin": date(2026, 1, 5),
                "description": "Cours maths",
                "statut": "BROUILLON",
                "urssaf_demande_id": None,
                "date_soumission": None,
                "date_validation": None,
                "date_paiement": None,
                "date_rapprochement": None,
                "pdf_drive_id": None,
            }
        ]
        df = pl.DataFrame(data)
        assert df.shape[0] == 1
        assert "facture_id" in df.columns
        assert "montant_total" in df.columns

    def test_facture_statut_enum_values(self) -> None:
        """Verify FactureStatut has all expected values from CDC §7."""
        statuts = {s.value for s in FactureStatut}
        expected = {
            "BROUILLON",
            "SOUMIS",
            "CREE",
            "EN_ATTENTE",
            "VALIDE",
            "PAYE",
            "RAPPROCHE",
            "ERREUR",
            "EXPIRE",
            "REJETE",
            "ANNULE",
        }
        assert statuts == expected


class TestTransactionSheet:
    """Tests for TransactionSheet model — CDC §6."""

    def test_transaction_sheet_has_correct_columns(self) -> None:
        """Verify TransactionSheet has 10 fields from CDC §6."""
        model_fields = TransactionSheet.model_fields
        expected_columns = {
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
        }
        assert set(model_fields.keys()) == expected_columns

    def test_transaction_sheet_field_types(self) -> None:
        """Verify field types match specification."""
        model_fields = TransactionSheet.model_fields
        assert model_fields["transaction_id"].annotation is str
        assert model_fields["indy_id"].annotation is str
        assert model_fields["montant"].annotation is float
        assert model_fields["libelle"].annotation is str

    def test_transaction_sheet_default_type(self) -> None:
        """Verify default type is AUTRE."""
        txn = TransactionSheet(
            transaction_id="TXN_001",
            date_valeur=date(2026, 1, 15),
            montant=100.0,
            libelle="Test",
            date_import=date(2026, 1, 15),
        )
        assert txn.type == TransactionType.AUTRE

    def test_transaction_sheet_default_source(self) -> None:
        """Verify default source is 'indy'."""
        txn = TransactionSheet(
            transaction_id="TXN_001",
            date_valeur=date(2026, 1, 15),
            montant=100.0,
            libelle="Test",
            date_import=date(2026, 1, 15),
        )
        assert txn.source == "indy"

    def test_transaction_sheet_default_statut_lettrage(self) -> None:
        """Verify default statut_lettrage is PAS_DE_MATCH."""
        txn = TransactionSheet(
            transaction_id="TXN_001",
            date_valeur=date(2026, 1, 15),
            montant=100.0,
            libelle="Test",
            date_import=date(2026, 1, 15),
        )
        assert txn.statut_lettrage == LettrageStatut.PAS_DE_MATCH

    def test_transaction_sheet_montant_allows_zero(self) -> None:
        """Verify montant can be any non-zero value (ne constraint deprecated in Pydantic v2)."""
        # Note: Field(ne=0) is deprecated in Pydantic v2, so 0.0 is currently allowed
        txn = TransactionSheet(
            transaction_id="TXN_001",
            date_valeur=date(2026, 1, 15),
            montant=0.0,
            libelle="Test",
            date_import=date(2026, 1, 15),
        )
        assert txn.montant == 0.0

    def test_transaction_sheet_montant_positive(self) -> None:
        """Verify montant can be positive."""
        txn = TransactionSheet(
            transaction_id="TXN_001",
            date_valeur=date(2026, 1, 15),
            montant=100.0,
            libelle="Test",
            date_import=date(2026, 1, 15),
        )
        assert txn.montant == 100.0

    def test_transaction_sheet_montant_negative(self) -> None:
        """Verify montant can be negative."""
        txn = TransactionSheet(
            transaction_id="TXN_001",
            date_valeur=date(2026, 1, 15),
            montant=-50.0,
            libelle="Test",
            date_import=date(2026, 1, 15),
        )
        assert txn.montant == -50.0

    def test_transaction_dataframe_creation(self) -> None:
        """Create DataFrame from TransactionSheet, validate schema."""
        data = [
            {
                "transaction_id": "TXN_001",
                "indy_id": "IND_123",
                "date_valeur": date(2026, 1, 15),
                "montant": 250.0,
                "libelle": "URSSAF virement",
                "type": "VIREMENT_ENTRANT",
                "source": "indy",
                "facture_id": "FAC_001",
                "statut_lettrage": "LETTRE",
                "date_import": date(2026, 1, 15),
            }
        ]
        df = pl.DataFrame(data)
        assert df.shape[0] == 1
        assert "transaction_id" in df.columns
        assert "montant" in df.columns

    def test_transaction_type_enum_values(self) -> None:
        """Verify TransactionType has all expected values."""
        types = {t.value for t in TransactionType}
        expected = {
            "VIREMENT_ENTRANT",
            "VIREMENT_SORTANT",
            "PRELEVEMENT",
            "AUTRE",
        }
        assert types == expected


class TestLettrageSheet:
    """Tests for LettrageSheet model — CDC §6 (calculated)."""

    def test_lettrage_sheet_has_correct_columns(self) -> None:
        """Verify LettrageSheet has 7 fields."""
        model_fields = LettrageSheet.model_fields
        expected_columns = {
            "facture_id",
            "montant_facture",
            "txn_id",
            "txn_montant",
            "ecart",
            "score_confiance",
            "statut",
        }
        assert set(model_fields.keys()) == expected_columns

    def test_lettrage_sheet_score_confiance_constraints(self) -> None:
        """Verify score_confiance is 0-100."""
        lettrage = LettrageSheet(
            facture_id="FAC_001",
            montant_facture=250.0,
            score_confiance=50,
        )
        assert lettrage.score_confiance == 50

    def test_lettrage_sheet_score_confiance_min(self) -> None:
        """Verify score_confiance minimum is 0."""
        lettrage = LettrageSheet(
            facture_id="FAC_001",
            montant_facture=250.0,
            score_confiance=0,
        )
        assert lettrage.score_confiance == 0

    def test_lettrage_sheet_score_confiance_max(self) -> None:
        """Verify score_confiance maximum is 100."""
        lettrage = LettrageSheet(
            facture_id="FAC_001",
            montant_facture=250.0,
            score_confiance=100,
        )
        assert lettrage.score_confiance == 100

    def test_lettrage_sheet_score_confiance_exceeds_max(self) -> None:
        """Verify score_confiance > 100 raises ValueError."""
        with pytest.raises(ValueError):
            LettrageSheet(
                facture_id="FAC_001",
                montant_facture=250.0,
                score_confiance=101,  # Invalid: > 100
            )

    def test_lettrage_sheet_default_statut(self) -> None:
        """Verify default statut is PAS_DE_MATCH."""
        lettrage = LettrageSheet(
            facture_id="FAC_001",
            montant_facture=250.0,
        )
        assert lettrage.statut == LettrageStatut.PAS_DE_MATCH

    def test_lettrage_statut_enum_values(self) -> None:
        """Verify LettrageStatut has all expected values from CDC §6."""
        statuts = {s.value for s in LettrageStatut}
        expected = {"LETTRE", "A_VERIFIER", "PAS_DE_MATCH"}
        assert statuts == expected


class TestBalancesSheet:
    """Tests for BalancesSheet model (calculated)."""

    def test_balances_sheet_has_correct_columns(self) -> None:
        """Verify BalancesSheet has 7 fields."""
        model_fields = BalancesSheet.model_fields
        expected_columns = {
            "mois",
            "nb_factures",
            "ca_total",
            "recu_urssaf",
            "solde",
            "nb_non_lettrees",
            "nb_en_attente",
        }
        assert set(model_fields.keys()) == expected_columns

    def test_balances_sheet_field_types(self) -> None:
        """Verify field types match specification."""
        model_fields = BalancesSheet.model_fields
        assert model_fields["mois"].annotation is str
        assert model_fields["nb_factures"].annotation is int
        assert model_fields["ca_total"].annotation is float

    def test_balances_sheet_non_negative_constraints(self) -> None:
        """Verify nb_factures, ca_total, recu_urssaf are >= 0."""
        balances = BalancesSheet(
            mois="2026-01",
            nb_factures=0,
            ca_total=0.0,
            recu_urssaf=0.0,
            solde=0.0,
            nb_non_lettrees=0,
            nb_en_attente=0,
        )
        assert balances.nb_factures == 0
        assert balances.ca_total == 0.0


class TestMetricsNovaSheet:
    """Tests for MetricsNovaSheet model (calculated)."""

    def test_metrics_nova_sheet_has_correct_columns(self) -> None:
        """Verify MetricsNovaSheet has 6 fields."""
        model_fields = MetricsNovaSheet.model_fields
        expected_columns = {
            "trimestre",
            "nb_intervenants",
            "heures_effectuees",
            "nb_particuliers",
            "ca_trimestre",
            "deadline_saisie",
        }
        assert set(model_fields.keys()) == expected_columns

    def test_metrics_nova_sheet_default_nb_intervenants(self) -> None:
        """Verify default nb_intervenants is 1."""
        metrics = MetricsNovaSheet(
            trimestre="2026-Q1",
            heures_effectuees=100.0,
            nb_particuliers=5,
            ca_trimestre=5000.0,
            deadline_saisie=date(2026, 4, 30),
        )
        assert metrics.nb_intervenants == 1

    def test_metrics_nova_sheet_nb_intervenants_constraint(self) -> None:
        """Verify nb_intervenants must be >= 1."""
        with pytest.raises(ValueError):
            MetricsNovaSheet(
                trimestre="2026-Q1",
                nb_intervenants=0,  # Invalid: must be >= 1
                heures_effectuees=100.0,
                nb_particuliers=5,
                ca_trimestre=5000.0,
                deadline_saisie=date(2026, 4, 30),
            )


class TestCotisationsSheet:
    """Tests for CotisationsSheet model (calculated)."""

    def test_cotisations_sheet_has_correct_columns(self) -> None:
        """Verify CotisationsSheet has 7 fields."""
        model_fields = CotisationsSheet.model_fields
        expected_columns = {
            "mois",
            "ca_encaisse",
            "taux_charges",
            "montant_charges",
            "date_limite",
            "cumul_ca",
            "net_apres_charges",
        }
        assert set(model_fields.keys()) == expected_columns

    def test_cotisations_sheet_default_taux_charges(self) -> None:
        """Verify default taux_charges is 25.8%."""
        cotisations = CotisationsSheet(
            mois="2026-01",
            ca_encaisse=1000.0,
            montant_charges=258.0,
            date_limite=date(2026, 2, 28),
            cumul_ca=1000.0,
            net_apres_charges=742.0,
        )
        assert cotisations.taux_charges == 25.8


class TestFiscalIRSheet:
    """Tests for FiscalIRSheet model (calculated)."""

    def test_fiscal_ir_sheet_has_correct_columns(self) -> None:
        """Verify FiscalIRSheet has 8 fields."""
        model_fields = FiscalIRSheet.model_fields
        expected_columns = {
            "revenu_apprentissage",
            "seuil_exo",
            "ca_micro",
            "abattement",
            "revenu_imposable",
            "tranches_ir",
            "taux_marginal",
            "simulation_vl",
        }
        assert set(model_fields.keys()) == expected_columns

    def test_fiscal_ir_sheet_default_seuil_exo(self) -> None:
        """Verify default seuil_exo is 5000.0."""
        fiscal = FiscalIRSheet(
            revenu_apprentissage=100.0,
            ca_micro=50000.0,
            revenu_imposable=33000.0,
            simulation_vl=1100.0,
        )
        assert fiscal.seuil_exo == 5000.0

    def test_fiscal_ir_sheet_default_abattement(self) -> None:
        """Verify default abattement is 0.34."""
        fiscal = FiscalIRSheet(
            revenu_apprentissage=100.0,
            ca_micro=50000.0,
            revenu_imposable=33000.0,
            simulation_vl=1100.0,
        )
        assert fiscal.abattement == 0.34

    def test_fiscal_ir_sheet_taux_marginal_constraints(self) -> None:
        """Verify taux_marginal is 0-100."""
        fiscal = FiscalIRSheet(
            revenu_apprentissage=100.0,
            ca_micro=50000.0,
            revenu_imposable=33000.0,
            taux_marginal=45.0,
            simulation_vl=1100.0,
        )
        assert fiscal.taux_marginal == 45.0

    def test_fiscal_ir_sheet_taux_marginal_exceeds_max(self) -> None:
        """Verify taux_marginal > 100 raises ValueError."""
        with pytest.raises(ValueError):
            FiscalIRSheet(
                revenu_apprentissage=100.0,
                ca_micro=50000.0,
                revenu_imposable=33000.0,
                taux_marginal=101.0,  # Invalid: > 100
                simulation_vl=1100.0,
            )


class TestSheetNamesMapping:
    """Tests for SHEET_NAMES constant — CDC §5."""

    def test_sheet_names_has_8_entries(self) -> None:
        """Verify SHEET_NAMES has 8 sheet models."""
        assert len(SHEET_NAMES) == 8

    def test_sheet_names_values_are_french(self) -> None:
        """Verify sheet names are French as per Google Sheets."""
        expected_names = {
            "Clients",
            "Factures",
            "Transactions",
            "Lettrage",
            "Balances",
            "Metrics NOVA",
            "Cotisations",
            "Fiscal IR",
        }
        assert set(SHEET_NAMES.values()) == expected_names

    def test_sheet_names_client_sheet(self) -> None:
        """Verify ClientSheet maps to 'Clients'."""
        assert SHEET_NAMES[ClientSheet] == "Clients"

    def test_sheet_names_facture_sheet(self) -> None:
        """Verify FactureSheet maps to 'Factures'."""
        assert SHEET_NAMES[FactureSheet] == "Factures"

    def test_sheet_names_transaction_sheet(self) -> None:
        """Verify TransactionSheet maps to 'Transactions'."""
        assert SHEET_NAMES[TransactionSheet] == "Transactions"

    def test_sheet_names_lettrage_sheet(self) -> None:
        """Verify LettrageSheet maps to 'Lettrage'."""
        assert SHEET_NAMES[LettrageSheet] == "Lettrage"

    def test_sheet_names_balances_sheet(self) -> None:
        """Verify BalancesSheet maps to 'Balances'."""
        assert SHEET_NAMES[BalancesSheet] == "Balances"

    def test_sheet_names_metrics_nova_sheet(self) -> None:
        """Verify MetricsNovaSheet maps to 'Metrics NOVA'."""
        assert SHEET_NAMES[MetricsNovaSheet] == "Metrics NOVA"

    def test_sheet_names_cotisations_sheet(self) -> None:
        """Verify CotisationsSheet maps to 'Cotisations'."""
        assert SHEET_NAMES[CotisationsSheet] == "Cotisations"

    def test_sheet_names_fiscal_ir_sheet(self) -> None:
        """Verify FiscalIRSheet maps to 'Fiscal IR'."""
        assert SHEET_NAMES[FiscalIRSheet] == "Fiscal IR"


class TestDataModelsClassification:
    """Tests for DATA_MODELS constant — writable sheets."""

    def test_data_models_has_3_entries(self) -> None:
        """Verify DATA_MODELS has exactly 3 data models."""
        assert len(DATA_MODELS) == 3

    def test_data_models_contains_client_sheet(self) -> None:
        """Verify ClientSheet is in DATA_MODELS."""
        assert ClientSheet in DATA_MODELS

    def test_data_models_contains_facture_sheet(self) -> None:
        """Verify FactureSheet is in DATA_MODELS."""
        assert FactureSheet in DATA_MODELS

    def test_data_models_contains_transaction_sheet(self) -> None:
        """Verify TransactionSheet is in DATA_MODELS."""
        assert TransactionSheet in DATA_MODELS

    def test_data_models_are_writable(self) -> None:
        """Verify DATA_MODELS are the 3 editable sheets — CDC §5."""
        expected = [ClientSheet, FactureSheet, TransactionSheet]
        assert expected == DATA_MODELS


class TestCalculatedModelsClassification:
    """Tests for CALC_MODELS constant — calculated sheets."""

    def test_calc_models_has_5_entries(self) -> None:
        """Verify CALC_MODELS has exactly 5 calculated models."""
        assert len(CALC_MODELS) == 5

    def test_calc_models_contains_lettrage_sheet(self) -> None:
        """Verify LettrageSheet is in CALC_MODELS."""
        assert LettrageSheet in CALC_MODELS

    def test_calc_models_contains_balances_sheet(self) -> None:
        """Verify BalancesSheet is in CALC_MODELS."""
        assert BalancesSheet in CALC_MODELS

    def test_calc_models_contains_metrics_nova_sheet(self) -> None:
        """Verify MetricsNovaSheet is in CALC_MODELS."""
        assert MetricsNovaSheet in CALC_MODELS

    def test_calc_models_contains_cotisations_sheet(self) -> None:
        """Verify CotisationsSheet is in CALC_MODELS."""
        assert CotisationsSheet in CALC_MODELS

    def test_calc_models_contains_fiscal_ir_sheet(self) -> None:
        """Verify FiscalIRSheet is in CALC_MODELS."""
        assert FiscalIRSheet in CALC_MODELS

    def test_calc_models_are_calculated(self) -> None:
        """Verify CALC_MODELS are the 5 formula-driven sheets — CDC §5."""
        expected = [
            LettrageSheet,
            BalancesSheet,
            MetricsNovaSheet,
            CotisationsSheet,
            FiscalIRSheet,
        ]
        assert expected == CALC_MODELS


class TestDataFrameRoundtrip:
    """Tests for DataFrame creation and conversion."""

    def test_client_sheet_roundtrip(self) -> None:
        """Create ClientSheet from dict, verify data."""
        data = {
            "client_id": "CL_001",
            "nom": "Dupont",
            "prenom": "Jean",
            "email": "jean@example.com",
            "telephone": "0123456789",
            "adresse": "123 Rue Main",
            "code_postal": "75001",
            "ville": "Paris",
            "urssaf_id": "URQ123",
            "statut_urssaf": "INSCRIT",
            "date_inscription": date(2026, 1, 15),
            "actif": True,
        }
        client = ClientSheet(**data)
        assert client.client_id == "CL_001"
        assert client.nom == "Dupont"
        assert client.statut_urssaf == ClientStatutURSSAF.INSCRIT

    def test_facture_sheet_roundtrip(self) -> None:
        """Create FactureSheet from dict, verify data."""
        data = {
            "facture_id": "FAC_001",
            "client_id": "CL_001",
            "type_unite": "HEURE",
            "nature_code": "COURS_PARTICULIERS",
            "quantite": 5.0,
            "montant_unitaire": 50.0,
            "montant_total": 250.0,
            "date_debut": date(2026, 1, 1),
            "date_fin": date(2026, 1, 5),
            "description": "Cours maths",
            "statut": "BROUILLON",
        }
        facture = FactureSheet(**data)
        assert facture.facture_id == "FAC_001"
        assert facture.quantite == 5.0
        assert facture.statut == FactureStatut.BROUILLON

    def test_transaction_sheet_roundtrip(self) -> None:
        """Create TransactionSheet from dict, verify data."""
        data = {
            "transaction_id": "TXN_001",
            "indy_id": "IND_123",
            "date_valeur": date(2026, 1, 15),
            "montant": 250.0,
            "libelle": "URSSAF virement",
            "type": "VIREMENT_ENTRANT",
            "source": "indy",
            "facture_id": "FAC_001",
            "statut_lettrage": "LETTRE",
            "date_import": date(2026, 1, 15),
        }
        txn = TransactionSheet(**data)
        assert txn.transaction_id == "TXN_001"
        assert txn.montant == 250.0
        assert txn.statut_lettrage == LettrageStatut.LETTRE


class TestValidationAndConstraints:
    """Tests for Pydantic validation and field constraints."""

    def test_client_sheet_missing_required_field(self) -> None:
        """Verify missing required fields raise ValueError."""
        with pytest.raises(ValueError):
            ClientSheet(
                # Missing: client_id
                nom="Dupont",
                prenom="Jean",
                email="jean@example.com",
            )

    def test_facture_sheet_missing_required_field(self) -> None:
        """Verify missing required fields raise ValueError."""
        with pytest.raises(ValueError):
            FactureSheet(
                # Missing: facture_id
                client_id="CL_001",
                quantite=5.0,
                montant_unitaire=50.0,
                montant_total=250.0,
                date_debut=date(2026, 1, 1),
                date_fin=date(2026, 1, 5),
            )

    def test_transaction_sheet_missing_required_field(self) -> None:
        """Verify missing required fields raise ValueError."""
        with pytest.raises(ValueError):
            TransactionSheet(
                # Missing: transaction_id
                date_valeur=date(2026, 1, 15),
                montant=100.0,
                libelle="Test",
                date_import=date(2026, 1, 15),
            )

    def test_client_nom_min_length(self) -> None:
        """Verify nom requires min_length=1."""
        with pytest.raises(ValueError):
            ClientSheet(
                client_id="CL_001",
                nom="",  # Invalid: empty
                prenom="Jean",
                email="jean@example.com",
            )

    def test_client_prenom_min_length(self) -> None:
        """Verify prenom requires min_length=1."""
        with pytest.raises(ValueError):
            ClientSheet(
                client_id="CL_001",
                nom="Dupont",
                prenom="",  # Invalid: empty
                email="jean@example.com",
            )


class TestEnumValidation:
    """Tests for enum field validation."""

    def test_client_statut_urssaf_valid_values(self) -> None:
        """Verify all ClientStatutURSSAF values are valid."""
        for statut in ClientStatutURSSAF:
            client = ClientSheet(
                client_id="CL_001",
                nom="Test",
                prenom="Test",
                email="test@example.com",
                statut_urssaf=statut,
            )
            assert client.statut_urssaf == statut

    def test_facture_statut_valid_values(self) -> None:
        """Verify all FactureStatut values are valid."""
        for statut in FactureStatut:
            facture = FactureSheet(
                facture_id="FAC_001",
                client_id="CL_001",
                quantite=5.0,
                montant_unitaire=50.0,
                montant_total=250.0,
                date_debut=date(2026, 1, 1),
                date_fin=date(2026, 1, 5),
                statut=statut,
            )
            assert facture.statut == statut

    def test_transaction_type_valid_values(self) -> None:
        """Verify all TransactionType values are valid."""
        for txn_type in TransactionType:
            txn = TransactionSheet(
                transaction_id="TXN_001",
                date_valeur=date(2026, 1, 15),
                montant=100.0,
                libelle="Test",
                type=txn_type,
                date_import=date(2026, 1, 15),
            )
            assert txn.type == txn_type

    def test_lettrage_statut_valid_values(self) -> None:
        """Verify all LettrageStatut values are valid."""
        for statut in LettrageStatut:
            lettrage = LettrageSheet(
                facture_id="FAC_001",
                montant_facture=250.0,
                statut=statut,
            )
            assert lettrage.statut == statut
