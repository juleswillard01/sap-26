# URSSAF Service Implementation

This document describes the URSSAF service layer implementation for SAP-Facture, including invoice submission and status polling.

## Overview

The URSSAF service layer consists of:

1. **InvoiceRepository** - Data access layer for Invoice records
2. **PaymentRequestRepository** - Data access layer for PaymentRequest records
3. **URSSAFService** - Business logic for URSSAF interactions

## Components

### InvoiceRepository (`app/repositories/invoice_repository.py`)

Handles all Invoice CRUD operations and invoice number generation.

#### Key Methods

- `get_by_id(invoice_id: str) -> Invoice | None` - Get invoice by ID
- `list_all(user_id: str, status: str | None = None, page: int = 1, per_page: int = 10) -> list[Invoice]` - List invoices with pagination and filtering
- `count(user_id: str, status: str | None = None) -> int` - Count invoices for a user
- `create(data: dict[str, Any]) -> Invoice` - Create new invoice
- `update_status(invoice_id: str, status: InvoiceStatus) -> Invoice` - Update invoice status
- `generate_invoice_number() -> str` - Generate unique invoice number (format: YYYY-MM-NNN)

#### Usage Example

```python
from app.repositories.invoice_repository import InvoiceRepository
from sqlalchemy.orm import Session

def create_invoice(db: Session, invoice_data: dict) -> Invoice:
    repo = InvoiceRepository(db)

    # Generate unique invoice number
    invoice_number = repo.generate_invoice_number()
    invoice_data["invoice_number"] = invoice_number

    # Create invoice
    invoice = repo.create(invoice_data)
    return invoice
```

### PaymentRequestRepository (`app/repositories/payment_request_repository.py`)

Handles all PaymentRequest CRUD operations.

#### Key Methods

- `create(invoice_id: str, amount: float) -> PaymentRequest` - Create payment request
- `get_by_id(payment_request_id: str) -> PaymentRequest | None` - Get payment request by ID
- `get_by_invoice_id(invoice_id: str) -> PaymentRequest | None` - Get payment request by invoice
- `list_pending() -> list[PaymentRequest]` - List pending payment requests
- `list_submitted() -> list[PaymentRequest]` - List all non-final payment requests
- `update_status(payment_request_id: str, status: PaymentRequestStatus, raw_response: str | None = None) -> PaymentRequest` - Update status
- `increment_retry_count(payment_request_id: str) -> PaymentRequest` - Increment retry counter
- `set_error(payment_request_id: str, error_message: str) -> PaymentRequest` - Mark as error

#### Usage Example

```python
from app.repositories.payment_request_repository import PaymentRequestRepository
from sqlalchemy.orm import Session

def create_payment_request(db: Session, invoice_id: str, amount: float) -> PaymentRequest:
    repo = PaymentRequestRepository(db)
    return repo.create(invoice_id, amount)
```

### URSSAFService (`app/services/urssaf_service.py`)

Business logic for URSSAF API interactions.

#### Key Methods

- `async submit_invoice(invoice_id: str) -> PaymentRequest` - Submit invoice to URSSAF
- `async poll_status(payment_request_id: str) -> PaymentRequestStatus` - Poll payment status
- `async sync_all_pending() -> list[dict[str, Any]]` - Sync all pending payment requests

#### Invoice Submission Workflow

```python
from app.services.urssaf_service import URSSAFService
from app.integrations.urssaf_client import URSSAFClient
from sqlalchemy.orm import Session

async def submit_invoice_to_urssaf(
    db: Session,
    urssaf_client: URSSAFClient,
    invoice_id: str,
) -> PaymentRequest:
    service = URSSAFService(db, urssaf_client)

    # Submit invoice (converts to URSSAF format, calls API, creates PaymentRequest)
    payment_request = await service.submit_invoice(invoice_id)

    # Invoice status is automatically updated to SUBMITTED
    # PaymentRequest is created with PENDING status
    return payment_request
```

#### Status Polling Workflow

```python
async def poll_invoice_status(
    db: Session,
    urssaf_client: URSSAFClient,
    payment_request_id: str,
) -> PaymentRequestStatus:
    service = URSSAFService(db, urssaf_client)

    # Poll status from URSSAF
    status = await service.poll_status(payment_request_id)

    # Both PaymentRequest and Invoice statuses are automatically updated
    return status
```

