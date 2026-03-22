"""Lettrage automatique factures ↔ transactions — CDC §5.3."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.models.invoice import InvoiceStatus
from src.models.transaction import LettrageResult, LettrageStatus, compute_matching_score

if TYPE_CHECKING:
    from src.adapters.indy_adapter import IndyBrowserAdapter
    from src.adapters.sheets_adapter import SheetsAdapter

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Service de rapprochement bancaire : Indy → lettrage → Sheets."""

    def __init__(
        self,
        indy_adapter: IndyBrowserAdapter,
        sheets_adapter: SheetsAdapter,
    ) -> None:
        """Initialise le service avec les adapteurs.

        Args:
            indy_adapter: Adapteur Indy pour exporter les transactions.
            sheets_adapter: Adapteur Sheets pour lire/écrire les données.
        """
        self._indy = indy_adapter
        self._sheets = sheets_adapter

    def reconcile(self) -> dict[str, int]:
        """Exécute le workflow complet de rapprochement.

        Étapes :
        1. Export des transactions depuis Indy
        2. Déduplication par indy_id
        3. Import des nouvelles transactions dans Sheets
        4. Scoring et lettrage des factures PAYE
        5. Transition PAYE → RAPPROCHE pour LETTRE_AUTO

        Returns:
            Dictionnaire résumé :
            - transactions_imported: Nombre de transactions importées
            - lettrage_updated: Nombre de lettrages enregistrés
            - auto_matched: Nombre de matches LETTRE_AUTO
            - to_verify: Nombre de matches A_VERIFIER
        """
        result = {
            "transactions_imported": 0,
            "lettrage_updated": 0,
            "auto_matched": 0,
            "to_verify": 0,
        }

        try:
            # 1. Export transactions depuis Indy
            indy_txns = self._indy.export_journal_csv()

            if not indy_txns:
                logger.info("Aucune transaction à importer")
                return result

            # 2. Préparer et dédupliquer les transactions
            transactions_to_add = self._prepare_transactions(indy_txns)

            # 3. Importer les transactions dans Sheets
            if transactions_to_add:
                self._sheets.add_transactions(transactions_to_add)
                result["transactions_imported"] = len(transactions_to_add)
                logger.info("Transactions importées: %d", len(transactions_to_add))

            # 4. Lettrage des factures PAYE
            lettrage_results = self._match_invoices_with_transactions(
                transactions_to_add + self._get_existing_transactions()
            )

            if lettrage_results:
                result["lettrage_updated"] = len(lettrage_results)
                result["auto_matched"] = sum(
                    1 for lr in lettrage_results if lr.statut == LettrageStatus.LETTRE_AUTO
                )
                result["to_verify"] = sum(
                    1 for lr in lettrage_results if lr.statut == LettrageStatus.A_VERIFIER
                )

                # 5. Transition PAYE → RAPPROCHE pour LETTRE_AUTO
                for lettrage_result in lettrage_results:
                    if lettrage_result.statut == LettrageStatus.LETTRE_AUTO:
                        self._sheets.update_invoice_status(
                            lettrage_result.facture_id,
                            InvoiceStatus.RAPPROCHE,
                        )
                        logger.info(
                            "Invoice %s transitioned to RAPPROCHE",
                            lettrage_result.facture_id,
                        )

        except Exception as e:
            logger.error("Erreur lors du rapprochement: %s", e, exc_info=True)
            raise

        return result

    def _prepare_transactions(
        self,
        indy_txns: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Prépare les transactions pour l'import (déduplication, conversion).

        Args:
            indy_txns: Transactions brutes depuis Indy.

        Returns:
            Liste des transactions prêtes à importer.
        """
        existing_txns = self._sheets.get_all_transactions()

        # Handle both DataFrame and list (for mocks in tests)
        if isinstance(existing_txns, list):
            existing_indy_ids = set(t.get("indy_id", "") for t in existing_txns)
        else:
            # DataFrame case
            existing_indy_ids = set(existing_txns["indy_id"].to_list())

        prepared = []
        seen = set()

        for txn in indy_txns:
            indy_id = txn.get("id", "")

            # Ignorer si déjà existant
            if indy_id in existing_indy_ids or indy_id in seen:
                continue

            seen.add(indy_id)

            # Convertir au format attendu
            prepared_txn = {
                "transaction_id": indy_id,
                "indy_id": indy_id,
                "date_valeur": txn.get("date", ""),
                "montant": float(txn.get("amount", 0)),
                "libelle": txn.get("label", ""),
                "type": txn.get("type", ""),
                "source": "indy",
            }

            prepared.append(prepared_txn)

        return prepared

    def _get_existing_transactions(self) -> list[dict[str, Any]]:
        """Récupère les transactions existantes depuis Sheets.

        Returns:
            Liste des transactions existantes en format dict.
        """
        try:
            txns = self._sheets.get_all_transactions()
            # Handle both DataFrame and list (for mocks in tests)
            if isinstance(txns, list):
                return txns
            if hasattr(txns, "is_empty") and txns.is_empty():
                return []
            if hasattr(txns, "to_dicts"):
                return txns.to_dicts()  # type: ignore[no-any-return]
            return []
        except Exception as e:
            logger.warning("Erreur lors de la lecture des transactions: %s", e)
            return []

    def _match_invoices_with_transactions(
        self,
        transactions: list[dict[str, Any]],
    ) -> list[LettrageResult]:
        """Effectue le matching entre factures PAYE et transactions.

        Args:
            transactions: Transactions disponibles.

        Returns:
            Liste des résultats de lettrage.
        """
        results = []

        try:
            # Récupérer les factures PAYE
            invoices_data = self._sheets.get_all_invoices()

            # Handle both DataFrame and list (for mocks in tests)
            invoices_list: list[dict[str, Any]] = []
            if isinstance(invoices_data, list):
                if not invoices_data:
                    return results
                # Convert Invoice objects to dicts if needed
                for inv in invoices_data:
                    if hasattr(inv, "model_dump"):
                        inv_dict = inv.model_dump()
                        # Add montant_total property if it exists
                        if hasattr(inv, "montant_total"):
                            inv_dict["montant_total"] = inv.montant_total
                        invoices_list.append(inv_dict)
                    else:
                        invoices_list.append(inv)
            else:
                # DataFrame case
                if invoices_data.is_empty():
                    return results
                invoices_list = invoices_data.to_dicts()  # type: ignore[no-any-return]

            # Filtrer pour PAYE uniquement
            paye_invoices = [
                inv for inv in invoices_list if inv.get("statut") == InvoiceStatus.PAYE
            ]

            if not paye_invoices:
                logger.info("Aucune facture PAYE pour le lettrage")
                return results

            # Matcher chaque transaction avec les factures
            matched_txn_ids = set()

            for txn in transactions:
                # Support both "date_valeur" and "date" fields
                txn_date_str = txn.get("date_valeur") or txn.get("date", "")
                txn_amount = float(txn.get("montant") or txn.get("amount") or 0.0)
                txn_label = txn.get("libelle") or txn.get("label") or ""
                txn_id = txn.get("transaction_id") or txn.get("id", "")

                if not txn_id or txn_id in matched_txn_ids:
                    continue

                # Convertir la date transaction
                try:
                    if isinstance(txn_date_str, str):
                        txn_date = datetime.fromisoformat(txn_date_str).date()
                    else:
                        txn_date = txn_date_str
                except (ValueError, AttributeError):
                    continue

                # Trouver le meilleur match parmi les factures
                best_match = None
                best_score = 0
                best_inv_amount = 0.0
                best_inv_date = None

                for inv in paye_invoices:
                    inv_amount = inv.get("montant_total", 0.0)
                    inv_id = inv.get("facture_id", "")

                    # Use transaction date as reference (invoices don't have payment date)
                    inv_date = txn_date

                    # Calculer le score
                    score = compute_matching_score(
                        invoice_amount=inv_amount,
                        transaction_amount=txn_amount,
                        invoice_payment_date=inv_date,
                        transaction_date=txn_date,
                        transaction_label=txn_label,
                    )

                    if score > best_score:
                        best_score = score
                        best_match = inv_id
                        best_inv_amount = inv_amount
                        best_inv_date = inv_date

                # Enregistrer le résultat si trouvé
                if best_match and best_inv_date is not None:
                    lettrage_result = LettrageResult(
                        facture_id=best_match,
                        transaction_id=txn_id,
                        score=best_score,
                        montant_exact=abs(txn_amount - best_inv_amount) < 0.01,
                        date_proche=abs((txn_date - best_inv_date).days) <= 3,
                        libelle_urssaf="urssaf" in txn_label.lower(),
                    )
                    results.append(lettrage_result)
                    matched_txn_ids.add(txn_id)

        except Exception as e:
            logger.error("Erreur lors du matching: %s", e, exc_info=True)

        return results


def compute_lettrage_score(
    facture_montant: float,
    facture_date_paiement: str,
    transaction_montant: float,
    transaction_date: str,
    transaction_libelle: str,
) -> LettrageResult:
    """Calcule le score de confiance pour le lettrage.

    Scoring :
    - Montant exact (100% facture) = +50
    - Date < 3 jours = +30
    - Libellé contient 'URSSAF' = +20

    Returns:
        Résultat du scoring avec statut.
    """
    raise NotImplementedError("À implémenter — CDC §5.3")
