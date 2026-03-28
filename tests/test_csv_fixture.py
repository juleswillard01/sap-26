"""Tests for Indy Journal CSV fixture — MPP-24.

Validates structure, encoding, distribution, and coherence of
tests/fixtures/indy_journal_Q1_2026.csv against acceptance criteria.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import pytest

CSV_PATH = Path(__file__).parent / "fixtures" / "indy_journal_Q1_2026.csv"

# Expected columns in real Indy Journal export
EXPECTED_HEADERS = ["date_valeur", "montant", "libelle", "type"]

# Factures PAYE/RAPPROCHE from master_dataset — amounts the CSV must match
FACTURE_AMOUNTS: dict[str, float] = {
    "F012": 90.0,
    "F013": 75.0,
    "F014": 120.0,
    "F016": 80.0,
    "F017": 55.0,
    "F018": 100.0,
    "F023": 45.0,
}

# Payment dates for date coherence check (±5 days window)
FACTURE_PAYMENT_DATES: dict[str, str] = {
    "F012": "2026-02-10",
    "F013": "2026-02-20",
    "F014": "2026-03-05",
    "F016": "2026-01-15",
    "F017": "2026-02-05",
    "F018": "2026-02-25",
    "F023": "2026-01-25",
}


@pytest.fixture
def csv_content() -> str:
    """Load raw CSV content."""
    return CSV_PATH.read_text(encoding="utf-8")


@pytest.fixture
def csv_rows(csv_content: str) -> list[dict[str, str]]:
    """Parse CSV rows with semicolon delimiter."""
    reader = csv.DictReader(io.StringIO(csv_content), delimiter=";")
    return list(reader)


# ──────────────────────────────────────────────
# Structure
# ──────────────────────────────────────────────


class TestCSVStructure:
    """CSV file existence, encoding, headers."""

    def test_file_exists(self) -> None:
        assert CSV_PATH.exists(), f"CSV fixture not found: {CSV_PATH}"

    def test_encoding_utf8(self) -> None:
        raw = CSV_PATH.read_bytes()
        # No BOM
        assert not raw.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM detected"
        # Decodable as UTF-8
        raw.decode("utf-8")

    def test_separator_semicolon(self, csv_content: str) -> None:
        header_line = csv_content.split("\n")[0].strip()
        assert ";" in header_line, "Header must use semicolon separator"
        assert header_line.count(";") == len(EXPECTED_HEADERS) - 1

    def test_headers_match(self, csv_content: str) -> None:
        header_line = csv_content.split("\n")[0].strip()
        headers = [h.strip() for h in header_line.split(";")]
        assert headers == EXPECTED_HEADERS

    def test_row_count_40(self, csv_rows: list[dict[str, str]]) -> None:
        assert len(csv_rows) == 40, f"Expected 40 rows, got {len(csv_rows)}"

    def test_no_empty_rows(self, csv_rows: list[dict[str, str]]) -> None:
        for i, row in enumerate(csv_rows):
            assert row["date_valeur"].strip(), f"Row {i + 1}: empty date_valeur"
            assert row["montant"].strip(), f"Row {i + 1}: empty montant"
            assert row["libelle"].strip(), f"Row {i + 1}: empty libelle"
            assert row["type"].strip(), f"Row {i + 1}: empty type"


# ──────────────────────────────────────────────
# Distribution
# ──────────────────────────────────────────────


class TestCSVDistribution:
    """20 URSSAF, 10 divers, 5 orphelines, 5 doublons."""

    def test_urssaf_count_at_least_20(self, csv_rows: list[dict[str, str]]) -> None:
        urssaf = [r for r in csv_rows if "urssaf" in r["libelle"].lower()]
        assert len(urssaf) >= 20, f"URSSAF: {len(urssaf)}/20"

    def test_divers_count_at_least_10(self, csv_rows: list[dict[str, str]]) -> None:
        divers = [r for r in csv_rows if "urssaf" not in r["libelle"].lower()]
        assert len(divers) >= 10, f"Divers: {len(divers)}/10"

    def test_doublons_at_least_5(self, csv_rows: list[dict[str, str]]) -> None:
        """At least 5 rows share (date_valeur, montant, libelle) with another row."""
        seen: dict[str, int] = {}
        for row in csv_rows:
            key = f"{row['date_valeur']}|{row['montant']}|{row['libelle']}"
            seen[key] = seen.get(key, 0) + 1
        doublon_count = sum(count for count in seen.values() if count > 1)
        assert doublon_count >= 5, f"Doublons: {doublon_count}/5"

    def test_type_values_valid(self, csv_rows: list[dict[str, str]]) -> None:
        valid_types = {"revenus", "depenses", "prelevement"}
        for i, row in enumerate(csv_rows):
            assert row["type"].strip() in valid_types, f"Row {i + 1}: invalid type '{row['type']}'"

    def test_revenus_type_present(self, csv_rows: list[dict[str, str]]) -> None:
        revenus = [r for r in csv_rows if r["type"].strip() == "revenus"]
        assert len(revenus) >= 25, f"revenus type: {len(revenus)}, expected >=25"

    def test_non_revenus_present(self, csv_rows: list[dict[str, str]]) -> None:
        non_rev = [r for r in csv_rows if r["type"].strip() != "revenus"]
        assert len(non_rev) >= 5, f"non-revenus: {len(non_rev)}, expected >=5"


# ──────────────────────────────────────────────
# Dates
# ──────────────────────────────────────────────


class TestCSVDates:
    """Dates in Q1 2026, valid format."""

    def test_dates_format_yyyy_mm_dd(self, csv_rows: list[dict[str, str]]) -> None:
        for i, row in enumerate(csv_rows):
            d = row["date_valeur"].strip()
            try:
                date.fromisoformat(d)
            except ValueError:
                pytest.fail(f"Row {i + 1}: invalid date format '{d}'")

    def test_dates_in_q1_2026(self, csv_rows: list[dict[str, str]]) -> None:
        q1_start = date(2026, 1, 1)
        q1_end = date(2026, 3, 31)
        for i, row in enumerate(csv_rows):
            d = date.fromisoformat(row["date_valeur"].strip())
            assert q1_start <= d <= q1_end, f"Row {i + 1}: date {d} outside Q1 2026"

    def test_dates_spread_across_months(self, csv_rows: list[dict[str, str]]) -> None:
        months = {date.fromisoformat(r["date_valeur"].strip()).month for r in csv_rows}
        assert {1, 2, 3} == months, f"Expected months 1,2,3 got {months}"


# ──────────────────────────────────────────────
# Montants
# ──────────────────────────────────────────────


class TestCSVMontants:
    """Amounts are valid floats, coherent with master dataset factures."""

    def test_montants_parseable(self, csv_rows: list[dict[str, str]]) -> None:
        for i, row in enumerate(csv_rows):
            try:
                float(row["montant"].strip())
            except ValueError:
                pytest.fail(f"Row {i + 1}: unparseable montant '{row['montant']}'")

    def test_facture_amounts_present(self, csv_rows: list[dict[str, str]]) -> None:
        """Each PAYE/RAPPROCHE facture amount must appear in CSV revenus rows."""
        revenus_amounts = [
            float(r["montant"].strip()) for r in csv_rows if r["type"].strip() == "revenus"
        ]
        for fid, amount in FACTURE_AMOUNTS.items():
            assert amount in revenus_amounts, f"{fid} amount {amount} not found in CSV revenus"

    def test_montant_range_realistic(self, csv_rows: list[dict[str, str]]) -> None:
        """Amounts should be in realistic range (no absurdly large values)."""
        for i, row in enumerate(csv_rows):
            m = float(row["montant"].strip())
            assert -5000 <= m <= 5000, f"Row {i + 1}: montant {m} outside realistic range"

    def test_negative_amounts_only_non_revenus(self, csv_rows: list[dict[str, str]]) -> None:
        """Negative amounts should only appear in non-revenus rows."""
        for i, row in enumerate(csv_rows):
            m = float(row["montant"].strip())
            if m < 0:
                assert row["type"].strip() != "revenus", (
                    f"Row {i + 1}: negative montant in revenus type"
                )


# ──────────────────────────────────────────────
# Coherence dates paiement
# ──────────────────────────────────────────────


class TestCSVDateCoherence:
    """CSV transaction dates within ±5 days of facture payment dates."""

    def test_matched_amounts_near_payment_dates(self, csv_rows: list[dict[str, str]]) -> None:
        """For each facture with a match, a CSV row with exact amount must be
        within ±5 days of the payment date."""
        revenus = [r for r in csv_rows if r["type"].strip() == "revenus"]
        for fid, amount in FACTURE_AMOUNTS.items():
            payment_date = date.fromisoformat(FACTURE_PAYMENT_DATES[fid])
            matching = [r for r in revenus if abs(float(r["montant"].strip()) - amount) < 0.01]
            if not matching:
                continue
            # At least one matching amount must be within ±5 days
            within_window = [
                r
                for r in matching
                if abs((date.fromisoformat(r["date_valeur"].strip()) - payment_date).days) <= 5
            ]
            assert within_window, (
                f"{fid}: amount {amount} found but no date within ±5 days of {payment_date}"
            )


# ──────────────────────────────────────────────
# Libelles
# ──────────────────────────────────────────────


class TestCSVLibelles:
    """Realistic labels."""

    def test_urssaf_libelles_varied(self, csv_rows: list[dict[str, str]]) -> None:
        """URSSAF labels should have variety (not all identical)."""
        urssaf_libelles = {
            r["libelle"].strip() for r in csv_rows if "urssaf" in r["libelle"].lower()
        }
        assert len(urssaf_libelles) >= 5, (
            f"Only {len(urssaf_libelles)} unique URSSAF labels, expected >=5"
        )

    def test_no_empty_libelles(self, csv_rows: list[dict[str, str]]) -> None:
        for i, row in enumerate(csv_rows):
            assert len(row["libelle"].strip()) >= 3, f"Row {i + 1}: libelle too short"