#### Bulk Sync Workflow

```python
async def sync_pending_invoices(
    db: Session,
    urssaf_client: URSSAFClient,
) -> list[dict]:
    service = URSSAFService(db, urssaf_client)

    # Sync all pending payment requests
    # - Polls status from URSSAF
    # - Updates PaymentRequest and Invoice statuses
    # - Implements retry logic (max 3 retries)
    # - Marks as ERROR after max retries exceeded
    results = await service.sync_all_pending()

    return results
```

## Error Handling

The service implements comprehensive error handling:

1. **Validation Errors** - Invoice not found, not in DRAFT status, etc.
2. **URSSAF Errors** - Authentication, server errors, timeouts
3. **Retry Logic** - Automatic retry on URSSAF errors (max 3 retries)
4. **Error Logging** - All errors logged with full context

## Status Mappings

### Invoice Status Enum
```
DRAFT → Not yet submitted
SUBMITTED → Submitted to URSSAF, awaiting response
VALIDATED → URSSAF validated the invoice
PAID → Payment completed
REJECTED → URSSAF rejected the invoice
ERROR → Submission failed after max retries
```

### Payment Request Status Enum
```
PENDING → Awaiting URSSAF response
VALIDATED → URSSAF validated
PAID → Payment completed
REJECTED → URSSAF rejected
EXPIRED → Payment window expired
ERROR → Submission failed after max retries
```

### URSSAF API Status → Payment Status Mapping
```
VALIDATED → PaymentRequestStatus.VALIDATED
PAID → PaymentRequestStatus.PAID
REJECTED → PaymentRequestStatus.REJECTED
EXPIRED → PaymentRequestStatus.EXPIRED
PENDING → PaymentRequestStatus.PENDING
(other) → PaymentRequestStatus.PENDING (default)
```

### Payment Status → Invoice Status Mapping
```
PENDING → InvoiceStatus.SUBMITTED
VALIDATED → InvoiceStatus.VALIDATED
PAID → InvoiceStatus.PAID
REJECTED → InvoiceStatus.REJECTED
EXPIRED → InvoiceStatus.REJECTED
ERROR → InvoiceStatus.ERROR
```

## Audit Logging

All status changes are logged to the audit_logs table via AuditService:

- Invoice submission
- Status updates
- Error conditions
- All actions include user_id, timestamp, and metadata

## Testing

Comprehensive test suites are provided:

- **test_invoice_repository.py** - 21 tests covering all repository methods
- **test_urssaf_service.py** - 23 tests covering service methods, error handling, and retry logic

Run tests with:
```bash
python3 -m pytest tests/unit/test_invoice_repository.py tests/unit/test_urssaf_service.py -v
```

## Database Schema

The implementation uses two main tables:

### invoices table
- id (UUID primary key)
- user_id (FK to users)
- client_id (FK to clients)
- invoice_number (unique)
- status (enum: DRAFT, SUBMITTED, VALIDATED, PAID, REJECTED, ERROR)
- amount_ttc (float)
- payment_request_id (FK to payment_requests)
- created_at, updated_at timestamps

### payment_requests table
- id (UUID primary key)
- invoice_id (FK to invoices)
- urssaf_request_id (unique)
- status (enum: PENDING, VALIDATED, PAID, REJECTED, EXPIRED, ERROR)
- amount (float)
- retry_count (int)
- error_message (text)
- raw_response (JSON text)
- created_at, updated_at timestamps

## Configuration

URSSAF client credentials are configured via environment variables:
- `URSSAF_API_BASE` - API base URL
- `URSSAF_CLIENT_ID` - OAuth client ID (encrypted in DB)
- `URSSAF_CLIENT_SECRET` - OAuth client secret (encrypted in DB)

See `app/config.py` for full configuration details.

## Dependencies

- sqlalchemy 2.0+
- pydantic (for validation)
- httpx (for URSSAF API calls)
- python 3.10+

## Code Quality

- Type hints on all function signatures
- mypy strict mode compliance
- ruff linting (no issues)
- 80%+ test coverage
- Comprehensive docstrings
- Logging at all key points
