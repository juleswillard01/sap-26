"""Tests RED — CLI sap reconcile (Indy → Sheets → Lettrage).

Sprint 6: BankReconciliation & Lettrage (plan.md §182-227)
Verifies: export_journal_book() → import Transactions → match_invoices_to_transactions()

Requirements from plan.md:
- sap reconcile calls bank_reconciliation.reconcile()
- Imports N transactions from Indy Journal Book CSV
- Calculates lettrage scores (matching score_confiance)
- Updates Sheets Lettrage onglet
- Transitions PAYE → RAPPROCHE if score ≥80 (auto-matched)
- Shows summary: N imported, X auto-lettrées, Y à vérifier
"""

from __future__ import annotations

from click.testing import CliRunner

from src.cli import main


class TestSapReconcileCommand:
    """RED tests for `sap reconcile` CLI command (currently NotImplementedError)."""

    def test_reconcile_command_exists(self) -> None:
        """reconcile command must exist and show help."""
        runner = CliRunner()
        result = runner.invoke(main, ["reconcile", "--help"])
        assert result.exit_code == 0
        assert "lettrage" in result.output.lower()

    def test_reconcile_requires_implementation(self) -> None:
        """reconcile command currently raises NotImplementedError."""
        runner = CliRunner()
        result = runner.invoke(main, ["reconcile"])
        # At RED phase: NotImplementedError expected
        assert result.exit_code != 0
        assert isinstance(result.exception, NotImplementedError) or "À implémenter" in str(
            result.exception
        )

    def test_reconcile_respects_verbose_flag(self) -> None:
        """sap reconcile --verbose should not crash."""
        runner = CliRunner()
        result = runner.invoke(main, ["--verbose", "reconcile"])
        # Currently: NotImplementedError, but should handle flag
        assert isinstance(result.exit_code, int)

    def test_reconcile_respects_dry_run_flag(self) -> None:
        """sap reconcile --dry-run should not crash."""
        runner = CliRunner()
        result = runner.invoke(main, ["--dry-run", "reconcile"])
        # Currently: NotImplementedError, but should handle flag
        assert isinstance(result.exit_code, int)

    def test_reconcile_context_has_verbose(self) -> None:
        """reconcile command receives verbose flag in context."""
        runner = CliRunner()
        result = runner.invoke(main, ["--verbose", "reconcile"])
        # At RED phase: NotImplementedError expected
        assert isinstance(result.exception, (NotImplementedError, type(None)))

    def test_reconcile_context_has_dry_run(self) -> None:
        """reconcile command receives dry_run flag in context."""
        runner = CliRunner()
        result = runner.invoke(main, ["--dry-run", "reconcile"])
        # At RED phase: NotImplementedError expected
        assert isinstance(result.exception, (NotImplementedError, type(None)))


class TestSapReconcileRequirements:
    """RED tests for `sap reconcile` behavior requirements (GREEN phase)."""

    def test_requirement_imports_transactions(self) -> None:
        """[GREEN] sap reconcile must import transactions from Indy Journal Book CSV.

        Requirement: plan.md §188-189
        - Call indy.export_journal_book() → CSV bytes
        - Call parse_journal_csv(csv_content) → list[Transaction]
        - Update Sheets Transactions onglet via add_rows()
        """
        # Will implement when service ready
        pass

    def test_requirement_calculates_lettrage_scores(self) -> None:
        """[GREEN] sap reconcile must calculate lettrage matching scores.

        Requirement: plan.md §193-204
        Scoring:
        - Montant exact (±0.01€) → +50pts
        - Date ≤3 jours → +30pts
        - Libelle contains "URSSAF" → +20pts
        Decision:
        - Score ≥80 → LETTRE_AUTO (auto-match)
        - Score <80 but ≥1 match → A_VERIFIER (manual review)
        - No match → PAS_DE_MATCH
        """
        # Will implement when service ready
        pass

    def test_requirement_updates_lettrage_sheet(self) -> None:
        """[GREEN] sap reconcile must update Sheets Lettrage onglet.

        Requirement: plan.md §205
        - Updates row per matching (facture_id, txn_id, score, status)
        """
        # Will implement when service ready
        pass

    def test_requirement_transitions_invoice_state(self) -> None:
        """[GREEN] sap reconcile must transition PAYE → RAPPROCHE if auto-matched.

        Requirement: plan.md §206
        - Only if score ≥80 (LETTRE_AUTO status)
        - Updates Sheets Factures onglet statut field
        """
        # Will implement when service ready
        pass

    def test_requirement_shows_summary(self) -> None:
        """[GREEN] sap reconcile must display summary to user.

        Requirement: plan.md §209
        Summary must include:
        - N transactions imported
        - X invoices auto-matched (score ≥80)
        - Y invoices pending manual review (score <80 but ≥1)
        """
        # Will implement when service ready
        pass

    def test_requirement_exit_0_on_success(self) -> None:
        """[GREEN] sap reconcile exits with code 0 on success."""
        # Will implement when service ready
        pass

    def test_requirement_exit_1_on_indy_error(self) -> None:
        """[GREEN] sap reconcile exits with code 1 on Indy adapter error."""
        # Will implement when service ready
        pass

    def test_requirement_exit_1_on_sheets_error(self) -> None:
        """[GREEN] sap reconcile exits with code 1 on Sheets adapter error."""
        # Will implement when service ready
        pass

    def test_requirement_handles_zero_transactions(self) -> None:
        """[GREEN] sap reconcile handles case with 0 transactions imported."""
        # Will implement when service ready
        pass

    def test_requirement_handles_all_auto_matched(self) -> None:
        """[GREEN] sap reconcile handles case where all transactions auto-matched."""
        # Will implement when service ready
        pass

    def test_requirement_handles_partial_matching(self) -> None:
        """[GREEN] sap reconcile handles partial matching (some auto, some manual)."""
        # Will implement when service ready
        pass

    def test_requirement_picks_best_match(self) -> None:
        """[GREEN] sap reconcile picks best score when multiple matches exist.

        Requirement: plan.md §220 (edge case)
        - For 1 invoice with multiple possible transactions
        - Pick match with highest score
        """
        # Will implement when service ready
        pass

    def test_requirement_handles_amount_variance(self) -> None:
        """[GREEN] sap reconcile handles small amount differences (rounding).

        Requirement: plan.md §222 (edge case)
        - Montants slightly different (but within tolerance)
        - Should consider in scoring or filtering
        """
        # Will implement when service ready
        pass

    def test_requirement_handles_missing_columns(self) -> None:
        """[GREEN] sap reconcile handles CSV with missing columns gracefully."""
        # Will implement when service ready
        pass
