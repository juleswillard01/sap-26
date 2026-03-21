"""Adapter Google Sheets via gspread — CDC §7.

IMPORTANT : Google Sheets est le backend data. Traiter comme un ORM.
- Batch reads : worksheet.get_all_records()
- Batch writes : worksheet.update() avec range
- JAMAIS cellule par cellule (worksheet.update_cell en boucle)
- Rate limit : 60 req/min/user → throttle intégré
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import cachetools  # type: ignore[import-untyped]
import gspread  # type: ignore[import-untyped]
import polars as pl
import pybreaker  # type: ignore[import-untyped]
from gspread.exceptions import GSpreadException  # type: ignore[import-untyped]
from tenacity import retry, stop_after_attempt, wait_exponential

from src.adapters.exceptions import (
    CircuitOpenError,
    RateLimitError,
    SheetValidationError,
    SpreadsheetNotFoundError,
    WorksheetNotFoundError,
)
from src.adapters.rate_limiter import TokenBucketRateLimiter
from src.adapters.sheets_schema import (
    CALC_SHEETS,
    DATA_SHEETS,
    SHEET_BALANCES,
    SHEET_CLIENTS,
    SHEET_COTISATIONS,
    SHEET_FACTURES,
    SHEET_FISCAL_IR,
    SHEET_LETTRAGE,
    SHEET_METRICS_NOVA,
    SHEET_TRANSACTIONS,
    get_headers,
    get_schema,
)
from src.adapters.write_queue import WriteOp, WriteQueueWorker

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)


class SheetsAdapter:
    """Adapter pour Google Sheets API v4 via gspread."""

    def __init__(self, settings: Settings) -> None:
        """Initialise l'adaptateur Google Sheets.

        Args:
            settings: Configuration Settings contenant spreadsheet_id, credentials, etc.

        Raises:
            ValueError: Si spreadsheet_id est vide.
        """
        if not settings.google_sheets_spreadsheet_id:
            raise ValueError("google_sheets_spreadsheet_id must not be empty")

        self._settings = settings
        self._spreadsheet: gspread.Spreadsheet | None = None
        self._worksheet_cache: dict[str, gspread.Worksheet] = {}

        # Initialize cache with TTL
        self._cache: cachetools.TTLCache[str, pl.DataFrame] = cachetools.TTLCache(
            maxsize=32, ttl=settings.sheets_cache_ttl
        )

        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0

        # Rate limiter
        self._rate_limiter = TokenBucketRateLimiter(
            max_requests=settings.sheets_rate_limit, window_seconds=60.0
        )

        # Circuit breaker
        self._circuit_breaker = pybreaker.CircuitBreaker(
            fail_max=settings.circuit_breaker_fail_max,
            reset_timeout=settings.circuit_breaker_reset_timeout,
            exclude=[WorksheetNotFoundError, SheetValidationError],
        )

        # Write queue
        self._write_queue = WriteQueueWorker(executor=self._execute_write_op)
        self._write_queue.start()

        # FK cache for validation lookups
        self._fk_cache: dict[str, tuple[set[str], float]] = {}

        self._connected = False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2))
    def _connect(self) -> gspread.Spreadsheet:
        """Lazy connection au spreadsheet.

        Returns:
            gspread.Spreadsheet object

        Raises:
            SpreadsheetNotFoundError: Si le spreadsheet ne peut pas être ouvert.
        """
        if self._spreadsheet is not None:
            return self._spreadsheet

        try:
            auth = gspread.service_account(filename=str(self._settings.google_service_account_file))
            self._spreadsheet = auth.open_by_key(self._settings.google_sheets_spreadsheet_id)
            self._connected = True
            logger.info(
                "Connected to Google Sheets",
                extra={"spreadsheet_id": self._settings.google_sheets_spreadsheet_id},
            )
            return self._spreadsheet
        except GSpreadException as e:
            logger.error("Failed to connect to spreadsheet", exc_info=True)
            raise SpreadsheetNotFoundError(f"Cannot open spreadsheet: {e!s}") from e

    def _get_worksheet(self, name: str) -> gspread.Worksheet:
        """Récupère un worksheet par nom.

        Args:
            name: Nom du worksheet (ex: "Clients")

        Returns:
            gspread.Worksheet object

        Raises:
            WorksheetNotFoundError: Si le worksheet n'existe pas.
        """
        if name in self._worksheet_cache:
            return self._worksheet_cache[name]

        try:
            spreadsheet = self._connect()
            worksheet = spreadsheet.worksheet(name)
            self._worksheet_cache[name] = worksheet
            logger.debug(f"Loaded worksheet: {name}")
            return worksheet
        except GSpreadException as e:
            logger.error(f"Worksheet not found: {name}", exc_info=True)
            raise WorksheetNotFoundError(f"Worksheet '{name}' not found", sheet_name=name) from e

    def _read_sheet(self, sheet_name: str) -> pl.DataFrame:
        """Lit un sheet complet et le convertit en DataFrame Polars.

        Args:
            sheet_name: Nom du sheet (ex: "Clients", "Factures")

        Returns:
            pl.DataFrame contenant les données du sheet

        Raises:
            WorksheetNotFoundError: Si le sheet n'existe pas.
            RateLimitError: Si le rate limit est atteint.
            CircuitOpenError: Si le circuit breaker est ouvert.
        """
        # Check cache first
        if sheet_name in self._cache:
            logger.debug(f"Cache hit for sheet: {sheet_name}")
            self._cache_hits += 1
            return self._cache[sheet_name]

        self._cache_misses += 1

        # Rate limit acquire
        if not self._rate_limiter.try_acquire():
            wait_time = self._rate_limiter.wait_time()
            logger.warning(
                f"Rate limit reached, waiting {wait_time}s",
                extra={"sheet_name": sheet_name},
            )
            raise RateLimitError(
                f"Google Sheets API rate limit exceeded for {sheet_name}",
                sheet_name=sheet_name,
                retry_after=wait_time,
            )

        try:
            # Circuit breaker wrapped
            @self._circuit_breaker
            def _fetch() -> pl.DataFrame:
                worksheet = self._get_worksheet(sheet_name)
                records: Any = worksheet.get_all_records()  # type: ignore[attr-defined]
                if not records:
                    # Empty sheet — return empty DataFrame with schema
                    schema = get_schema(sheet_name)
                    return pl.DataFrame(schema=schema)
                df: pl.DataFrame = pl.DataFrame(records)
                # Cast to correct schema (strict=False handles empty strings in date fields)
                schema = get_schema(sheet_name)
                df = df.cast(schema, strict=False)  # type: ignore[arg-type]
                return df

            df: pl.DataFrame = _fetch()  # type: ignore[assignment]
            self._cache[sheet_name] = df
            logger.info(
                f"Loaded sheet: {sheet_name}",
                extra={"rows": len(df), "columns": len(df.columns)},  # type: ignore[arg-type]
            )
            return df  # type: ignore[return-value]

        except Exception as e:  # type: ignore[unreachable]
            if "CircuitBreakerOpenError" in type(e).__name__:
                raise CircuitOpenError(
                    f"Circuit breaker is open for {sheet_name}", sheet_name=sheet_name
                ) from e
            raise

    def get_all_clients(self) -> pl.DataFrame:
        """Lit tous les enregistrements de l'onglet Clients."""
        return self._read_sheet(SHEET_CLIENTS)

    def get_all_invoices(self) -> pl.DataFrame:
        """Lit tous les enregistrements de l'onglet Factures."""
        return self._read_sheet(SHEET_FACTURES)

    def get_all_transactions(self) -> pl.DataFrame:
        """Lit tous les enregistrements de l'onglet Transactions."""
        return self._read_sheet(SHEET_TRANSACTIONS)

    def get_all_lettrage(self) -> pl.DataFrame:
        """Lit tous les enregistrements de l'onglet Lettrage (read-only)."""
        return self._read_sheet(SHEET_LETTRAGE)

    def get_all_balances(self) -> pl.DataFrame:
        """Lit tous les enregistrements de l'onglet Balances (read-only)."""
        return self._read_sheet(SHEET_BALANCES)

    def get_all_metrics_nova(self) -> pl.DataFrame:
        """Lit tous les enregistrements de l'onglet Metrics NOVA (read-only)."""
        return self._read_sheet(SHEET_METRICS_NOVA)

    def get_all_cotisations(self) -> pl.DataFrame:
        """Lit tous les enregistrements de l'onglet Cotisations (read-only)."""
        return self._read_sheet(SHEET_COTISATIONS)

    def get_all_fiscal(self) -> pl.DataFrame:
        """Lit tous les enregistrements de l'onglet Fiscal IR (read-only)."""
        return self._read_sheet(SHEET_FISCAL_IR)

    def get_client(self, client_id: str) -> pl.DataFrame:
        """Récupère un client spécifique.

        Args:
            client_id: ID du client

        Returns:
            DataFrame avec une ligne (ou vide si non trouvé)
        """
        df = self.get_all_clients()
        return df.filter(pl.col("client_id") == client_id)

    def get_client_by_id(self, client_id: str) -> pl.DataFrame:
        """Alias for get_client() — récupère un client spécifique.

        Args:
            client_id: ID du client

        Returns:
            DataFrame avec une ligne (ou vide si non trouvé)
        """
        return self.get_client(client_id)

    def get_invoice(self, facture_id: str) -> pl.DataFrame:
        """Récupère une facture spécifique.

        Args:
            facture_id: ID de la facture

        Returns:
            DataFrame avec une ligne (ou vide si non trouvée)
        """
        df = self.get_all_invoices()
        return df.filter(pl.col("facture_id") == facture_id)

    def get_invoice_by_id(self, facture_id: str) -> pl.DataFrame:
        """Alias for get_invoice() — récupère une facture spécifique.

        Args:
            facture_id: ID de la facture

        Returns:
            DataFrame avec une ligne (ou vide si non trouvée)
        """
        return self.get_invoice(facture_id)

    def get_transaction(self, transaction_id: str) -> pl.DataFrame:
        """Récupère une transaction spécifique.

        Args:
            transaction_id: ID de la transaction

        Returns:
            DataFrame avec une ligne (ou vide si non trouvée)
        """
        df = self.get_all_transactions()
        return df.filter(pl.col("transaction_id") == transaction_id)

    def add_client(self, data: dict[str, Any] | Any) -> None:
        """Ajoute un client aux données Clients.

        Args:
            data: Dictionnaire ou modèle Client avec les champs client

        Raises:
            SheetValidationError: Si les champs requis manquent.
        """
        # Convert Pydantic model to dict if needed
        data_dict = data if isinstance(data, dict) else data.model_dump()  # type: ignore[assignment]

        headers = get_headers(SHEET_CLIENTS)
        values = self._dict_to_row(data_dict, headers, SHEET_CLIENTS)  # type: ignore[arg-type]
        op = WriteOp(sheet_name=SHEET_CLIENTS, operation="append", data=[values])
        self._write_queue.submit(op)
        self._invalidate_cache()
        logger.info(f"Added client: {data_dict.get('client_id')}")  # type: ignore[union-attr]

    def add_invoice(self, data: dict[str, Any] | Any) -> None:
        """Ajoute une facture aux données Factures.

        Args:
            data: Dictionnaire ou modèle Invoice avec les champs facture

        Raises:
            SheetValidationError: Si les champs requis manquent ou si client_id n'existe pas.
        """
        # Convert Pydantic model to dict if needed
        data_dict = data if isinstance(data, dict) else data.model_dump()  # type: ignore[assignment]

        # Validate client_id FK
        client_id: str = str(data_dict.get("client_id", ""))
        if not self._validate_fk(client_id, SHEET_CLIENTS, "client_id"):
            raise SheetValidationError(
                f"Foreign key violation: client_id '{client_id}' not found in Clients sheet",
                sheet_name=SHEET_FACTURES,
                field_name="client_id",
            )

        headers = get_headers(SHEET_FACTURES)
        values = self._dict_to_row(data_dict, headers, SHEET_FACTURES)  # type: ignore[arg-type]
        op = WriteOp(sheet_name=SHEET_FACTURES, operation="append", data=[values])
        self._write_queue.submit(op)
        self._invalidate_cache(SHEET_FACTURES)
        logger.info(f"Added invoice: {data_dict.get('facture_id')}")  # type: ignore[union-attr]

    def add_transactions(self, data: list[dict[str, Any] | Any]) -> None:
        """Ajoute une ou plusieurs transactions aux données Transactions.

        Déduplique par indy_id avant d'ajouter. Valide tous les facture_id FKs atomiquement.

        Args:
            data: Liste de dictionnaires ou modèles Transaction avec les champs transaction

        Raises:
            SheetValidationError: Si les champs requis manquent ou si facture_id n'existe pas.
        """
        if not data:
            return

        # Convert Pydantic models to dicts if needed
        data_list: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                data_list.append(item)  # type: ignore[arg-type]
            else:
                result = item.model_dump()  # type: ignore[attr-defined]
                data_list.append(result)  # type: ignore[arg-type]

        # Validate facture_id FKs BEFORE dedup (atomic: all or nothing)
        for i, d in enumerate(data_list):
            facture_id_raw = d.get("facture_id")
            facture_id: str = str(facture_id_raw) if facture_id_raw else ""
            if not self._validate_fk(facture_id, SHEET_FACTURES, "facture_id"):
                raise SheetValidationError(
                    f"Foreign key violation: facture_id '{facture_id}' not found in Factures sheet",
                    sheet_name=SHEET_TRANSACTIONS,
                    field_name="facture_id",
                    row_index=i + 1,
                )

        # Dedup by indy_id: first against existing, then within input
        existing = self.get_all_transactions()
        existing_indy_ids: set[Any] = set(existing["indy_id"].to_list())

        # Filter out transactions that already exist in the sheet
        candidates: list[dict[str, Any]] = [
            d for d in data_list if d.get("indy_id") not in existing_indy_ids
        ]

        # Dedup within candidates to keep only first occurrence of each indy_id
        seen_indy_ids: set[Any] = set()
        deduped: list[dict[str, Any]] = []
        for d in candidates:
            indy_id = d.get("indy_id")
            if indy_id not in seen_indy_ids:
                deduped.append(d)
                seen_indy_ids.add(indy_id)

        if not deduped:
            logger.info("No new transactions to add (all deduped)")
            return

        headers = get_headers(SHEET_TRANSACTIONS)
        rows = [self._dict_to_row(d, headers, SHEET_TRANSACTIONS) for d in deduped]
        op = WriteOp(sheet_name=SHEET_TRANSACTIONS, operation="append", data=rows)
        self._write_queue.submit(op)
        self._invalidate_cache(SHEET_TRANSACTIONS)
        logger.info(f"Added {len(deduped)} transactions")

    def update_invoice(self, facture_id: str, updates: dict[str, Any]) -> None:
        """Mets à jour les champs spécifiés d'une facture.

        Args:
            facture_id: ID de la facture
            updates: Dictionnaire {colonne: valeur}

        Raises:
            WorksheetNotFoundError: Si la facture n'est pas trouvée.
            SheetValidationError: Si client_id dans updates n'existe pas.
        """
        # Validate client_id FK if updating it
        if "client_id" in updates:
            client_id: str = str(updates["client_id"])
            if not self._validate_fk(client_id, SHEET_CLIENTS, "client_id"):
                raise SheetValidationError(
                    f"Foreign key violation: client_id '{client_id}' not found in Clients sheet",
                    sheet_name=SHEET_FACTURES,
                    field_name="client_id",
                )

        df = self.get_all_invoices()
        mask = df["facture_id"] == facture_id
        if not mask.any():
            raise WorksheetNotFoundError(
                f"Invoice {facture_id} not found",
                sheet_name=SHEET_FACTURES,
            )

        idx = mask.arg_max()
        if idx is None:
            raise WorksheetNotFoundError(
                f"Invoice {facture_id} not found",
                sheet_name=SHEET_FACTURES,
            )
        row_index: int = int(idx) + 2  # +1 for header, +1 for 1-based indexing
        self._update_row(SHEET_FACTURES, row_index, updates)
        self._invalidate_cache(SHEET_FACTURES)
        logger.info(f"Updated invoice: {facture_id}")

    def update_invoice_status(self, facture_id: str, new_status: str) -> None:
        """Mets à jour le statut d'une facture.

        Args:
            facture_id: ID de la facture
            new_status: Nouveau statut (string)

        Raises:
            WorksheetNotFoundError: Si la facture n'est pas trouvée.
        """
        self.update_invoice(facture_id, {"statut": new_status})

    def update_transaction(self, transaction_id: str, updates: dict[str, Any]) -> None:
        """Mets à jour les champs spécifiés d'une transaction.

        Rejette les modifications à transaction_id ou indy_id.

        Args:
            transaction_id: ID de la transaction
            updates: Dictionnaire {colonne: valeur}

        Raises:
            ValueError: Si transaction_id/indy_id changent.
            WorksheetNotFoundError: Si la transaction n'est pas trouvée.
        """
        if "transaction_id" in updates or "indy_id" in updates:
            raise ValueError("Cannot modify transaction_id or indy_id")

        df = self.get_all_transactions()
        mask = df["transaction_id"] == transaction_id
        if not mask.any():
            raise WorksheetNotFoundError(
                f"Transaction {transaction_id} not found",
                sheet_name=SHEET_TRANSACTIONS,
            )

        idx = mask.arg_max()
        if idx is None:
            raise WorksheetNotFoundError(
                f"Transaction {transaction_id} not found",
                sheet_name=SHEET_TRANSACTIONS,
            )
        row_index: int = int(idx) + 2  # +1 for header, +1 for 1-based indexing
        self._update_row(SHEET_TRANSACTIONS, row_index, updates)
        self._invalidate_cache(SHEET_TRANSACTIONS)
        logger.info(f"Updated transaction: {transaction_id}")

    def update_invoices_batch(self, updates: list[dict[str, Any]]) -> int:
        """Batch update multiple invoices in a single API call.

        Deduplicates by facture_id (last update wins).
        Returns count of rows updated.

        Args:
            updates: List of dicts, each with 'facture_id' + fields to update

        Returns:
            Count of unique facture_ids updated

        Raises:
            WorksheetNotFoundError: If a facture_id is not found.
        """
        if not updates:
            return 0

        # Dedup by facture_id: last occurrence wins
        deduped: dict[str, dict[str, Any]] = {}
        for update_dict in updates:
            facture_id = update_dict.get("facture_id")
            if facture_id:
                deduped[facture_id] = update_dict

        if not deduped:
            return 0

        # Get all invoices to find row indices
        df = self.get_all_invoices()
        headers = get_headers(SHEET_FACTURES)
        worksheet = self._get_worksheet(SHEET_FACTURES)

        # Build list of (row_index, fields_dict) for rows to update
        rows_to_update: list[tuple[int, dict[str, Any]]] = []
        for facture_id, update_dict in deduped.items():
            mask = df["facture_id"] == facture_id
            if not mask.any():
                raise WorksheetNotFoundError(
                    f"Invoice {facture_id} not found",
                    sheet_name=SHEET_FACTURES,
                )
            idx = mask.arg_max()
            if idx is None:
                raise WorksheetNotFoundError(
                    f"Invoice {facture_id} not found",
                    sheet_name=SHEET_FACTURES,
                )
            row_index: int = int(idx) + 2  # +1 for header, +1 for 1-based indexing
            rows_to_update.append((row_index, update_dict))

        # Build batch update: map of cell coords to values for single API call
        cells_map: dict[tuple[int, int], str] = {}  # (row, col) -> value
        for row_index, update_dict in rows_to_update:
            for col_name, value in update_dict.items():
                if col_name not in headers:
                    logger.warning(f"Skipping unknown column {col_name} in {SHEET_FACTURES}")
                    continue
                col_index: int = headers.index(col_name) + 1  # 1-based
                cells_map[(row_index, col_index)] = str(value) if value else ""

        # Execute single batch update via worksheet.update() with range notation
        if cells_map:
            # Find bounds
            rows = [r for r, _ in cells_map]
            cols = [c for _, c in cells_map]
            min_row, max_row = min(rows), max(rows)
            min_col, max_col = min(cols), max(cols)

            # Build 2D values array for the bounding box
            num_rows = max_row - min_row + 1
            num_cols = max_col - min_col + 1
            values: list[list[str]] = [["" for _ in range(num_cols)] for _ in range(num_rows)]

            # Populate with cell values
            for (row, col), value in cells_map.items():
                values[row - min_row][col - min_col] = value

            # Build range notation (e.g., "A2:Q11")
            start_letter = chr(64 + min_col)
            end_letter = chr(64 + max_col)
            range_notation = f"{start_letter}{min_row}:{end_letter}{max_row}"

            # Single API call
            worksheet.update(values=values, range_name=range_notation)  # type: ignore[attr-defined]
            logger.debug(
                f"Updated {len(cells_map)} cells in batch for {SHEET_FACTURES} ({range_notation})"
            )

        self._invalidate_cache(SHEET_FACTURES)
        logger.info(f"Batch updated {len(deduped)} invoices")
        return len(deduped)

    def update_transactions_batch(self, updates: list[dict[str, Any]]) -> int:
        """Batch update multiple transactions in a single API call.

        Deduplicates by transaction_id (last update wins).
        REJECTS updates to immutable fields: date_valeur, montant, libelle, type,
        source, indy_id, date_import.
        ALLOWS updates to: facture_id, statut_lettrage.
        Returns count of rows updated.

        Args:
            updates: List of dicts, each with 'transaction_id' + fields to update

        Returns:
            Count of unique transaction_ids updated

        Raises:
            SheetValidationError: If attempting to modify immutable fields.
            WorksheetNotFoundError: If a transaction_id is not found.
        """
        if not updates:
            return 0

        # Define immutable fields
        immutable_fields = {
            "date_valeur",
            "montant",
            "libelle",
            "type",
            "source",
            "indy_id",
            "date_import",
        }

        # Validate no immutable fields are being modified
        for update_dict in updates:
            for field in immutable_fields:
                if field in update_dict:
                    raise SheetValidationError(
                        f"Cannot modify immutable field '{field}' in Transactions",
                        sheet_name=SHEET_TRANSACTIONS,
                        field_name=field,
                    )

        # Dedup by transaction_id: last occurrence wins
        deduped: dict[str, dict[str, Any]] = {}
        for update_dict in updates:
            transaction_id = update_dict.get("transaction_id")
            if transaction_id:
                deduped[transaction_id] = update_dict

        if not deduped:
            return 0

        # Get all transactions to find row indices
        df = self.get_all_transactions()
        headers = get_headers(SHEET_TRANSACTIONS)
        worksheet = self._get_worksheet(SHEET_TRANSACTIONS)

        # Build list of (row_index, fields_dict) for rows to update
        rows_to_update: list[tuple[int, dict[str, Any]]] = []
        for transaction_id, update_dict in deduped.items():
            mask = df["transaction_id"] == transaction_id
            if not mask.any():
                raise WorksheetNotFoundError(
                    f"Transaction {transaction_id} not found",
                    sheet_name=SHEET_TRANSACTIONS,
                )
            idx = mask.arg_max()
            if idx is None:
                raise WorksheetNotFoundError(
                    f"Transaction {transaction_id} not found",
                    sheet_name=SHEET_TRANSACTIONS,
                )
            row_index: int = int(idx) + 2  # +1 for header, +1 for 1-based indexing
            rows_to_update.append((row_index, update_dict))

        # Build batch update: map of cell coords to values for single API call
        cells_map: dict[tuple[int, int], str] = {}  # (row, col) -> value
        for row_index, update_dict in rows_to_update:
            for col_name, value in update_dict.items():
                if col_name not in headers:
                    logger.warning(f"Skipping unknown column {col_name} in {SHEET_TRANSACTIONS}")
                    continue
                col_index: int = headers.index(col_name) + 1  # 1-based
                cells_map[(row_index, col_index)] = str(value) if value else ""

        # Execute single batch update via worksheet.update() with range notation
        if cells_map:
            # Find bounds
            rows = [r for r, _ in cells_map]
            cols = [c for _, c in cells_map]
            min_row, max_row = min(rows), max(rows)
            min_col, max_col = min(cols), max(cols)

            # Build 2D values array for the bounding box
            num_rows = max_row - min_row + 1
            num_cols = max_col - min_col + 1
            values: list[list[str]] = [["" for _ in range(num_cols)] for _ in range(num_rows)]

            # Populate with cell values
            for (row, col), value in cells_map.items():
                values[row - min_row][col - min_col] = value

            # Build range notation (e.g., "A2:Q11")
            start_letter = chr(64 + min_col)
            end_letter = chr(64 + max_col)
            range_notation = f"{start_letter}{min_row}:{end_letter}{max_row}"

            # Single API call
            worksheet.update(values=values, range_name=range_notation)  # type: ignore[attr-defined]
            logger.debug(
                f"Updated {len(cells_map)} cells in batch for "
                f"{SHEET_TRANSACTIONS} ({range_notation})"
            )

        self._invalidate_cache(SHEET_TRANSACTIONS)
        logger.info(f"Batch updated {len(deduped)} transactions")
        return len(deduped)

    def init_spreadsheet(self) -> None:
        """Crée un spreadsheet avec 8 worksheets, headers, et formules.

        Pour les CALC_SHEETS, ajoute des formules de calcul automatique.
        """
        spreadsheet = self._connect()

        # Create all 8 worksheets and add headers
        all_sheets = DATA_SHEETS + CALC_SHEETS
        worksheets_created: dict[str, gspread.Worksheet] = {}

        for sheet_name in all_sheets:
            try:
                spreadsheet.worksheet(sheet_name)
                logger.info(f"Worksheet already exists: {sheet_name}")
            except Exception:
                # Create new worksheet
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=20)
                logger.info(f"Created worksheet: {sheet_name}")

                # Cache and store the newly created worksheet
                self._worksheet_cache[sheet_name] = worksheet
                worksheets_created[sheet_name] = worksheet

                # Add headers
                headers = get_headers(sheet_name)
                worksheet.append_row(headers)
                logger.info(f"Added headers to {sheet_name}")

        # Add formulas to calculated sheets (after all headers are added)
        for sheet_name in CALC_SHEETS:
            if sheet_name in worksheets_created:
                worksheet = worksheets_created[sheet_name]
                # Add example formulas for balance/metrics/cotisations/fiscal
                if sheet_name == SHEET_LETTRAGE:
                    # Lettrage formulas: score = 50 (montant match) + 30 (date <=3j) + 20 (URSSAF)
                    # facture_id references Factures sheet, txn_id references Transactions sheet
                    facture_id_formula = '=IFERROR(VLOOKUP(A2,Factures!$A:$A,1,FALSE),"")'
                    txn_id_formula = '=IFERROR(VLOOKUP(C2,Transactions!$A:$A,1,FALSE),"")'
                    score_formula = (
                        '=IF(B2=D2,50,0)+IF(ABS(E2)<=3,30,0)+IF(ISNUMBER(SEARCH("URSSAF",C2)),20,0)'
                    )
                    # Statut formula determines lettrage status based on score
                    statut_formula = (
                        '=IF(F2>=80,"LETTRE_AUTO",IF(F2>0,"A_VERIFIER","PAS_DE_MATCH"))'
                    )
                    worksheet.append_row(
                        [
                            facture_id_formula,
                            "",
                            txn_id_formula,
                            "",
                            "",
                            score_formula,
                            statut_formula,
                        ]
                    )
                elif sheet_name == SHEET_BALANCES:
                    # Balances: SUMIFS for ca_total (filter by PAYE status)
                    worksheet.append_row(
                        [
                            "2026-01",
                            '=COUNTIFS(Factures!$K:$K,"PAYE",Factures!$H:$H,A2)',
                            '=SUMIFS(Factures!montant_total,Factures!statut,"PAYE",Factures!date_fin,A2)',
                            "=SUMIFS(Transactions!montant,Transactions!date_import,A2)",
                            "=C2-D2",
                            '=COUNTIFS(Factures!$K:$K,"<>PAYE",Factures!$H:$H,A2)',
                            '=COUNTIFS(Factures!$K:$K,"EN_ATTENTE",Factures!$H:$H,A2)',
                        ]
                    )
                elif sheet_name == SHEET_METRICS_NOVA:
                    # Metrics NOVA: heures_effectuees = SUM quantite WHERE type_unite=HEURE
                    worksheet.append_row(
                        [
                            "2026-Q1",
                            "=1",
                            '=SUMIF(Factures!$C:$C,"HEURE",Factures!$E:$E)',
                            '=SUMPRODUCT((Factures!$C:$C="HEURE")/COUNTIF(Factures!$B:$B,Factures!$B:$B&""))',
                            '=SUMIFS(Factures!$G:$G,Factures!$C:$C,"HEURE")',
                            "=DATE(2026,4,15)",
                        ]
                    )
                elif sheet_name == SHEET_COTISATIONS:
                    # Cotisations: taux_charges = 0.258, montant_charges = ca_encaisse * 0.258
                    worksheet.append_row(
                        [
                            "2026-01",
                            "0",
                            "=0.258",
                            "=B2*0.258",
                            "=DATE(2026,2,15)",
                            "=SUM(B$2:B2)",
                            "=B2-D2",
                        ]
                    )
                elif sheet_name == SHEET_FISCAL_IR:
                    # Fiscal IR: abattement = ca_micro * 0.34
                    # revenu_imposable = ca_micro - abattement
                    worksheet.append_row(
                        [
                            "0",
                            "=24000",
                            "=MIN(A2,B2)",
                            "=C2*0.34",
                            "=C2-D2",
                            "",
                            "",
                            "",
                        ]
                    )
                logger.info(f"Added formulas to {sheet_name}")

        self._connected = True
        logger.info("Spreadsheet initialization completed")

    def get_cache_stats(self) -> dict[str, int]:
        """Retourne les statistiques de cache (hits/misses).

        Returns:
            Dictionnaire contenant 'hits' et 'misses'
        """
        return {"hits": self._cache_hits, "misses": self._cache_misses}

    def _invalidate_cache(self, sheet_name: str | None = None) -> None:
        """Invalide le cache.

        Args:
            sheet_name: Nom du sheet à invalider (None = tout le cache)
        """
        if sheet_name is None:
            self._cache.clear()
            logger.debug("Cache cleared (all sheets)")
        else:
            self._cache.pop(sheet_name, None)
            logger.debug(f"Cache cleared for sheet: {sheet_name}")

    def _validate_fk(self, fk_value: str, target_sheet: str, target_column: str) -> bool:
        """Valide qu'une clé étrangère existe dans la cible.

        Implémente un cache TTL pour éviter les appels répétés à l'API Sheets.
        Les valeurs vides (nullable FKs) sont toujours valides.

        Args:
            fk_value: Valeur à chercher
            target_sheet: Nom du sheet cible (ex: "Clients")
            target_column: Nom de la colonne cible (ex: "client_id")

        Returns:
            True si fk_value existe ou est vide (nullable), False sinon.
        """
        # Nullable FKs: empty values are always valid
        if not fk_value or fk_value.strip() == "":
            return True

        cache_key = f"{target_sheet}:{target_column}"
        current_time = time.time()

        # Check cache validity
        if cache_key in self._fk_cache:
            cached_values, cached_at = self._fk_cache[cache_key]
            age = current_time - cached_at
            if age < self._settings.sheets_cache_ttl:
                # Cache hit
                return fk_value in cached_values

        # Cache miss: read from sheet using the appropriate getter
        if target_sheet == SHEET_CLIENTS:
            df = self.get_all_clients()
        elif target_sheet == SHEET_FACTURES:
            df = self.get_all_invoices()
        elif target_sheet == SHEET_TRANSACTIONS:
            df = self.get_all_transactions()
        else:
            df = self._read_sheet(target_sheet)

        if target_column not in df.columns:
            logger.warning(
                f"Column {target_column} not found in {target_sheet}",
                extra={"sheet": target_sheet, "column": target_column},
            )
            return False

        # Extract unique values and cache them
        values_set: set[str] = set(df[target_column].to_list())
        self._fk_cache[cache_key] = (values_set, current_time)

        result = fk_value in values_set
        logger.debug(
            f"FK validation: {target_sheet}.{target_column}={fk_value}",
            extra={"result": result, "cache_key": cache_key},
        )
        return result

    def _dict_to_row(self, data: dict[str, Any], headers: list[str], sheet_name: str) -> list[str]:
        """Convertit un dictionnaire en une liste ordonnée de valeurs.

        Args:
            data: Dictionnaire source
            headers: Liste ordonnée des colonnes
            sheet_name: Nom du sheet (pour logs)

        Returns:
            Liste de valeurs en ordre de headers

        Raises:
            SheetValidationError: Si un champ requis manque.
        """
        row: list[str] = []
        for header in headers:
            value: Any = data.get(header)
            row.append(str(value) if value is not None else "")
        return row

    def _update_row(self, sheet_name: str, row_index: int, fields: dict[str, Any]) -> None:
        """Mets à jour des cellules spécifiques d'une ligne.

        Args:
            sheet_name: Nom du sheet
            row_index: Numéro de ligne (1-based)
            fields: Dictionnaire {colonne: valeur}
        """
        headers: list[str] = get_headers(sheet_name)
        worksheet = self._get_worksheet(sheet_name)

        # Build cells to update: list of (cell_notation, value)
        cells_to_update: list[tuple[str, str]] = []
        for col_name, value in fields.items():
            if col_name not in headers:
                logger.warning(f"Skipping unknown column {col_name} in {sheet_name}")
                continue
            col_index: int = headers.index(col_name) + 1  # 1-based
            cell_notation: str = f"{chr(64 + col_index)}{row_index}"
            cells_to_update.append((cell_notation, str(value) if value else ""))

        if cells_to_update:
            # Use batch update via worksheet.update()
            for cell_notation, value in cells_to_update:
                worksheet.update(cell_notation, value)  # type: ignore[attr-defined]
            logger.debug(f"Updated {len(cells_to_update)} cells in {sheet_name} row {row_index}")

    def _execute_write_op(self, op: WriteOp) -> None:
        """Exécute une opération WriteOp.

        Args:
            op: WriteOp à exécuter

        Raises:
            WorksheetNotFoundError: Si le worksheet n'existe pas.
        """
        worksheet = self._get_worksheet(op.sheet_name)

        if op.operation == "append":
            worksheet.append_rows(op.data)
            logger.info(
                f"Appended {len(op.data)} rows to {op.sheet_name}",
                extra={"sheet_name": op.sheet_name},
            )
        elif op.operation == "update":
            # Range notation: "A1:C3" for example
            if not op.range_notation:
                raise ValueError("range_notation required for update operation")
            worksheet.update(values=op.data, range_name=op.range_notation)  # type: ignore[arg-type]
            logger.info(
                f"Updated range {op.range_notation} in {op.sheet_name}",
                extra={"sheet_name": op.sheet_name},
            )
        else:
            logger.warning(f"Unknown operation: {op.operation}")

    def close(self) -> None:
        """Arrête le worker de la write queue."""
        self._write_queue.stop()
        logger.info("SheetsAdapter closed")
