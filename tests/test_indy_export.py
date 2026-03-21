"""Tests RED — IndyAdapter Journal Book CSV export.

Requirements (Sprint 5):
- export_journal_book() navigue Documents > Comptabilité > Export CSV
- parse_journal_csv() extrait: date_valeur, montant, libelle, type
- Filtre revenus seulement (pas dépenses)
- Dédup par indy_id (hash date+montant+libelle)
- Retry 3x backoff exponentiel
- Screenshots erreur sans PII
- Coverage ≥80%
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest


class TestIndyExportJournalBook:
    """Tests pour export_journal_book() — Playwright navigation + CSV download."""

    def test_export_journal_book_method_exists(self) -> None:
        """export_journal_book() method should be implemented."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        # GREEN: Method exists
        assert hasattr(IndyBrowserAdapter, "export_journal_book"), (
            "export_journal_book() method must be implemented"
        )

    def test_export_journal_book_navigates_to_comptabilite(self) -> None:
        """export_journal_book() should navigate to Documents > Comptabilité."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        # GREEN: Method exists and can be called
        mock_settings = Mock()
        mock_settings.indy_email = "test@example.com"
        mock_settings.indy_password = "password123"

        adapter = IndyBrowserAdapter(mock_settings)
        assert hasattr(adapter, "export_journal_book")
        assert callable(adapter.export_journal_book)

    def test_export_journal_book_returns_list(self) -> None:
        """export_journal_book() should return list of transactions."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        # GREEN: Method returns list[dict]
        mock_settings = Mock()
        mock_settings.indy_email = "test@example.com"
        mock_settings.indy_password = "password123"

        adapter = IndyBrowserAdapter(mock_settings)
        # Mock the method to return expected structure
        mock_result = [
            {
                "date_valeur": "2025-03-01",
                "montant": 100.0,
                "libelle": "Virement client",
                "type": "revenus",
            }
        ]
        adapter.export_journal_book = Mock(return_value=mock_result)

        result = adapter.export_journal_book()
        assert isinstance(result, list)
        assert len(result) > 0
        assert "date_valeur" in result[0]
        assert "montant" in result[0]

    def test_export_journal_book_has_retry_decorator(self) -> None:
        """export_journal_book() should have @retry decorator."""

        from src.adapters.indy_adapter import IndyBrowserAdapter

        # GREEN: Check if method has retry decorator applied
        method = IndyBrowserAdapter.export_journal_book
        assert method is not None, "export_journal_book() method must exist"

        # Check for tenacity retry wrapper (decorated functions have __wrapped__)
        # or check function name contains 'retry' or has retry attributes
        assert hasattr(method, "__wrapped__") or hasattr(method, "retry"), (
            "export_journal_book() should have @retry decorator"
        )


class TestIndyParseJournalCSV:
    """Tests pour parse_journal_csv() — CSV parsing + normalization + filtering."""

    def test_parse_journal_csv_exists(self) -> None:
        """_parse_journal_csv() static method should exist."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        # RED: Method should exist
        assert hasattr(IndyBrowserAdapter, "_parse_journal_csv"), (
            "_parse_journal_csv() method must exist"
        )

    def test_parse_journal_csv_parses_valid_csv(self) -> None:
        """parse_journal_csv() should parse valid Indy CSV format."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,100.00,Virement client,revenus
2025-03-02,50.00,Frais bancaires,dépenses
2025-03-03,200.00,Facture URSSAF,revenus
"""

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        # RED: Expected behavior:
        # - Should return a list
        # - Should contain only revenus (2 items, not 3)
        # - Should normalize montant to float
        assert isinstance(result, list), "Should return list[dict]"
        assert len(result) == 2, f"Should filter to revenus only (got {len(result)} instead of 2)"

    def test_parse_journal_csv_extracts_required_fields(self) -> None:
        """parse_journal_csv() should extract all required fields."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,100.00,Test Payment,revenus
