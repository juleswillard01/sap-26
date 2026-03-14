from __future__ import annotations


class URSSAFError(Exception):
    """Base exception for all URSSAF client errors."""

    pass


class URSSAFAuthError(URSSAFError):
    """Raised when authentication fails (401, invalid credentials)."""

    pass


class URSSAFValidationError(URSSAFError):
    """Raised when request validation fails (4xx payload errors)."""

    pass


class URSSAFServerError(URSSAFError):
    """Raised when URSSAF server returns 5xx errors."""

    pass


class URSSAFTimeoutError(URSSAFError):
    """Raised when network request times out."""

    pass


class URSSAFCircuitBreakerOpenError(URSSAFError):
    """Raised when circuit breaker is open (too many consecutive failures)."""

    pass
