from __future__ import annotations


class SwanError(Exception):
    """Base exception for Swan API errors."""

    pass


class SwanAuthError(SwanError):
    """Raised for authentication/authorization errors (401/403)."""

    pass


class SwanAPIError(SwanError):
    """Raised for general Swan API errors."""

    pass
