# Security Quick Reference — Phase 1

**Print this and post on desk for Phase 1 implementation**

---

## Critical Changes in Code

### 1. Configuration (app/config.py)

**Change 1: Secret Masking**
```python
# BEFORE
URSSAF_CLIENT_SECRET: str  # EXPOSED IN LOGS!

# AFTER
URSSAF_CLIENT_SECRET: SecretStr  # Masked as ***
```

**Change 2: Google Service Account**
```python
# BEFORE
GOOGLE_SERVICE_ACCOUNT_PATH: str = "secrets/service-account.json"  # JSON FILE RISK

# AFTER
GOOGLE_SERVICE_ACCOUNT_B64: SecretStr  # Base64, no files
def get_google_service_account_dict() -> dict:  # Safe decoding
```

**Change 3: API Key Validation**
```python
# NEW
@field_validator("API_KEY_INTERNAL")
def validate_api_key_length(cls, v):
    if len(v.get_secret_value()) < 32:
        raise ValueError("API_KEY_INTERNAL must be >= 32 chars")
```

### 2. Main Application (app/main.py)

**Change 1: CORS Restriction**
```python
# BEFORE
allow_methods=["*"]
allow_headers=["*"]

# AFTER
allow_methods=["GET", "POST", "PUT", "DELETE"]
allow_headers=["Content-Type", "Authorization"]
```

**Change 2: Error Handler Improvement**
```python
# BEFORE
logger.error(f"Unhandled exception: {exc}", exc_info=True)
return JSONResponse(status_code=500, content={"error": "..."})

# AFTER
request_id = generate_request_id()
logger.error("...", extra={"request_id": request_id}, exc_info=True)
# Client sees request_id, server logs full trace
```

**Change 3: Security Headers**
```python
# NEW in error responses
response.headers["Strict-Transport-Security"] = "max-age=31536000"
response.headers["X-Content-Type-Options"] = "nosniff"
response.headers["X-Frame-Options"] = "DENY"
```

### 3. New Security Module (app/security.py)

**Created:** 150+ lines of security utilities

```python
# Authentication
async def verify_api_key(credentials, settings) -> str:
    if not hmac.compare_digest(submitted_key, expected_key):
        raise HTTPException(status_code=401)

# Audit Logging
def log_audit_event(action, resource, resource_id, status, details):
    audit_logger.info(json.dumps({
        "timestamp": ...,
        "action": action,
        "resource": resource,
        "status": status,
        ...
    }))

# Utilities
def generate_request_id() -> str: return str(uuid.uuid4())
def is_https_required(environment) -> bool: return environment in ["staging", "production"]
```

---

## Tasks to Complete

| # | Task | Status | Time | How |
|---|------|--------|------|-----|
| 1 | Fix Google SA loading | ✅ | 0h | Done in config.py |
| 2 | SecretStr masking | ✅ | 0h | Done in config.py |
| 3 | API authentication | ⏳ | 2h | Update 10 routers |
| 4 | CORS + headers | ✅ | 0h | Done in main.py |
| 5 | Audit logging | ⏳ | 2h | Call log_audit_event() |
| 6 | Rate limiting | ⏳ | 1h | Add @limiter.limit() |
| 7 | Exception IDs | ✅ | 0h | Done in main.py |

---

## Testing Checklist

```bash
# 1. Health (no auth)
curl http://localhost:8000/health
# Expected: 200 OK

# 2. Missing API key
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Content-Type: application/json" \
  -d '{"nom":"Test","email":"test@example.com"}'
# Expected: 401 Unauthorized

# 3. Invalid API key
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Authorization: Bearer wrong" \
  -H "Content-Type: application/json" \
  -d '{"nom":"Test","email":"test@example.com"}'
# Expected: 401 Unauthorized

# 4. Valid API key (will fail with 501 if endpoint not implemented)
API_KEY="<your-32-char-key>"
curl -X POST http://localhost:8000/api/v1/clients/ \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"nom":"Test","email":"test@example.com"}'
# Expected: 501 Not Implemented (OK, auth passed)

# 5. Rate limiting (after 10/min)
for i in {1..15}; do
  curl -X POST http://localhost:8000/api/v1/invoices/ \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"client_id":"c1","items":[],"montant_total":100}'
done
# Expected: Last 5 return 429 Too Many Requests

# 6. Check audit log
tail audit.log | jq '.'
# Expected: JSON with timestamp, action, status, etc.

# 7. Check headers
curl -i http://localhost:8000/api/v1/invalid
# Expected: Strict-Transport-Security, X-Frame-Options, etc.
```

---

## Environment Variables

### Production (.env)

```bash
# Secrets (NEVER in git)
ENVIRONMENT=production
GOOGLE_SERVICE_ACCOUNT_B64=<base64 JSON>
URSSAF_CLIENT_ID=<id>
URSSAF_CLIENT_SECRET=<secret>
SWAN_API_KEY=<key>
SMTP_PASSWORD=<app-password>
API_KEY_INTERNAL=<32+ random chars>

# Configuration
SPREADSHEET_ID=<sheet-id>
SWAN_ACCOUNT_ID=<account>
CORS_ORIGINS=https://sap-facture.example.com

# Optional
SENTRY_DSN=<optional>
```

### Development (.env.local)

```bash
ENVIRONMENT=development
GOOGLE_SERVICE_ACCOUNT_B64=<test base64>
API_KEY_INTERNAL=test_key_12345678901234567890123456
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
# ... other required fields
```

---

## Router Integration Template

### For Each Endpoint:

```python
# BEFORE
@router.post("/", response_model=Client, status_code=201)
async def create_client(request: ClientCreateRequest) -> Client:
    raise HTTPException(status_code=501, detail="Not implemented")

# AFTER
@router.post("/", response_model=Client, status_code=201)
async def create_client(
    request: ClientCreateRequest,
    api_key: str = Depends(verify_api_key),  # ADD THIS
) -> Client:
    try:
        # Create client
        client = await service.create_client(request)

        # Log success
        log_audit_event(
            action="create_client",
            resource="client",
            resource_id=client.id,
            status="success",
            details={"email": client.email}
        )
        return client

    except Exception as e:
        # Log failure
        log_audit_event(
            action="create_client",
            resource="client",
            resource_id=request.email,
            status="failure",
            error=str(e)
        )
        raise
```

---

## Rate Limiting by Endpoint

```python
# app/routers/invoices.py
@router.post("/", ...)
@limiter.limit("10/minute")
async def create_invoice(request: Request, ...):

@router.post("/{invoice_id}/submit", ...)
@limiter.limit("5/minute")
async def submit_invoice(request: Request, ...):

@router.get("/", ...)
@limiter.limit("100/minute")
async def list_invoices(request: Request, ...):

@router.post("/", ...)
@limiter.limit("5/minute")
async def create_client(request: Request, ...):
```

---

## Deployment Pre-Check

```bash
#!/bin/bash
set -e

echo "=== Security Pre-Deployment Check ==="

# 1. Check .env exists and is ignored
if [ ! -f .env ]; then
  echo "❌ .env file missing"
  exit 1
fi

if ! git check-ignore .env > /dev/null 2>&1; then
  echo "❌ .env not in .gitignore"
  exit 1
fi

# 2. Check API key length
API_KEY=$(grep "API_KEY_INTERNAL=" .env | cut -d= -f2)
if [ ${#API_KEY} -lt 32 ]; then
  echo "❌ API_KEY_INTERNAL too short (${#API_KEY} < 32)"
  exit 1
fi

# 3. Validate Google SA
python -c "
from app.config import Settings
s = Settings()
sa = s.get_google_service_account_dict()
print('✅ Google Service Account: ' + sa['client_email'])
" || exit 1

# 4. Check no hardcoded secrets
if grep -r "sk_live_\|sk_sandbox_\|AKIA\|BEGIN RSA" app/ --include="*.py"; then
  echo "❌ Hardcoded secrets found in app/"
  exit 1
fi

echo "✅ All checks passed"
```

---

## Common Issues & Solutions

### Issue 1: "GOOGLE_SERVICE_ACCOUNT_B64 is not valid base64"

**Solution:**
```bash
# Verify base64 is valid
echo $GOOGLE_SERVICE_ACCOUNT_B64 | base64 -d | jq .

# Re-encode if needed
base64 < service-account.json | tr -d '\n'
```

### Issue 2: "API_KEY_INTERNAL must be >= 32 characters"

**Solution:**
```bash
# Generate new key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Add to .env
API_KEY_INTERNAL=<output>
```

### Issue 3: "Invalid API key" on valid request

**Solution:**
```bash
# Check key matches exactly (no spaces)
echo -n $API_KEY_INTERNAL | wc -c  # Should be 43

# Check header format
curl -H "Authorization: Bearer <key>"  # Must be "Bearer", not "Basic"
```

### Issue 4: audit.log permission denied

**Solution:**
```bash
touch audit.log
chmod 600 audit.log  # Only app user can read
```

### Issue 5: Rate limiting not working

**Solution:**
```bash
# Verify slowapi installed
pip list | grep slowapi

# Check @limiter.limit() decorator on route
grep -n "@limiter.limit" app/routers/*.py

# Check Request param in handler
def handler(request: Request, ...):  # Must have Request
```

---

## Debugging Commands

```bash
# View real-time logs
tail -f app.log

# View audit events
tail -f audit.log | jq '.'

# Search audit log for failures
grep '"status": "failure"' audit.log | jq '.error'

# Check CORS headers
curl -i -X OPTIONS http://localhost:8000/api/v1/clients/ \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"

# Check security headers
curl -i http://localhost:8000/api/v1/invalid | grep -E "Strict-Transport|X-Frame|X-Content"

# Test auth header parsing
python -c "
from fastapi.security import HTTPBearer
from fastapi import HTTPAuthCredentials
bearer = HTTPBearer()
print(bearer)
"

# List all routes
python -c "
from app.main import app
for route in app.routes:
    print(f'{route.path} → {route.methods}')
"
```

---

## Phase 1 Completion Checklist

- [ ] All routers have `Depends(verify_api_key)` on protected endpoints
- [ ] All state-changing endpoints call `log_audit_event()`
- [ ] Rate limiting applied to critical endpoints
- [ ] Tests passing (pytest)
- [ ] curl tests from "Testing Checklist" passing
- [ ] Pre-deployment check script passing
- [ ] No secrets in git history
- [ ] Documentation updated
- [ ] Incident response procedures reviewed
- [ ] Team trained on security controls

---

## Quick Links

- **Code Review:** docs/SECURITY-CODE-REVIEW.md
- **Phase 1 Tasks:** docs/phase1/12-SECURITY-PHASE1-TASKS.md
- **Security Summary:** docs/SECURITY-SUMMARY.md
- **Incident Response:** docs/INCIDENT_RESPONSE.md
- **Environment Example:** .env.example

**Questions?** Start with docs/SECURITY-CODE-REVIEW.md for detailed explanations.