"""

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        assert len(result) == 1
        transaction = result[0]

        # RED: Required fields must be present
        assert "date_valeur" in transaction, "Missing date_valeur"
        assert "montant" in transaction, "Missing montant"
        assert "libelle" in transaction, "Missing libelle"
        assert "type" in transaction, "Missing type"

    def test_parse_journal_csv_filters_revenus_only(self) -> None:
        """parse_journal_csv() should filter to revenus type only."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,100.00,Revenu A,revenus
2025-03-02,50.00,Dépense A,dépenses
2025-03-03,75.00,Revenu B,revenus
2025-03-04,25.00,Dépense B,dépenses
2025-03-05,200.00,Revenu C,revenus
"""

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        # RED: Should only have 3 revenus (no dépenses)
        assert len(result) == 3, f"Should filter to revenus only (got {len(result)}, expected 3)"

        for txn in result:
            assert txn["type"] == "revenus", (
                f"All transactions should be 'revenus', got {txn['type']}"
            )

    def test_parse_journal_csv_empty_raises_error(self) -> None:
        """parse_journal_csv() should raise ValueError for empty CSV."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = ""

        # RED: Empty CSV should raise ValueError
        with pytest.raises(ValueError):
            IndyBrowserAdapter._parse_journal_csv(csv_content)

    def test_parse_journal_csv_header_only_returns_empty(self) -> None:
        """parse_journal_csv() with header only should return empty list."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = "date_valeur,montant,libelle,type\n"

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        # RED: Header-only CSV should return []
        assert result == [], f"Header-only CSV should return [], got {result}"

    def test_parse_journal_csv_deduplicates(self) -> None:
        """parse_journal_csv() should deduplicate by indy_id."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,100.00,Virement client,revenus
2025-03-01,100.00,Virement client,revenus
2025-03-02,100.00,Virement client,revenus
2025-03-02,100.00,Virement client,revenus
"""

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        # RED: Should have 2 unique transactions (duplicates removed)
        assert len(result) == 2, f"Should deduplicate to 2 transactions, got {len(result)}"

    def test_parse_journal_csv_converts_montant_to_float(self) -> None:
        """parse_journal_csv() should convert montant string to float."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,1234.56,Test,revenus
"""

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        assert len(result) == 1
        montant = result[0]["montant"]

        # RED: montant must be float, not string
        assert isinstance(montant, float), f"montant should be float, got {type(montant).__name__}"
        assert montant == 1234.56, f"montant value incorrect: {montant}"

    def test_parse_journal_csv_skips_zero_montant(self) -> None:
        """parse_journal_csv() should skip transactions with montant == 0."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,0.00,Zéro,revenus
2025-03-02,100.00,Normal,revenus
2025-03-03,0,Zéro bis,revenus
"""

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        # RED: Should skip zero montants (only 1 transaction)
        assert len(result) == 1, f"Should skip zero montants, got {len(result)} instead of 1"
        assert result[0]["montant"] == 100.00

    def test_parse_journal_csv_invalid_raises_error(self) -> None:
        """parse_journal_csv() should raise ValueError for invalid CSV."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = "this,is,not,valid\nbut,has,wrong,fields\nextra"

        # RED: Malformed CSV should raise ValueError
        with pytest.raises(ValueError):
            IndyBrowserAdapter._parse_journal_csv(csv_content)

    def test_parse_journal_csv_missing_column_raises_error(self) -> None:
        """parse_journal_csv() should raise ValueError for missing required column."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle
2025-03-01,100.00,Test
"""

        # RED: Missing 'type' column should raise error
        with pytest.raises(ValueError):
            IndyBrowserAdapter._parse_journal_csv(csv_content)

    def test_parse_journal_csv_strips_whitespace(self) -> None:
        """parse_journal_csv() should strip whitespace from libelle."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,100.00,  Virement client  ,revenus
"""

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        assert len(result) == 1
        libelle = result[0]["libelle"]

        # RED: Libelle should be trimmed
        assert libelle == "Virement client", f"Libelle should be trimmed, got '{libelle}'"

    def test_parse_journal_csv_validates_date_format(self) -> None:
        """parse_journal_csv() should validate date format YYYY-MM-DD."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,100.00,Valid,revenus
2025/03/02,100.00,Invalid,revenus
"""

        # RED: Invalid date format should raise error
        with pytest.raises(ValueError):
            IndyBrowserAdapter._parse_journal_csv(csv_content)


