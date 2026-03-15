"""
Security utilities: authentication, authorization, audit logging.

Reference: docs/SECURITY-CODE-REVIEW.md
"""

from __future__ import annotations

import hmac
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer

from app.config import Settings

# Security-specific logger (separate from app logs)
security_logger = logging.getLogger("security")
audit_logger = logging.getLogger("audit")

# Configure audit logger to write to separate file
_audit_file_handler = logging.FileHandler("audit.log")
_audit_file_handler.setFormatter(logging.Formatter("%(message)s"))
audit_logger.addHandler(_audit_file_handler)
audit_logger.setLevel(logging.INFO)

bearer_scheme = HTTPBearer()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = HTTPBearer(),
    settings: Settings = None,  # Injected by FastAPI dependency
) -> str:
    """
    Verify API key using constant-time comparison.

    Args:
        credentials: HTTPAuthCredentials from Authorization: Bearer header
        settings: Application settings (contains expected API key)

    Returns:
        The verified API key

    Raises:
        HTTPException: 401 if key is invalid or missing

    Security:
        - Uses hmac.compare_digest() to prevent timing attacks
        - Does NOT log the submitted key
        - Does NOT expose key in error messages
    """
    if settings is None:
        # This should not happen if dependency injection is correct,
        # but fail securely if it does
        raise HTTPException(status_code=500, detail="Internal configuration error")

    expected_key = settings.API_KEY_INTERNAL.get_secret_value()
    submitted_key = credentials.credentials

    # Constant-time comparison (prevent timing attack / key brute-force)
    if not hmac.compare_digest(submitted_key, expected_key):
        security_logger.warning(
            "Invalid API key attempt",
            extra={"event": "auth_failure", "failure_reason": "invalid_key"},
        )
        raise HTTPException(status_code=401, detail="Invalid API key")

    return submitted_key


def log_audit_event(
    action: str,
    resource: str,
    resource_id: str,
    status: str,
    api_key_id: str | None = None,
    details: dict[str, Any] | None = None,
    error: str | None = None,
) -> None:
    """
    Log security-relevant action to audit log.

    Args:
        action: Action performed (e.g., "create_invoice", "submit_urssaf", "delete_client")
        resource: Resource type (e.g., "invoice", "client", "urssaf_submission")
        resource_id: ID of the resource affected
        status: Status of the action ("success" or "failure")
        api_key_id: Identifier of the API key used (e.g., fingerprint, not the key itself)
        details: Additional context (e.g., {"old_status": "DRAFT", "new_status": "SUBMITTED"})
        error: Error message if status is "failure"

    Example:
        log_audit_event(
            action="create_invoice",
            resource="invoice",
            resource_id="inv_abc123",
            status="success",
            api_key_id="key_fingerprint",
            details={"client_id": "cli_xyz789", "amount": 150.00}
        )
    """
    audit_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "status": status,
        "api_key_id": api_key_id,
        "details": details or {},
    }

    if error:
        audit_record["error"] = error

    audit_logger.info(json.dumps(audit_record))


def generate_request_id() -> str:
    """
    Generate a unique request ID for tracing.

    Used in error responses to allow support to correlate with server logs.

    Returns:
        UUID4 string
    """
    return str(uuid.uuid4())


def is_https_required(environment: str) -> bool:
    """
    Check if HTTPS should be enforced in responses.

    Args:
        environment: Current environment (development, staging, production)

    Returns:
        True if HTTPS enforcement headers should be added
    """
    return environment in ["staging", "production"]


def validate_request_origin(request: Request, allowed_origins: list[str]) -> bool:
    """
    Validate request origin against allowed list (additional to CORS middleware).

    Args:
        request: FastAPI request
        allowed_origins: List of allowed origins

    Returns:
        True if origin is allowed

    Note:
        This is supplementary to CORSMiddleware. Primarily useful for
        additional validation in sensitive endpoints.
    """
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        return True  # No origin header = likely same-site

    return any(origin.startswith(allowed) for allowed in allowed_origins)
