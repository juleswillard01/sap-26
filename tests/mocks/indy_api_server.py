"""Mock Indy API server for integration testing.

FastAPI app simulating the reverse-engineered Indy REST API.
Supports auth, banking endpoints, error simulation, and 40 fixture transactions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

MOCK_JWT = "mock-jwt"
MOCK_CUSTOM_TOKEN = "mock-custom-token"
VALID_EMAIL = "test@indy.fr"
VALID_PASSWORD = "test-password"
VALID_2FA_CODE = "123456"
BANK_ACCOUNT_ID = "Xv7tiXcgbqoiKJ97k"

# ──────────────────────────────────────────────
# Pydantic request models
# ──────────────────────────────────────────────


class MfaVerifyPayload(BaseModel):
    """2FA verification payload."""

    emailCode: str  # noqa: N815


class LoginRequest(BaseModel):
    """Indy /api/auth/login request body."""

    email: str
    password: str
    turnstileToken: str  # noqa: N815
    mfaVerifyPayload: MfaVerifyPayload | None = None  # noqa: N815


class AccountingSummaryRequest(BaseModel):
    """Accounting summary request body."""

    startDate: str | None = None  # noqa: N815
    endDate: str | None = None  # noqa: N815


# ──────────────────────────────────────────────
# Fixture data — 40 transactions
# ──────────────────────────────────────────────


def _build_transactions() -> list[dict[str, Any]]:
    """Build 40 fixture transactions for testing."""
    txns: list[dict[str, Any]] = []

    # --- 20 URSSAF transactions (credit, spread across 2025) ---
    urssaf_data: list[tuple[str, str, str, int]] = [
        ("txn_001", "2025-01-10", "VIREMENT URSSAF CESU", 15000),
        ("txn_002", "2025-01-25", "VIR URSSAF 202501", 12500),
        ("txn_003", "2025-02-12", "VIREMENT URSSAF CESU", 18000),
        ("txn_004", "2025-02-28", "VIR URSSAF 202502", 22000),
        ("txn_005", "2025-03-15", "VIREMENT URSSAF CESU", 13500),
        ("txn_006", "2025-03-30", "VIR URSSAF 202503", 27000),
        ("txn_007", "2025-04-10", "VIREMENT URSSAF CESU", 19500),
        ("txn_008", "2025-04-28", "VIR URSSAF 202504", 16000),
        ("txn_009", "2025-05-14", "VIREMENT URSSAF CESU", 24000),
        ("txn_010", "2025-05-29", "VIR URSSAF 202505", 11000),
        ("txn_011", "2025-06-15", "VIREMENT URSSAF CESU", 20000),
        ("txn_012", "2025-07-08", "VIR URSSAF 202507", 28500),
        ("txn_013", "2025-07-22", "VIREMENT URSSAF CESU", 14000),
        ("txn_014", "2025-08-11", "VIR URSSAF 202508", 17500),
        ("txn_015", "2025-09-05", "VIREMENT URSSAF CESU", 21000),
        ("txn_016", "2025-09-25", "VIR URSSAF 202509", 26000),
        ("txn_017", "2025-10-10", "VIREMENT URSSAF CESU", 10500),
        ("txn_018", "2025-10-30", "VIR URSSAF 202510", 23000),
        ("txn_019", "2025-11-15", "VIREMENT URSSAF CESU", 19000),
        ("txn_020", "2025-12-10", "VIR URSSAF 202512", 30000),
    ]
    for txn_id, txn_date, desc, amount in urssaf_data:
        txns.append(_make_txn(txn_id, txn_date, desc, f"VIR URSSAF {txn_id}", amount))

    # --- 10 diverse transactions (debits, misc categories) ---
    diverse_data: list[tuple[str, str, str, int]] = [
        ("txn_021", "2025-01-18", "CB ACHAT FNAC", -8500),
        ("txn_022", "2025-02-20", "PRLV ASSURANCE MMA", -15000),
        ("txn_023", "2025-03-08", "CB RESTAURANT LE PETIT", -4200),
        ("txn_024", "2025-04-15", "PRLV EDF ELECTRICITE", -9800),
        ("txn_025", "2025-05-22", "CB ACHAT AMAZON", -6700),
        ("txn_026", "2025-06-30", "PRLV MUTUELLE HARMONIE", -12000),
        ("txn_027", "2025-07-14", "CB STATION TOTAL", -7500),
        ("txn_028", "2025-08-25", "PRLV BOUYGUES TELECOM", -3900),
        ("txn_029", "2025-09-18", "CB ACHAT DECATHLON", -11500),
        ("txn_030", "2025-10-05", "PRLV LOYER OCTOBRE", -20000),
    ]
    for txn_id, txn_date, desc, amount in diverse_data:
        txns.append(_make_txn(txn_id, txn_date, desc, desc, amount))

    # --- 5 orphan transactions (credits, no invoice pattern) ---
    orphan_data: list[tuple[str, str, str, int]] = [
        ("txn_031", "2025-02-05", "VIREMENT RECEIVED M DUPONT", 8000),
        ("txn_032", "2025-04-20", "REMBOURSEMENT TRESOR PUBLIC", 5500),
        ("txn_033", "2025-06-12", "VIR RECEIVED CLIENT DIVERS", 9200),
        ("txn_034", "2025-08-18", "VIREMENT CPAM REMBOURSEMENT", 3400),
        ("txn_035", "2025-11-02", "VIR RECEIVED PARTICULIER", 7100),
    ]
    for txn_id, txn_date, desc, amount in orphan_data:
        txns.append(_make_txn(txn_id, txn_date, desc, desc, amount))

    # --- 5 duplicate transactions (reuse IDs from URSSAF txn_001..txn_005) ---
    dup_data: list[tuple[str, str, str, int]] = [
        ("txn_001", "2025-01-10", "VIREMENT URSSAF CESU", 15000),
        ("txn_002", "2025-01-25", "VIR URSSAF 202501", 12500),
        ("txn_003", "2025-02-12", "VIREMENT URSSAF CESU", 18000),
        ("txn_004", "2025-02-28", "VIR URSSAF 202502", 22000),
        ("txn_005", "2025-03-15", "VIREMENT URSSAF CESU", 13500),
    ]
    for txn_id, txn_date, desc, amount in dup_data:
        txns.append(_make_txn(txn_id, txn_date, desc, f"VIR URSSAF {txn_id}", amount))

    return txns


def _make_txn(
    txn_id: str,
    txn_date: str,
    description: str,
    raw_description: str,
    amount_cents: int,
) -> dict[str, Any]:
    """Build a single transaction dict matching Indy's schema."""
    return {
        "_id": txn_id,
        "date": txn_date,
        "description": description,
        "rawDescription": raw_description,
        "amountInCents": amount_cents,
        "totalAmountInCents": amount_cents,
        "transactionType": "od",
        "bankAccountId": BANK_ACCOUNT_ID,
        "isVerified": False,
        "isDeleted": False,
        "subdivisions": [],
    }


