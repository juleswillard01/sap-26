"""Tests for master_dataset.json fixture — MPP-21.

Validates structure, FK coherence, state coverage, scoring edge cases,
and expected_results accuracy.
"""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from src.models.client import Client, ClientStatus
from src.models.invoice import InvoiceStatus
from src.models.transaction import LettrageStatus, compute_matching_score

FIXTURES_DIR = Path(__file__).parent / "fixtures"
MASTER_FILE = FIXTURES_DIR / "master_dataset.json"


@pytest.fixture
def dataset() -> dict[str, Any]:
    """Load master dataset."""
    return json.loads(MASTER_FILE.read_text())


@pytest.fixture
def clients(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    return dataset["clients"]


@pytest.fixture
def factures(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    return dataset["factures"]


@pytest.fixture
def transactions(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    return dataset["transactions"]


@pytest.fixture
def expected(dataset: dict[str, Any]) -> dict[str, Any]:
    return dataset["expected_results"]


# ── T1: Counts ──


class TestCounts:
    def test_clients_count_is_10(self, clients: list[dict]) -> None:
        assert len(clients) == 10

    def test_factures_count_is_25(self, factures: list[dict]) -> None:
        assert len(factures) == 25

    def test_transactions_count_is_40(self, transactions: list[dict]) -> None:
        assert len(transactions) == 40


# ── T1: Client distribution ──


class TestClientDistribution:
    def test_clients_6_actifs_inscrit(self, clients: list[dict]) -> None:
        actifs = [c for c in clients if c["actif"] and c["statut_urssaf"] == "INSCRIT"]
        assert len(actifs) == 6

    def test_clients_2_inactifs(self, clients: list[dict]) -> None:
        inactifs = [c for c in clients if not c["actif"]]
        assert len(inactifs) == 2

    def test_clients_2_en_inscription(self, clients: list[dict]) -> None:
        en_inscription = [
            c
            for c in clients
            if c["actif"] and c["statut_urssaf"] == "EN_ATTENTE" and c["urssaf_id"] is None
        ]
        assert len(en_inscription) == 2


# ── T1: ID format & uniqueness ──


class TestIDFormats:
    def test_client_ids_format(self, clients: list[dict]) -> None:
        for c in clients:
            assert re.match(r"^C\d{3}$", c["client_id"]), f"Bad client_id: {c['client_id']}"

    def test_facture_ids_format(self, factures: list[dict]) -> None:
        for f in factures:
            assert re.match(r"^F\d{3}$", f["facture_id"]), f"Bad facture_id: {f['facture_id']}"

    def test_transaction_ids_format(self, transactions: list[dict]) -> None:
        for t in transactions:
            assert re.match(r"^TRX-\d{3}$", t["transaction_id"]), (
                f"Bad transaction_id: {t['transaction_id']}"
            )

    def test_client_ids_unique(self, clients: list[dict]) -> None:
        ids = [c["client_id"] for c in clients]
        assert len(ids) == len(set(ids))

    def test_facture_ids_unique(self, factures: list[dict]) -> None:
        ids = [f["facture_id"] for f in factures]
        assert len(ids) == len(set(ids))

    def test_transaction_ids_unique(self, transactions: list[dict]) -> None:
        ids = [t["transaction_id"] for t in transactions]
        assert len(ids) == len(set(ids))


# ── T1: FK coherence ──


class TestFKCoherence:
    def test_facture_client_ids_exist(self, clients: list[dict], factures: list[dict]) -> None:
        client_ids = {c["client_id"] for c in clients}
        for f in factures:
            assert f["client_id"] in client_ids, (
                f"FK broken: {f['facture_id']}.client_id={f['client_id']}"
            )

    def test_transaction_facture_ids_exist_or_null(
        self, factures: list[dict], transactions: list[dict]
    ) -> None:
        facture_ids = {f["facture_id"] for f in factures}
        for t in transactions:
            if t["facture_id"] is not None:
                assert t["facture_id"] in facture_ids, (
                    f"FK broken: {t['transaction_id']}.facture_id={t['facture_id']}"
                )


# ── T1: Montant coherence ──


class TestMontants:
    def test_montant_total_equals_quantite_times_unitaire(self, factures: list[dict]) -> None:
        for f in factures:
            expected = f["quantite"] * f["montant_unitaire"]
            assert abs(f["montant_total"] - expected) < 0.01, (
                f"{f['facture_id']}: {f['montant_total']} != "
                f"{f['quantite']} x {f['montant_unitaire']}"
            )

    def test_montants_realistes_sap(self, factures: list[dict]) -> None:
        for f in factures:
            assert 0 < f["montant_total"] <= 300, (
                f"{f['facture_id']}: montant {f['montant_total']} hors range"
            )


# ── T1: Date coherence ──


class TestDates:
    def test_dates_chronological(self, factures: list[dict]) -> None:
        date_fields = ["date_soumission", "date_validation", "date_paiement", "date_rapprochement"]
        for f in factures:
            dates = [f.get(d) for d in date_fields if f.get(d) is not None]
            for i in range(len(dates) - 1):
                assert dates[i] <= dates[i + 1], f"{f['facture_id']}: {dates[i]} > {dates[i + 1]}"

    def test_dates_q1_2026(self, factures: list[dict], transactions: list[dict]) -> None:
        all_dates: list[str] = []
        for f in factures:
            for d in [
                "date_debut",
                "date_fin",
                "date_soumission",
                "date_validation",
                "date_paiement",
            ]:
                if f.get(d):
                    all_dates.append(f[d])
        for t in transactions:
            if t.get("date_valeur"):
                all_dates.append(t["date_valeur"])

        for d in all_dates:
            assert d.startswith("2026-0"), f"Date hors Q1 2026: {d}"


# ── T1: State coverage ──


class TestStateCoverage:
    def test_all_11_invoice_statuts_present(self, factures: list[dict]) -> None:
        statuts = {f["statut"] for f in factures}
        expected_statuts = {s.value for s in InvoiceStatus}
        missing = expected_statuts - statuts
        assert not missing, f"Missing statuts: {missing}"

    def test_lettrage_statuts_coverage(self, transactions: list[dict]) -> None:
        statuts = {t["statut_lettrage"] for t in transactions}
        # At minimum NON_LETTRE, LETTRE_AUTO, A_VERIFIER, PAS_DE_MATCH
        expected_statuts = {"NON_LETTRE", "LETTRE_AUTO", "A_VERIFIER", "PAS_DE_MATCH"}
        missing = expected_statuts - statuts
        assert not missing, f"Missing lettrage statuts: {missing}"


# ── T1: Transaction distribution ──


class TestTransactionDistribution:
    def test_20_urssaf_matchable(self, transactions: list[dict]) -> None:
        urssaf = [t for t in transactions if "urssaf" in t["libelle"].lower()]
        assert len(urssaf) >= 20, f"Only {len(urssaf)} URSSAF transactions"

    def test_10_divers(self, transactions: list[dict]) -> None:
        divers = [t for t in transactions if "urssaf" not in t["libelle"].lower()]
        assert len(divers) >= 10, f"Only {len(divers)} divers transactions"

    def test_5_orphelines(self, transactions: list[dict]) -> None:
        orphelines = [t for t in transactions if t["statut_lettrage"] == "PAS_DE_MATCH"]
        assert len(orphelines) >= 5, f"Only {len(orphelines)} orphelines"

    def test_5_doublons_potentiels(self, transactions: list[dict]) -> None:
        """At least 5 transactions share (indy_id, montant, date_valeur) with another."""
        seen: dict[str, int] = {}
        for t in transactions:
            key = f"{t['indy_id']}|{t['montant']}|{t['date_valeur']}"
            seen[key] = seen.get(key, 0) + 1
        doublons = sum(count for count in seen.values() if count > 1)
        assert doublons >= 5, f"Only {doublons} doublon transactions"


# ── T1: Enum validity ──


class TestEnumValidity:
    def test_client_statuts_valid(self, clients: list[dict]) -> None:
        valid = {s.value for s in ClientStatus}
        for c in clients:
            assert c["statut_urssaf"] in valid, f"Bad statut: {c['statut_urssaf']}"

    def test_facture_statuts_valid(self, factures: list[dict]) -> None:
        valid = {s.value for s in InvoiceStatus}
        for f in factures:
            assert f["statut"] in valid, f"Bad statut: {f['statut']}"

    def test_transaction_lettrage_valid(self, transactions: list[dict]) -> None:
        valid = {s.value for s in LettrageStatus}
        for t in transactions:
            assert t["statut_lettrage"] in valid, f"Bad statut: {t['statut_lettrage']}"


# ── T1: Pydantic model acceptance ──


class TestPydanticModels:
    def test_clients_parse_as_pydantic(self, clients: list[dict]) -> None:
        for c in clients:
            Client(**c)

    def test_factures_have_required_fields(self, factures: list[dict]) -> None:
        required = {
            "facture_id",
            "client_id",
            "quantite",
            "montant_unitaire",
            "montant_total",
            "statut",
        }
        for f in factures:
            missing = required - set(f.keys())
            assert not missing, f"{f['facture_id']} missing fields: {missing}"


# ── T4: Lettrage scoring verification ──


class TestLettrageScoring:
    def test_expected_lettrage_scores_match_computed(
        self, factures: list[dict], transactions: list[dict], expected: dict[str, Any]
    ) -> None:
        """Recalculate lettrage scores and compare to expected_results."""
        lettrage = expected["lettrage"]
        txn_map = {t["transaction_id"]: t for t in transactions}
        fac_map = {f["facture_id"]: f for f in factures}

        for entry in lettrage:
            fac = fac_map[entry["facture_id"]]
            if entry["txn_id"] is None:
                assert entry["score_confiance"] == 0
                continue

            txn = txn_map[entry["txn_id"]]
            computed = compute_matching_score(
                invoice_amount=fac["montant_total"],
                transaction_amount=txn["montant"],
                invoice_payment_date=date.fromisoformat(fac["date_paiement"]),
                transaction_date=date.fromisoformat(txn["date_valeur"]),
                transaction_label=txn["libelle"],
            )
            assert computed == entry["score_confiance"], (
                f"{entry['facture_id']}↔{entry['txn_id']}: "
                f"computed={computed} != expected={entry['score_confiance']}"
            )

    def test_edge_case_score_exactly_80(
        self, factures: list[dict], transactions: list[dict], expected: dict[str, Any]
    ) -> None:
        """At least one lettrage entry with score exactly 80 (LETTRE_AUTO threshold)."""
        lettrage = expected["lettrage"]
        scores = [e["score_confiance"] for e in lettrage]
        assert 80 in scores, f"No score==80 found in lettrage. Scores: {sorted(set(scores))}"

    def test_edge_case_score_below_80(self, expected: dict[str, Any]) -> None:
        """At least one lettrage entry with score < 80 (A_VERIFIER)."""
        lettrage = expected["lettrage"]
        below_80 = [e for e in lettrage if 0 < e["score_confiance"] < 80]
        assert len(below_80) >= 1, "No A_VERIFIER score (0 < score < 80) found"

    def test_edge_case_score_100(self, expected: dict[str, Any]) -> None:
        """At least one lettrage entry with score 100 (perfect match)."""
        lettrage = expected["lettrage"]
        scores = [e["score_confiance"] for e in lettrage]
        assert 100 in scores, "No perfect score (100) found"


# ── T4: Expected results coherence ──


class TestExpectedResults:
    def test_expected_results_has_required_keys(self, expected: dict[str, Any]) -> None:
        required = {"lettrage", "balances_mensuelles", "nova_q1", "cotisations", "coherence"}
        missing = required - set(expected.keys())
        assert not missing, f"Missing expected_results keys: {missing}"

    def test_coherence_flags_all_true(self, expected: dict[str, Any]) -> None:
        coherence = expected["coherence"]
        for key, val in coherence.items():
            assert val is True, f"coherence.{key} is {val}"

    def test_cotisations_taux_charges(self, expected: dict[str, Any]) -> None:
        for cot in expected["cotisations"]:
            assert abs(cot["montant_charges"] - cot["ca_encaisse"] * 0.258) < 0.01, (
                f"Cotisations {cot['mois']}: charges mismatch"
            )

    def test_balances_solde_coherent(self, expected: dict[str, Any]) -> None:
        for bal in expected["balances_mensuelles"]:
            assert abs(bal["solde"] - (bal["ca_total"] - bal["recu_urssaf"])) < 0.01, (
                f"Balance {bal['mois']}: solde mismatch"
            )
