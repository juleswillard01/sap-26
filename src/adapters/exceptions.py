from __future__ import annotations


class SheetsError(Exception):
    """Base exception for Google Sheets adapter errors."""

    def __init__(
        self,
        message: str = "An error occurred with Google Sheets",
        sheet_name: str | None = None,
    ) -> None:
        self.message = message
        self.sheet_name = sheet_name
        super().__init__(message)


class SpreadsheetNotFoundError(SheetsError):
    """Raised when spreadsheet_id is invalid or spreadsheet not found."""

    def __init__(
        self,
        message: str = "Spreadsheet not found or invalid spreadsheet_id",
        sheet_name: str | None = None,
    ) -> None:
        super().__init__(message, sheet_name)


class WorksheetNotFoundError(SheetsError):
    """Raised when worksheet/sheet with given name does not exist."""

    def __init__(
        self,
        message: str = "Worksheet not found",
        sheet_name: str | None = None,
    ) -> None:
        super().__init__(message, sheet_name)


class SheetValidationError(SheetsError):
    """Raised when row data is corrupted, missing field, or invalid type."""

    def __init__(
        self,
        message: str = "Sheet validation failed",
        sheet_name: str | None = None,
        row_index: int | None = None,
        field_name: str | None = None,
    ) -> None:
        self.row_index = row_index
        self.field_name = field_name
        super().__init__(message, sheet_name)


class RateLimitError(SheetsError):
    """Raised when Google Sheets API rate limit (60 req/min) exceeded."""

    def __init__(
        self,
        message: str = "Google Sheets API rate limit exceeded",
        sheet_name: str | None = None,
        retry_after: float = 60.0,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message, sheet_name)


class CircuitOpenError(SheetsError):
    """Raised when circuit breaker is open (pybreaker)."""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        sheet_name: str | None = None,
    ) -> None:
        super().__init__(message, sheet_name)


# ============================================================================
# Indy exceptions
# ============================================================================


class IndyError(Exception):
    """Base exception for Indy adapter errors."""

    def __init__(
        self,
        message: str = "An error occurred with Indy",
        http_status: int | None = None,
    ) -> None:
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class IndyLoginError(IndyError):
    """Login failed (credentials invalid, 2FA timeout, Turnstile)."""


class IndyAuthError(IndyError):
    """Firebase token exchange or refresh failed."""


class IndyAPIError(IndyError):
    """REST API call failed (5xx, timeout, malformed response)."""


class IndyConnectionError(IndyError):
    """connect() not called before using API methods."""
