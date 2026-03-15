# Security Implementation — Phase 1 Tasks

**Document:** Phase 1 Security Implementation Checklist
**Status:** Ready for implementation
**Estimated Effort:** 6-8 hours (5 critical tasks)
**Reference:** docs/SECURITY-CODE-REVIEW.md

---

## Overview

This document provides **step-by-step instructions** to implement critical security fixes identified in the code review. These must be completed before Phase 1 deployment.

### Critical Issues to Fix

| # | Task | Severity | Effort | Status |
|---|------|----------|--------|--------|
| 1 | Fix Google Service Account loading (base64 decoding) | CRITICAL | 1h | ⏳ |
| 2 | Use SecretStr for all secrets (config masking) | CRITICAL | 30m | ✅ |
| 3 | Implement API key authentication (verify_api_key) | CRITICAL | 2h | ⏳ |
| 4 | Improve CORS and HTTP security headers | HIGH | 1h | ✅ |
| 5 | Implement audit logging system | HIGH | 2h | ⏳ |
| 6 | Add rate limiting to endpoints | HIGH | 1h | ⏳ |
| 7 | Improve exception handling with request IDs | MEDIUM | 1h | ✅ |

---

## Task 1: Google Service Account Base64 Decoding

**Status:** ✅ Completed in app/config.py

**What was done:**
- Added `GOOGLE_SERVICE_ACCOUNT_B64: SecretStr` field to Settings
- Implemented `get_google_service_account_dict()` method
- Validates base64 decoding and JSON structure
- Added validation in lifespan startup

**Verification:**
```bash
# Test that config loads and validates
python -c "
from app.config import Settings
settings = Settings()
sa_dict = settings.get_google_service_account_dict()
print(f'Service Account: {sa_dict[\"client_email\"]}')"
```

**Status:** ✅ DONE

---

## Task 2: SecretStr for All Secrets

**Status:** ✅ Completed in app/config.py

**What was done:**
- Changed `URSSAF_CLIENT_SECRET` to `SecretStr`
- Changed `SWAN_API_KEY` to `SecretStr`
- Changed `SMTP_PASSWORD` to `SecretStr`
- Changed `API_KEY_INTERNAL` to `SecretStr`
- Changed `FERNET_ENCRYPTION_KEY` to `SecretStr | None`

**Added validators:**
- `validate_api_key_length()` — Ensures API_KEY_INTERNAL >= 32 chars
- `validate_secrets_not_placeholder()` — Prevents deploying with placeholder values

**Custom `__repr__`:**
```python
def __repr__(self) -> str:
    return f"Settings(ENVIRONMENT={self.ENVIRONMENT}, API_KEY_INTERNAL=***)"
```

**Verification:**
```bash
# Secrets should be masked in logs
python -c "
from app.config import Settings
settings = Settings()
print(repr(settings))  # Should show *** not actual key"
```

**Status:** ✅ DONE

---

## Task 3: API Key Authentication

**Status:** ⏳ In Progress — Need to integrate into routers

**What was done:**
- Created `app/security.py` with `verify_api_key()` dependency
- Uses `hmac.compare_digest()` for constant-time comparison
- Logs failed attempts to `security.log`
- Does NOT expose key in error messages

**What still needs to be done:**

### 3.1 Update Dependencies in app/config.py

The `verify_api_key()` function needs access to `Settings`. Update it to use FastAPI's dependency injection:

```python
# app/security.py
from fastapi import Depends, HTTPException
from app.config import Settings

async def verify_api_key(
    credentials: HTTPAuthCredentials = Depends(HTTPBearer()),
    settings: Settings = Depends(lambda: Settings()),  # ← Will be fixed in main.py
) -> str:
    """Verify API key..."""
```

### 3.2 Update main.py to provide Settings as dependency

```python
# app/main.py
from fastapi import Depends

def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    app = FastAPI(...)
    app.state.settings = settings

    # Add dependency override
    app.dependency_overrides[Settings] = lambda: settings

    # ... rest of app creation
```

### 3.3 Update routers to require authentication