TRANSACTIONS: list[dict[str, Any]] = _build_transactions()

# ──────────────────────────────────────────────
# FastAPI app
# ──────────────────────────────────────────────

app = FastAPI(title="Mock Indy API", docs_url=None, redoc_url=None)


# ──────────────────────────────────────────────
# Error simulation middleware
# ──────────────────────────────────────────────


@app.middleware("http")
async def error_simulation_middleware(request: Request, call_next: Any) -> JSONResponse:
    """Intercept X-Mock-Error header to simulate failures."""
    mock_error = request.headers.get("X-Mock-Error")

    if mock_error == "timeout":
        await asyncio.sleep(31)
        return JSONResponse(status_code=504, content={"error": "Gateway Timeout"})

    if mock_error == "500":
        return JSONResponse(status_code=500, content={"error": "Internal Server Error"})

    if mock_error == "401":
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    response: JSONResponse = await call_next(request)
    return response


# ──────────────────────────────────────────────
# Auth helpers
# ──────────────────────────────────────────────


def _validate_bearer(authorization: str | None) -> bool:
    """Check that Authorization header carries the expected mock JWT."""
    if authorization is None:
        return False
    return authorization == f"Bearer {MOCK_JWT}"


def _unauthorized_response() -> JSONResponse:
    """Standard 401 response for invalid/missing bearer token."""
    return JSONResponse(status_code=401, content={"error": "Unauthorized"})


