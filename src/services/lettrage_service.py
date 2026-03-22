"""Service de lettrage — Matching factures ↔ transactions bancaires (CDC §3.2).

Responsabilités :
- Charger factures PAYE et transactions depuis Sheets
- Calculer score de confiance pour chaque paire candidat
- Sélectionner le meilleur match par fenêtre ±5 jours
- Persister résultats (facture_id, statut_lettrage)
"""

from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING, Any

from src.models.transaction import LettrageResult, LettrageStatus, compute_matching_score

if TYPE_CHECKING:
    from src.adapters.sheets_adapter import SheetsAdapter

logger = logging.getLogger(__name__)


class LettrageService:
    """Service de lettrage bancaire — Appairage factures ↔ transactions."""

    def __init__(self, sheets_adapter: SheetsAdapter) -> None:
        """Initialise le service de lettrage.

        Args:
            sheets_adapter: Adaptateur pour lecture/écriture Google Sheets
        """
        self._sheets = sheets_adapter

    def compute_matches(
        self, invoices: list[dict[str, Any]], transactions: list[dict[str, Any]]
    ) -> list[LettrageResult]:
        """Calcule les appairages factures ↔ transactions.

        Algorithme (CDC §3.2) :
        1. Filtrer factures avec statut="PAYE"
        2. Pour chaque facture, trouver transactions dans fenêtre ±5 jours
        3. Scorer chaque candidat (montant, date, libellé)
        4. Sélectionner meilleur match (score max)
        5. Marquer transaction utilisée (chaque transaction max une facture)

        Args:
            invoices: Liste factures avec colonnes facture_id, statut, montant_total, date_paiement
            transactions: Liste transactions avec date_valeur, montant, libelle

        Returns:
            Liste LettrageResult (une par facture PAYE, avec ou sans match)
        """
        # Filtrer factures PAYE seulement
        paye_invoices = [inv for inv in invoices if inv.get("statut") == "PAYE"]

        if not paye_invoices:
            logger.info("No PAYE invoices to match")
            return []

        results: list[LettrageResult] = []
        used_txn_ids: set[str] = set()  # Track matched transactions

        for invoice in paye_invoices:
            facture_id = invoice.get("facture_id", "")
            montant_facture = float(invoice.get("montant_total", 0.0))
            date_paiement_str = invoice.get("date_paiement", "")

            # Parse payment date
            try:
                date_paiement = date.fromisoformat(date_paiement_str)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Invalid date_paiement for {facture_id}",
                    extra={"value": date_paiement_str, "error": str(e)},
                )
                # No match if payment date is invalid
                results.append(
                    LettrageResult(
                        facture_id=facture_id,
                        transaction_id=None,
                        score=0,
                        montant_exact=False,
                        date_proche=False,
                        libelle_urssaf=False,
                    )
                )
                continue

            # Consider all transactions (scoring naturally prioritizes closer dates)
            candidates: list[tuple[dict[str, Any], int]] = []

            for transaction in transactions:
                txn_id = transaction.get("transaction_id", "")

                # Skip if already used for another invoice
                if txn_id in used_txn_ids:
                    continue

                date_valeur_str = transaction.get("date_valeur", "")

                # Parse transaction date
                try:
                    date_valeur = date.fromisoformat(date_valeur_str)
                except (ValueError, TypeError):
                    continue

                montant_txn = float(transaction.get("montant", 0.0))
                libelle = transaction.get("libelle", "")

                # Score this candidate
                score = compute_matching_score(
                    invoice_amount=montant_facture,
                    transaction_amount=montant_txn,
                    invoice_payment_date=date_paiement,
                    transaction_date=date_valeur,
                    transaction_label=libelle,
                )

                # Only consider candidates with positive score (within ±5 day window)
                if score > 0:
                    candidates.append((transaction, score))

            # Select best match (highest score, break ties by earliest date)
            if candidates:
                # Sort by score descending, then by date ascending (earliest first)
                best_txn, best_score = max(
                    candidates,
                    key=lambda x: (
                        x[1],  # score (descending via max)
                        -date.fromisoformat(
                            x[0].get("date_valeur", "")
                        ).toordinal(),  # date (ascending)
                    ),
                )
                transaction_id = best_txn.get("transaction_id", "")
                used_txn_ids.add(transaction_id)  # Mark as used

                # Compute boolean flags based on scoring components
                montant_exact = abs(montant_facture - float(best_txn.get("montant", 0.0))) < 0.01
                date_proche = (
                    abs((date.fromisoformat(best_txn.get("date_valeur", "")) - date_paiement).days)
                    <= 3
                )
                libelle_urssaf = "urssaf" in best_txn.get("libelle", "").lower()

                result = LettrageResult(
                    facture_id=facture_id,
                    transaction_id=transaction_id,
                    score=best_score,
                    montant_exact=montant_exact,
                    date_proche=date_proche,
                    libelle_urssaf=libelle_urssaf,
                )
                results.append(result)
            else:
                # No candidates found, return PAS_DE_MATCH
                results.append(
                    LettrageResult(
                        facture_id=facture_id,
                        transaction_id=None,
                        score=0,
                        montant_exact=False,
                        date_proche=False,
                        libelle_urssaf=False,
                    )
                )

        logger.info(
            "Computed matches",
            extra={
                "total_paye": len(paye_invoices),
                "with_match": sum(1 for r in results if r.transaction_id is not None),
                "lettre_auto": sum(1 for r in results if r.statut == LettrageStatus.LETTRE_AUTO),
                "a_verifier": sum(1 for r in results if r.statut == LettrageStatus.A_VERIFIER),
                "pas_de_match": sum(1 for r in results if r.statut == LettrageStatus.PAS_DE_MATCH),
            },
        )

        return results

    def apply_matches(self, matches: list[LettrageResult]) -> int:
        """Applique les résultats du lettrage à Google Sheets.

        Pour chaque match avec score ≥80 (LETTRE_AUTO) :
        - Met à jour transaction.facture_id
        - Met à jour transaction.statut_lettrage = LETTRE_AUTO
        - Met à jour facture.statut = RAPPROCHE

        Pour matches avec score <80 (A_VERIFIER) :
        - Met à jour transaction.statut_lettrage = A_VERIFIER

        Args:
            matches: Liste LettrageResult à appliquer

        Returns:
            Nombre de transactions mises à jour
        """
        if not matches:
            logger.info("No matches to apply")
            return 0

        updated_count = 0

        for match in matches:
            # Only update if a match was found
            if match.transaction_id is None:
                continue

            try:
                # Update transaction with facture_id and statut_lettrage
                updates: dict[str, str] = {
                    "facture_id": match.facture_id,
                    "statut_lettrage": str(match.statut),
                }
                self._sheets.update_transaction(match.transaction_id, updates)
                updated_count += 1

                # If LETTRE_AUTO, also transition invoice to RAPPROCHE
                if match.statut == LettrageStatus.LETTRE_AUTO:
                    self._sheets.update_invoice_status(match.facture_id, "RAPPROCHE")
                    logger.info(
                        "Applied match (LETTRE_AUTO)",
                        extra={
                            "facture_id": match.facture_id,
                            "transaction_id": match.transaction_id,
                            "score": match.score,
                        },
                    )
                else:
                    logger.info(
                        "Applied match (A_VERIFIER)",
                        extra={
                            "facture_id": match.facture_id,
                            "transaction_id": match.transaction_id,
                            "score": match.score,
                        },
                    )

            except Exception as e:
                logger.error(
                    "Failed to apply match",
                    extra={
                        "facture_id": match.facture_id,
                        "transaction_id": match.transaction_id,
                        "error": str(e),
                    },
                    exc_info=True,
                )
                raise

        logger.info(
            "Applied matches",
            extra={"total_applied": updated_count},
        )

        return updated_count