```python
# app/routers/clients.py
from fastapi import Depends
from app.security import verify_api_key
from app.config import Settings

@router.post("/", response_model=Client, status_code=201)
async def create_client(
    request: ClientCreateRequest,
    api_key: str = Depends(verify_api_key),
    settings: Settings = Depends(Settings),
) -> Client:
    """Create client (requires valid API key)."""
    # api_key is verified at this point
    # Proceed with creation
    ...
```

### 3.4 Testing

```bash
# Test: Missing API key → 401
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Content-Type: application/json" \
  -d '{"nom": "Test"}'
# Should return: {"detail": "Invalid API key"}

# Test: Invalid API key → 401
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Authorization: Bearer wrong_key" \
  -H "Content-Type: application/json" \
  -d '{"nom": "Test"}'
# Should return: {"detail": "Invalid API key"}

# Test: Valid API key → 501 (endpoint not implemented, but auth passed)
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Authorization: Bearer $API_KEY_INTERNAL" \
  -H "Content-Type: application/json" \
  -d '{"nom": "Test"}'
# Should return: {"detail": "Not implemented - SheetsAdapter pending"}
```

**Status:** ⏳ In Progress — Router integration needed

---

## Task 4: CORS and HTTP Security Headers

**Status:** ✅ Completed in app/main.py

**What was done:**
- Changed `allow_methods=["*"]` to `["GET", "POST", "PUT", "DELETE"]`
- Changed `allow_headers=["*"]` to `["Content-Type", "Authorization"]`
- Added `max_age=600` to cache preflight responses
- Added security headers in error handler:
  - `Strict-Transport-Security: max-age=31536000`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
- Disabled Swagger UI in production

**Verification:**
```bash
# Check CORS headers
curl -i -X OPTIONS http://localhost:8000/api/v1/clients/ \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET"

# Check error headers
curl -i http://localhost:8000/error
# Should see: Strict-Transport-Security, X-Frame-Options, etc.
```

**Status:** ✅ DONE

---

## Task 5: Audit Logging System

**Status:** ⏳ In Progress — Need to integrate into services

**What was done:**
- Created `log_audit_event()` function in `app/security.py`
- Logs to separate `audit.log` file
- JSON format for machine-readability
- Logs: timestamp, action, resource, resource_id, status, details, error

**What still needs to be done:**

### 5.1 Create audit.log and verify permissions

```bash
touch audit.log
chmod 600 audit.log  # Only app user can read
```

### 5.2 Update routers to call `log_audit_event()`

Example: When creating an invoice

```python
# app/routers/invoices.py
from app.security import log_audit_event

@router.post("/", response_model=Invoice, status_code=201)
async def create_invoice(
    request: InvoiceCreateRequest,
    api_key: str = Depends(verify_api_key),
) -> Invoice:
    """Create invoice."""
    try:
        # Create invoice in Google Sheets
        invoice = await service.create_invoice(request)

        # Log success
        log_audit_event(
            action="create_invoice",
            resource="invoice",
            resource_id=invoice.id,
            status="success",
            api_key_id=api_key[:8] + "...",  # Don't log full key
            details={
                "client_id": invoice.client_id,
                "amount": float(invoice.montant_total),
                "items_count": len(invoice.items),
            }
        )

        return invoice

    except Exception as e:
        # Log failure
        log_audit_event(
            action="create_invoice",
            resource="invoice",
            resource_id=request.client_id,
            status="failure",
            error=str(e),
        )
        raise
```

### 5.3 Monitoring audit logs

```bash
# View recent audit events
tail -f audit.log

# Search for failed submissions
grep '"status": "failure"' audit.log

# Parse JSON for analysis
grep submit audit.log | jq '.resource_id'
```

**Status:** ⏳ In Progress — Service integration needed

---

## Task 6: Rate Limiting

**Status:** ⏳ Not started

**Effort:** ~1 hour

### 6.1 Install slowapi

```bash
pip install slowapi
```

### 6.2 Update pyproject.toml

```toml
[project]
dependencies = [
    # ... existing ...
    "slowapi==0.1.5",
]
```

### 6.3 Configure rate limiter in main.py