# ──────────────────────────────────────────────
# Auth endpoints
# ──────────────────────────────────────────────


@app.post("/api/auth/login")
async def login(body: LoginRequest) -> JSONResponse:
    """Simulate Indy login with optional 2FA."""
    if body.email != VALID_EMAIL or body.password != VALID_PASSWORD:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid credentials"},
        )

    if body.mfaVerifyPayload is None:
        return JSONResponse(
            status_code=401,
            content={"error": "2FA required", "mfaRequired": True},
        )

    if body.mfaVerifyPayload.emailCode != VALID_2FA_CODE:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid 2FA code"},
        )

    return JSONResponse(
        status_code=200,
        content={"customToken": MOCK_CUSTOM_TOKEN},
    )


# ──────────────────────────────────────────────
# Banking endpoints
# ──────────────────────────────────────────────


@app.get("/api/transactions/transactions-list")
async def transactions_list(
    startDate: str | None = None,  # noqa: N803
    endDate: str | None = None,  # noqa: N803
    authorization: str | None = Header(None),
) -> JSONResponse:
    """Return filtered transaction list."""
    if not _validate_bearer(authorization):
        return _unauthorized_response()

    filtered = _filter_transactions_by_date(startDate, endDate)
    return JSONResponse(
        status_code=200,
        content={"transactions": filtered},
    )


def _filter_transactions_by_date(
    start_date: str | None,
    end_date: str | None,
) -> list[dict[str, Any]]:
    """Filter TRANSACTIONS fixture by date range."""
    result: list[dict[str, Any]] = []
    for txn in TRANSACTIONS:
        txn_date: str = txn["date"]
        if start_date and txn_date < start_date:
            continue
        if end_date and txn_date > end_date:
            continue
        result.append(txn)
    return result


@app.get("/api/transactions/transactions-pending-list")
async def transactions_pending(
    authorization: str | None = Header(None),
) -> JSONResponse:
    """Return empty pending transactions (nothing pending in mock)."""
    if not _validate_bearer(authorization):
        return _unauthorized_response()

    return JSONResponse(
        status_code=200,
        content={"transactions": []},
    )


@app.get("/api/compte-pro/bank-account")
async def bank_account(
    authorization: str | None = Header(None),
) -> JSONResponse:
    """Return mock bank account with balance."""
    if not _validate_bearer(authorization):
        return _unauthorized_response()

    return JSONResponse(
        status_code=200,
        content={
            "_id": BANK_ACCOUNT_ID,
            "name": "Compte courant",
            "balanceInCents": 450000,
            "availableBalanceInCents": 440000,
            "lastSyncAt": "2025-12-31T12:00:00.000Z",
            "bankConnector": {
                "id": "76e14af1-a2db-452d-b818-5b3b37b305a8",
                "type": "swan",
                "accountStatus": "Opened",
            },
        },
    )


@app.get("/api/compte-pro/account-statements")
async def account_statements(
    authorization: str | None = Header(None),
) -> JSONResponse:
    """Return mock monthly statement URLs."""
    if not _validate_bearer(authorization):
        return _unauthorized_response()

    statements = [
        {
            "month": f"2025-{m:02d}",
            "url": f"https://swan.io/statements/2025-{m:02d}.pdf",
        }
        for m in range(1, 13)
    ]
    return JSONResponse(status_code=200, content=statements)


@app.post("/api/accounting/transactions/summary")
async def accounting_summary(
    body: AccountingSummaryRequest,
    authorization: str | None = Header(None),
) -> JSONResponse:
    """Return mock accounting summary."""
    if not _validate_bearer(authorization):
        return _unauthorized_response()

    return JSONResponse(
        status_code=200,
        content={
            "totalIncomeInCents": 387500,
            "totalExpenseInCents": -99100,
            "netInCents": 288400,
            "startDate": body.startDate or "2025-01-01",
            "endDate": body.endDate or "2025-12-31",
        },
    )