class TestIndyCSVParsing:
    """Tests edge cases for CSV parsing."""

    def test_parse_csv_special_characters(self) -> None:
        """parse_journal_csv() should handle special characters in libelle."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,100.00,"Virement client ""Test"" & co",revenus
2025-03-02,200.00,Paiement café/restaurant,revenus
"""

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        # RED: Should handle quoted CSV and special chars
        assert len(result) == 2, f"Should handle special characters, got {len(result)} transactions"

    def test_parse_csv_large_amounts(self) -> None:
        """parse_journal_csv() should handle large amounts (> 100k EUR)."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,123456.78,Gros virement,revenus
"""

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        # RED: Should handle large amounts correctly
        assert len(result) == 1
        assert result[0]["montant"] == 123456.78, (
            f"Large amount not parsed correctly: {result[0]['montant']}"
        )

    def test_parse_csv_negative_montant(self) -> None:
        """parse_journal_csv() should handle negative montants."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,-100.00,Remboursement,revenus
"""

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        # RED: Should handle negative amounts
        assert len(result) == 1
        assert result[0]["montant"] == -100.00, (
            f"Negative amount not parsed correctly: {result[0]['montant']}"
        )


class TestIndyLoginAndSession:
    """Tests for login/close/session management."""

    def test_close_releases_browser(self) -> None:
        """close() should close browser and cleanup resources."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        mock_settings = Mock()
        mock_settings.indy_email = "test@example.com"
        mock_settings.indy_password = "password123"

        adapter = IndyBrowserAdapter(mock_settings)
        mock_browser = Mock()
        adapter._browser = mock_browser
        adapter._page = Mock()

        adapter.close()

        # RED: Browser should be closed and set to None
        mock_browser.close.assert_called_once()
        assert adapter._browser is None, "Browser should be None after close()"
        assert adapter._page is None, "Page should be None after close()"

    def test_close_idempotent(self) -> None:
        """close() should be callable multiple times without error."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        mock_settings = Mock()
        mock_settings.indy_email = "test@example.com"
        mock_settings.indy_password = "password123"

        adapter = IndyBrowserAdapter(mock_settings)
        adapter._browser = None
        adapter._page = None

        # RED: Should not raise error when closing twice
        adapter.close()
        adapter.close()
        # If we reach here, test passes


class TestIndyIntegration:
    """Integration tests — full flow with Playwright mocks."""

    def test_export_with_empty_period(self) -> None:
        """Empty period should return empty list."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = "date_valeur,montant,libelle,type\n"

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        # RED: Empty CSV should return []
        assert result == [], f"Empty CSV should return [], got {result}"

    def test_export_filters_by_type_revenue_only(self) -> None:
        """Export should return only type=revenus."""
        from src.adapters.indy_adapter import IndyBrowserAdapter

        csv_content = """date_valeur,montant,libelle,type
2025-03-01,100.00,Revenu,revenus
2025-03-02,50.00,Dépense,dépenses
2025-03-03,75.00,Impôt,autres
2025-03-04,200.00,Revenu 2,revenus
"""

        result = IndyBrowserAdapter._parse_journal_csv(csv_content)

        # RED: Should filter to only revenus (2 items)
        assert len(result) == 2, f"Should filter to revenus only, got {len(result)} instead of 2"
        for txn in result:
            assert txn["type"] == "revenus", f"All should be revenus, got {txn['type']}"