```python
# app/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)

def create_app(settings: Settings | None = None) -> FastAPI:
    # ... existing setup ...

    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        request_id = generate_request_id()
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "Too many requests. Please try again later.",
                    "request_id": request_id,
                }
            },
        )

    return app

app = create_app()
```

### 6.4 Apply rate limiting to endpoints

```python
# app/routers/invoices.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/", response_model=Invoice)
@limiter.limit("10/minute")  # 10 invoices per minute per IP
async def create_invoice(
    request: Request,  # Required for slowapi
    body: InvoiceCreateRequest,
    api_key: str = Depends(verify_api_key),
) -> Invoice:
```

**Suggested rate limits:**
- `POST /api/v1/clients/` — 5/minute (creating clients is rare)
- `POST /api/v1/invoices/` — 10/minute (main operation)
- `POST /api/v1/invoices/{id}/submit` — 5/minute (critical, don't overload URSSAF)
- `GET /api/v1/*` — 100/minute (reading is frequent)

**Status:** ⏳ Not started

---

## Task 7: Exception Handling with Request IDs

**Status:** ✅ Completed in app/main.py

**What was done:**
- Updated global exception handler to generate request_id
- Request ID included in error response to client
- Full stack trace logged server-side (never exposed to client)
- Request ID allows support to correlate with logs

**Example flow:**
```
Client: GET /api/v1/invalid → 500 error
Response: {"error": {"code": "INTERNAL_ERROR", "request_id": "abc-123"}}

Server logs:
2026-03-15 10:05:32 ERROR Unhandled exception (request_id=abc-123, ...)
Traceback: ...
```

**Status:** ✅ DONE

---

## Implementation Order

**Recommended sequence:**

1. ✅ Task 2: SecretStr (already done)
2. ✅ Task 1: Google Service Account (already done)
3. ✅ Task 4: CORS + Headers (already done)
4. ✅ Task 7: Exception handling (already done)
5. ⏳ Task 3: API Key authentication → 2 hours
6. ⏳ Task 5: Audit logging → 2 hours
7. ⏳ Task 6: Rate limiting → 1 hour

**Total time remaining:** ~5 hours

---

## Pre-Deployment Checklist

Before deploying to production, verify:

- [ ] `.env` file created from `.env.example`
- [ ] `GOOGLE_SERVICE_ACCOUNT_B64` is valid base64-encoded JSON
- [ ] `API_KEY_INTERNAL` is at least 32 random characters (not placeholder)
- [ ] `ENVIRONMENT=production`
- [ ] `CORS_ORIGINS` does NOT include `localhost`
- [ ] `SMTP_PASSWORD` is Gmail App Password (not regular password)
- [ ] Secrets Manager initialized on startup (test with `python -c "from app.config import Settings; Settings()"`)
- [ ] API key authentication working (test with curl)
- [ ] Audit logging to file
- [ ] Rate limiting active
- [ ] HTTPS enforced in production (Nginx, not FastAPI)
- [ ] Error handler returns generic messages
- [ ] Security headers present in responses

---

## Testing Commands

```bash
# Start dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test health endpoint (no auth required)
curl http://localhost:8000/health

# Test client creation without auth (should fail)
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Content-Type: application/json" \
  -d '{"nom":"Test","email":"test@example.com"}'
# Expected: 401 Unauthorized

# Test client creation with auth (should fail with 501, but auth passes)
API_KEY="<your-32-char-key>"
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"nom":"Test","email":"test@example.com"}'
# Expected: 501 Not Implemented

# Test rate limiting (should fail after 10 requests)
for i in {1..15}; do
  curl -X POST http://localhost:8000/api/v1/invoices/ \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"client_id":"c1","items":[],"montant_total":100}'
done
# Last 5 should return 429 Too Many Requests

# View audit log
tail -20 audit.log | jq '.' # Pretty-print JSON
```

---

## References

- Full code review: docs/SECURITY-CODE-REVIEW.md
- Security architecture: docs/phase3/security-review.md
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- OWASP Authentication: https://owasp.org/www-community/authentication_cheat_sheet
