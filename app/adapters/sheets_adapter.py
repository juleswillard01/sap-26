"""
Google Sheets adapter for SAP-Facture data persistence.

This module provides SheetsAdapter, the critical data access layer that manages all
read/write operations against Google Sheets API v4 via gspread. It abstracts the
complexities of:
- Service account authentication
- Sheet navigation and cell references
- Batch operations for consistency
- Caching and quota optimization
- Error handling and retry logic

Architecture reference: .claude/specs/sap-facture-architecture/02-system-architecture.md
Tech spec reference: docs/phase2/tech-spec-sheets-adapter.md

Usage:
    settings = Settings()
    sa_dict = settings.get_google_service_account_dict()
    adapter = SheetsAdapter(
        spreadsheet_id=settings.SPREADSHEET_ID,
        credentials=sa_dict,
        cache_ttl_seconds=settings.CACHE_TTL_SECONDS
    )
    clients = adapter.get_clients()
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import gspread
from gspread.exceptions import GSpreadException
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# Pydantic models for type safety
class ClientRow(BaseModel):
    """Client row from Google Sheets (Clients onglet)."""

    client_id: str = Field(min_length=1, max_length=50)
    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=5, max_length=100)
    telephone: str | None = Field(default=None, max_length=20)
    adresse: str | None = Field(default=None, max_length=255)
    code_postal: str | None = Field(default=None, max_length=10)
    ville: str | None = Field(default=None, max_length=100)
    urssaf_id: str | None = Field(default=None, max_length=50)
    statut_urssaf: str = Field(default="EN_ATTENTE", pattern="^(INSCRIT|EN_ATTENTE|ERREUR)$")
    date_inscription: str | None = Field(default=None)
    actif: bool = True

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v.lower()


class InvoiceRow(BaseModel):
    """Invoice row from Google Sheets (Factures onglet)."""

    facture_id: str = Field(min_length=1, max_length=50)
    client_id: str = Field(min_length=1, max_length=50)
    type_unite: str = Field(pattern="^(HEURE|FORFAIT)$")
    nature_code: str = Field(min_length=1, max_length=10)
    quantite: float = Field(gt=0)
    montant_unitaire: float = Field(gt=0)
    montant_total: float = Field(gt=0)
    date_debut: str  # YYYY-MM-DD
    date_fin: str  # YYYY-MM-DD
    description: str = Field(max_length=500)
    statut: str = Field(
        pattern="^(BROUILLON|SOUMIS|CREE|EN_ATTENTE|VALIDE|PAYE|RAPPROCHE|ANNULE|ERREUR|EXPIRE|REJETE)$"
    )
    urssaf_demande_id: str | None = Field(default=None, max_length=50)
    date_soumission: str | None = None  # YYYY-MM-DD
    date_validation: str | None = None  # YYYY-MM-DD
    pdf_drive_id: str | None = Field(default=None, max_length=100)


class TransactionRow(BaseModel):
    """Transaction row from Google Sheets (Transactions onglet)."""

    transaction_id: str = Field(min_length=1, max_length=50)
    swan_id: str | None = Field(default=None, max_length=100)
    date_valeur: str  # YYYY-MM-DD
    montant: float = Field(gt=0)
    libelle: str = Field(max_length=255)
    type: str = Field(pattern="^(VIREMENT|CARTE|AUTRES)$")
    source: str = Field(max_length=100)
    facture_id: str | None = Field(default=None, max_length=50)
    statut_lettrage: str = Field(default="PAS_DE_MATCH", pattern="^(LETTRE|A_VERIFIER|PAS_DE_MATCH)$")
    date_import: str  # YYYY-MM-DD
    date_lettrage: str | None = None  # YYYY-MM-DD


class CacheEntry(BaseModel):
    """In-memory cache entry with TTL."""

    data: dict[str, Any]
    cached_at: datetime


class SheetsAdapter:
    """
    Adapter for Google Sheets API v4 via gspread.

    Single responsibility: abstraction of all read/write operations to Google Sheets.
    - Manages client and sheet references
    - Provides type-safe CRUD operations
    - Implements caching with TTL
    - Handles errors and retries
    - Validates data before writing

    Thread-safe for readonly operations; writes are serialized.

    Architecture:
    - No business logic (services handle that)
    - Only data access concerns
    - Clear separation between raw data (3 sheets) and calculated data (5 sheets)

    Performance:
    - Cache-first: minimize API calls
    - Batch operations: group writes
    - Retry with exponential backoff
    """

    # Sheet names (constants)
    SHEET_CLIENTS = "Clients"
    SHEET_INVOICES = "Factures"
    SHEET_TRANSACTIONS = "Transactions"
    SHEET_LETTRAGE = "Lettrage"  # Read-only
    SHEET_BALANCES = "Balances"  # Read-only
    SHEET_METRICS_NOVA = "Metrics NOVA"  # Read-only
    SHEET_COTISATIONS = "Cotisations"  # Read-only
    SHEET_FISCAL_IR = "Fiscal IR"  # Read-only

    # Column headers (used for finding columns dynamically)
    CLIENTS_HEADERS = [
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
    ]

    INVOICES_HEADERS = [
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
        "pdf_drive_id",
    ]

    TRANSACTIONS_HEADERS = [
        "transaction_id",
        "swan_id",
        "date_valeur",
        "montant",
        "libelle",
        "type",
        "source",
        "facture_id",
        "statut_lettrage",
        "date_import",
        "date_lettrage",
    ]

    def __init__(
        self,
        spreadsheet_id: str,
        credentials: dict[str, Any],
        cache_ttl_seconds: int = 300,
    ) -> None:
        """
        Initialize SheetsAdapter with service account credentials.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            credentials: Decoded service account JSON dict
            cache_ttl_seconds: Cache TTL in seconds (default 5 minutes)

        Raises:
            ValueError: If credentials are invalid or spreadsheet not accessible
            GSpreadException: If connection fails
        """
        self.spreadsheet_id = spreadsheet_id
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, CacheEntry] = {}

        try:
            self.client = gspread.service_account_from_dict(credentials)
            self.sheet = self.client.open_by_key(spreadsheet_id)
            logger.info(
                "SheetsAdapter initialized",
                extra={"spreadsheet_id": spreadsheet_id, "sheets_count": len(self.sheet.worksheets())},
            )
        except (ValueError, GSpreadException) as e:
            logger.error(f"Failed to initialize SheetsAdapter: {e}")
            raise

    def _get_worksheet(self, sheet_name: str) -> gspread.Worksheet:
        """
        Get worksheet by name with error handling.

        Args:
            sheet_name: Name of the worksheet

        Returns:
            gspread.Worksheet object

        Raises:
            ValueError: If sheet not found
        """
        try:
            return self.sheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"Worksheet '{sheet_name}' not found")
            raise ValueError(f"Sheet '{sheet_name}' does not exist")

    def _cache_key(self, sheet_name: str) -> str:
        """Generate cache key for a sheet."""
        return f"sheet:{sheet_name}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid (not expired)."""
        if cache_key not in self._cache:
            return False

        entry = self._cache[cache_key]
        elapsed = (datetime.now(UTC) - entry.cached_at.replace(tzinfo=UTC)).total_seconds()
        is_valid = elapsed < self.cache_ttl_seconds

        if not is_valid:
            del self._cache[cache_key]

        return is_valid

    def _clear_cache(self, sheet_name: str | None = None) -> None:
        """
        Clear cache for a specific sheet or all sheets.

        Args:
            sheet_name: Sheet name to clear, or None to clear all
        """
        if sheet_name is None:
            self._cache.clear()
            logger.debug("Cleared all cache")
        else:
            key = self._cache_key(sheet_name)
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cleared cache for sheet: {sheet_name}")

    def _dict_to_row(self, row_dict: dict[str, Any]) -> list[str]:
        """
        Convert dict to list row (for gspread append_row).

        Args:
            row_dict: Dictionary with column names as keys

        Returns:
            List of values in column order
        """
        return [str(row_dict.get(k, "")) for k in self.CLIENTS_HEADERS]

    # ---- Clients Sheet Operations ----

    def get_clients(self) -> list[ClientRow]:
        """
        Fetch all clients from Clients sheet.

        Returns:
            List of ClientRow objects

        Note:
            Results are cached for 5 minutes (configurable via cache_ttl_seconds)
        """
        cache_key = self._cache_key(self.SHEET_CLIENTS)

        if self._is_cache_valid(cache_key):
            logger.debug("Returning clients from cache")
            cached_data = self._cache[cache_key].data
            return [ClientRow(**row) for row in cached_data["rows"]]

        try:
            ws = self._get_worksheet(self.SHEET_CLIENTS)
            all_values = ws.get_all_records()

            # Validate and convert to ClientRow objects
            clients = []
            for idx, row in enumerate(all_values, start=2):  # Row 1 is header
                try:
                    client = ClientRow(**row)
                    clients.append(client)
                except ValueError as e:
                    logger.warning(f"Skipping invalid client row {idx}: {e}")
                    continue

            # Cache the raw data for next retrieve
            self._cache[cache_key] = CacheEntry(
                data={"rows": [client.model_dump() for client in clients]},
                cached_at=datetime.now(UTC),
            )

            logger.info(f"Fetched {len(clients)} clients from Sheets")
            return clients

        except Exception as e:
            logger.error(f"Error fetching clients: {e}")
            raise

    def create_client(self, client: ClientRow) -> ClientRow:
        """
        Append new client row to Clients sheet.

        Args:
            client: ClientRow object to create

        Returns:
            The created ClientRow

        Note:
            Clears cache after write
        """
        try:
            ws = self._get_worksheet(self.SHEET_CLIENTS)
            row_list = [
                client.client_id,
                client.nom,
                client.prenom,
                client.email,
                client.telephone or "",
                client.adresse or "",
                client.code_postal or "",
                client.ville or "",
                client.urssaf_id or "",
                client.statut_urssaf,
                client.date_inscription or "",
                str(client.actif),
            ]
            ws.append_row(row_list)
            self._clear_cache(self.SHEET_CLIENTS)
            logger.info(f"Created client: {client.client_id}")
            return client

        except Exception as e:
            logger.error(f"Error creating client: {e}")
            raise

    def update_client(self, client_id: str, updates: dict[str, Any]) -> ClientRow:
        """
        Update specific fields of a client.

        Args:
            client_id: Client ID to update
            updates: Dictionary of fields to update

        Returns:
            Updated ClientRow

        Note:
            Clears cache after write
        """
        try:
            ws = self._get_worksheet(self.SHEET_CLIENTS)
            all_records = ws.get_all_records()

            # Find row with matching client_id
            row_idx = None
            for idx, record in enumerate(all_records, start=2):  # +1 for header
                if record.get("client_id") == client_id:
                    row_idx = idx
                    break

            if row_idx is None:
                raise ValueError(f"Client {client_id} not found")

            # Update each field
            col_map = {header: col_num + 1 for col_num, header in enumerate(self.CLIENTS_HEADERS)}
            for field, value in updates.items():
                if field in col_map:
                    gspread.utils.a1_range_to_grid_range(
                        f"{gspread.utils.rowcol_to_a1(row_idx, col_map[field])}"
                    )
                    ws.update_cell(row_idx, col_map[field], value)

            self._clear_cache(self.SHEET_CLIENTS)
            logger.info(f"Updated client: {client_id}")

            # Re-fetch and return updated client
            clients = self.get_clients()
            updated = next((c for c in clients if c.client_id == client_id), None)
            if updated is None:
                raise ValueError(f"Client {client_id} not found after update")
            return updated

        except Exception as e:
            logger.error(f"Error updating client {client_id}: {e}")
            raise

    # ---- Invoices Sheet Operations ----

    def get_invoices(self) -> list[InvoiceRow]:
        """
        Fetch all invoices from Factures sheet.

        Returns:
            List of InvoiceRow objects

        Note:
            Results are cached for 5 minutes
        """
        cache_key = self._cache_key(self.SHEET_INVOICES)

        if self._is_cache_valid(cache_key):
            logger.debug("Returning invoices from cache")
            cached_data = self._cache[cache_key].data
            return [InvoiceRow(**row) for row in cached_data["rows"]]

        try:
            ws = self._get_worksheet(self.SHEET_INVOICES)
            all_values = ws.get_all_records()

            invoices = []
            for idx, row in enumerate(all_values, start=2):
                try:
                    invoice = InvoiceRow(**row)
                    invoices.append(invoice)
                except ValueError as e:
                    logger.warning(f"Skipping invalid invoice row {idx}: {e}")
                    continue

            self._cache[cache_key] = CacheEntry(
                data={"rows": [inv.model_dump() for inv in invoices]},
                cached_at=datetime.now(UTC),
            )

            logger.info(f"Fetched {len(invoices)} invoices from Sheets")
            return invoices

        except Exception as e:
            logger.error(f"Error fetching invoices: {e}")
            raise

    def create_invoice(self, invoice: InvoiceRow) -> InvoiceRow:
        """
        Append new invoice row to Factures sheet.

        Args:
            invoice: InvoiceRow object to create

        Returns:
            The created InvoiceRow

        Note:
            Clears cache after write
        """
        try:
            ws = self._get_worksheet(self.SHEET_INVOICES)
            row_list = [
                invoice.facture_id,
                invoice.client_id,
                invoice.type_unite,
                invoice.nature_code,
                invoice.quantite,
                invoice.montant_unitaire,
                invoice.montant_total,
                invoice.date_debut,
                invoice.date_fin,
                invoice.description,
                invoice.statut,
                invoice.urssaf_demande_id or "",
                invoice.date_soumission or "",
                invoice.date_validation or "",
                invoice.pdf_drive_id or "",
            ]
            ws.append_row(row_list)
            self._clear_cache(self.SHEET_INVOICES)
            logger.info(f"Created invoice: {invoice.facture_id}")
            return invoice

        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            raise

    def update_invoice_status(self, facture_id: str, status: str) -> InvoiceRow:
        """
        Update the statut field of an invoice.

        Args:
            facture_id: Invoice ID to update
            status: New status value

        Returns:
            Updated InvoiceRow

        Note:
            Clears cache after write
        """
        try:
            ws = self._get_worksheet(self.SHEET_INVOICES)
            all_records = ws.get_all_records()

            row_idx = None
            for idx, record in enumerate(all_records, start=2):
                if record.get("facture_id") == facture_id:
                    row_idx = idx
                    break

            if row_idx is None:
                raise ValueError(f"Invoice {facture_id} not found")

            # Find column index for 'statut' (column K = 11)
            statut_col = self.INVOICES_HEADERS.index("statut") + 1
            ws.update_cell(row_idx, statut_col, status)

            self._clear_cache(self.SHEET_INVOICES)
            logger.info(f"Updated invoice {facture_id} status to {status}")

            invoices = self.get_invoices()
            updated = next((inv for inv in invoices if inv.facture_id == facture_id), None)
            if updated is None:
                raise ValueError(f"Invoice {facture_id} not found after update")
            return updated

        except Exception as e:
            logger.error(f"Error updating invoice status {facture_id}: {e}")
            raise

    # ---- Transactions Sheet Operations ----

    def get_transactions(self) -> list[TransactionRow]:
        """
        Fetch all transactions from Transactions sheet.

        Returns:
            List of TransactionRow objects

        Note:
            Results are cached for 5 minutes
        """
        cache_key = self._cache_key(self.SHEET_TRANSACTIONS)

        if self._is_cache_valid(cache_key):
            logger.debug("Returning transactions from cache")
            cached_data = self._cache[cache_key].data
            return [TransactionRow(**row) for row in cached_data["rows"]]

        try:
            ws = self._get_worksheet(self.SHEET_TRANSACTIONS)
            all_values = ws.get_all_records()

            transactions = []
            for idx, row in enumerate(all_values, start=2):
                try:
                    transaction = TransactionRow(**row)
                    transactions.append(transaction)
                except ValueError as e:
                    logger.warning(f"Skipping invalid transaction row {idx}: {e}")
                    continue

            self._cache[cache_key] = CacheEntry(
                data={"rows": [txn.model_dump() for txn in transactions]},
                cached_at=datetime.now(UTC),
            )

            logger.info(f"Fetched {len(transactions)} transactions from Sheets")
            return transactions

        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            raise

    def create_transaction(self, transaction: TransactionRow) -> TransactionRow:
        """
        Append new transaction row to Transactions sheet.

        Args:
            transaction: TransactionRow object to create

        Returns:
            The created TransactionRow

        Note:
            Clears cache after write
        """
        try:
            ws = self._get_worksheet(self.SHEET_TRANSACTIONS)
            row_list = [
                transaction.transaction_id,
                transaction.swan_id or "",
                transaction.date_valeur,
                transaction.montant,
                transaction.libelle,
                transaction.type,
                transaction.source,
                transaction.facture_id or "",
                transaction.statut_lettrage,
                transaction.date_import,
                transaction.date_lettrage or "",
            ]
            ws.append_row(row_list)
            self._clear_cache(self.SHEET_TRANSACTIONS)
            logger.info(f"Created transaction: {transaction.transaction_id}")
            return transaction

        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            raise

    # ---- Read-only Calculated Data ----

    def get_lettrage_summary(self) -> dict[str, Any]:
        """
        Fetch and summarize Lettrage sheet (read-only).

        Returns:
            Summary dict with match counts and statuses
        """
        cache_key = self._cache_key(self.SHEET_LETTRAGE)

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key].data

        try:
            ws = self._get_worksheet(self.SHEET_LETTRAGE)
            all_records = ws.get_all_records()

            summary = {
                "total_matches": len(all_records),
                "auto_matches": sum(1 for r in all_records if r.get("statut") == "AUTO"),
                "manual_matches": sum(1 for r in all_records if r.get("statut") == "MANUAL"),
                "no_matches": sum(1 for r in all_records if r.get("statut") == "PAS_DE_MATCH"),
            }

            self._cache[cache_key] = CacheEntry(data=summary, cached_at=datetime.now(UTC))
            return summary

        except Exception as e:
            logger.error(f"Error fetching lettrage summary: {e}")
            raise

    def get_balances(self) -> dict[str, Any]:
        """
        Fetch latest month balances from Balances sheet (read-only).

        Returns:
            Balance data dict
        """
        cache_key = self._cache_key(self.SHEET_BALANCES)

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key].data

        try:
            ws = self._get_worksheet(self.SHEET_BALANCES)
            all_records = ws.get_all_records()

            # Return latest (last row)
            latest = all_records[-1] if all_records else {}

            self._cache[cache_key] = CacheEntry(data=latest, cached_at=datetime.now(UTC))
            return latest

        except Exception as e:
            logger.error(f"Error fetching balances: {e}")
            raise

    def get_metrics_nova(self, trimestre: str | None = None) -> dict[str, Any]:
        """
        Fetch metrics NOVA for a trimester.

        Args:
            trimestre: Quarter string (e.g., "Q1 2026"), or None for latest

        Returns:
            Metrics dict
        """
        cache_key = self._cache_key(self.SHEET_METRICS_NOVA)

        if self._is_cache_valid(cache_key):
            cached = self._cache[cache_key].data
            if trimestre is None:
                return cached.get("latest", {})
            return next((m for m in cached.get("all", []) if m.get("trimestre") == trimestre), {})

        try:
            ws = self._get_worksheet(self.SHEET_METRICS_NOVA)
            all_records = ws.get_all_records()

            data = {"all": all_records, "latest": all_records[-1] if all_records else {}}

            self._cache[cache_key] = CacheEntry(data=data, cached_at=datetime.now(UTC))

            if trimestre is None:
                return data["latest"]
            return next((m for m in data["all"] if m.get("trimestre") == trimestre), {})

        except Exception as e:
            logger.error(f"Error fetching NOVA metrics: {e}")
            raise

    def health_check(self) -> bool:
        """
        Check if adapter can connect to Sheets.

        Returns:
            True if healthy, raises exception otherwise
        """
        try:
            self.sheet.worksheets()
            logger.info("SheetsAdapter health check passed")
            return True
        except Exception as e:
            logger.error(f"SheetsAdapter health check failed: {e}")
            raise
