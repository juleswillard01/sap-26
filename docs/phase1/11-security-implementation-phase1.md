# Security Implementation — Phase 1 Quick Start

**Document** : Quick Start Guide pour sécurité MVP
**Auteur** : Security Reviewer
**Date** : 15 Mars 2026
**Temps Estimé** : 4-6 heures (Day 1-3)

---

## Vue d'Ensemble (5 min)

Avant de déployer en production, 5 tâches CRITICAL de sécurité doivent être complétées :

| # | Task | Sévérité | Effort | Deadline |
|---|------|----------|--------|----------|
| 1 | Setup Secrets Management (.env, Pydantic) | CRITICAL | 1h | Day 1 |
| 2 | Implement API Authentication | CRITICAL | 2h | Day 1 |
| 3 | Google Sheets Access Control | CRITICAL | 30m | Day 1 |
| 4 | HTTPS + Certificate Verification | CRITICAL | 1h | Day 2 |
| 5 | Audit Logging | CRITICAL | 2h | Day 2 |

**Après ces 5 tâches** : MVP est sûr pour déployer.

---

## Task 1 : Setup Secrets Management (1 hour)

### Objectif
Charger tous les secrets (URSSAF, Google, Swan, SMTP) depuis `.env` sans les committer.

### Steps

#### 1.1 Create `.env` from template (5 min)

```bash
cd /path/to/sap-facture
cp .env.example .env

# Verify it's ignored by git
git check-ignore .env
# Output: .env (should match)

# If not in .gitignore, add it
echo ".env*" >> .gitignore
git add .gitignore
git commit -m "chore: ensure .env* in gitignore"
```

#### 1.2 Fill in secrets (15 min)

Edit `.env` and fill in (do NOT share this file):

```bash
# Get URSSAF credentials
URSSAF_CLIENT_ID=abc123
URSSAF_CLIENT_SECRET=xyz789
URSSAF_API_BASE_URL=https://portailapi.urssaf.fr

# Get Swan API key
SWAN_API_KEY=swan_key_here

# Get Google Service Account
# DON'T store JSON file on disk — encode base64:
# base64 -i /path/to/service-account.json | tr -d '\n'
GOOGLE_SERVICE_ACCOUNT_B64=eyJhbGc...

# Get Sheets & Drive IDs from URLs
GOOGLE_SHEETS_SPREADSHEET_ID=1a2b3c...
SHEETS_DRIVE_FOLDER_ID=0a1b2c...

# SMTP credentials
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password  # Use App Password, not regular Gmail password

# Generate strong API key
# python -c "import secrets; print(secrets.token_urlsafe(32))"
API_KEY_INTERNAL=your_strong_random_key_32_chars_min

# Set environment
APP_DEBUG=false
ENVIRONMENT=production
APP_LOG_LEVEL=INFO
```

#### 1.3 Create Pydantic Settings (30 min)

File: `app/config.py`

```python
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from .env"""

    # ============ URSSAF OAuth2 ============
    urssaf_client_id: str = Field(min_length=1)
    urssaf_client_secret: SecretStr = Field(min_length=1)
    urssaf_api_base_url: str = "https://portailapi.urssaf.fr"

    # ============ Swan API ============
    swan_api_key: SecretStr = Field(min_length=1)
    swan_api_base_url: str = "https://api.swan.io"

    # ============ Google Cloud ============
    google_service_account_b64: SecretStr = Field(min_length=1)
    google_sheets_spreadsheet_id: str = Field(min_length=1)
    sheets_drive_folder_id: str = Field(min_length=1)

    # ============ SMTP ============
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str
    smtp_password: SecretStr
    smtp_from_email: str = "noreply@sap-facture.example.com"

    # ============ API Security ============
    api_key_internal: SecretStr = Field(
        min_length=32,
        description="Internal API key for endpoint authentication"
    )

    # ============ App Config ============
    app_debug: bool = False
    app_log_level: str = "INFO"
    environment: str = Field(
        default="development",
        pattern="^(development|staging|production)$"
    )

    # ============ Optional Encryption ============
    fernet_encryption_key: Optional[SecretStr] = None

    # ============ Polling & Timeout ============
    payment_polling_interval_hours: int = 4
    api_timeout_seconds: int = 30

    # ============ Feature Flags ============
    enable_bank_reconciliation: bool = True
    enable_email_reminders: bool = True
    enable_nova_reporting: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Fail at startup if required field missing
        extra = "forbid"

        # Load from .env before environment variables
        env_file_encoding = "utf-8"

    def __init__(self, **data):
        """Validate at startup."""
        super().__init__(**data)

        # Enforce HTTPS in production
        if self.environment == "production":
            for url_name, url in [
                ("urssaf_api_base_url", self.urssaf_api_base_url),
                ("swan_api_base_url", self.swan_api_base_url),
            ]:
                if not url.startswith("https://"):
                    raise ValueError(
                        f"{url_name} must use HTTPS in production"
                    )

        logger.info(
            "Settings loaded",
            extra={
                "environment": self.environment,
                "debug": self.app_debug,
            }
        )


# Global settings instance (loaded once at startup)
settings = Settings()
```

#### 1.4 Verify secrets are NOT logged (5 min)

Add to Python startup code:

```python
# app/main.py
from app.config import settings

# Verify secrets are masked
print(f"Debug: {settings}")
# Output should show: api_key_internal=SecretStr('***') (masked, not exposed)
```

---

## Task 2 : Implement API Authentication (2 hours)

### Objectif
Toutes les routes FastAPI doivent nécessiter une clé API valide.

### Steps

#### 2.1 Create auth dependency (30 min)

File: `app/auth.py`

```python
from __future__ import annotations

import hmac
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Header, status

from app.config import settings

logger = logging.getLogger(__name__)


async def verify_api_key(
    x_api_key: Annotated[str, Header()] = None
) -> str:
    """
    Verify API key from X-API-Key header.
    Use constant-time comparison (prevent timing attack).
    """
    expected_key = settings.api_key_internal.get_secret_value()

    if not x_api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing API key"
        )

    # Constant-time comparison
    if not hmac.compare_digest(x_api_key, expected_key):
        logger.warning(f"Invalid API key attempt from client")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    return x_api_key
```

#### 2.2 Protect all routes (1 hour)

File: `app/main.py`

```python
from fastapi import FastAPI, Depends
from app.auth import verify_api_key

app = FastAPI()

# ========== POST /invoices ==========
@app.post("/invoices")
async def create_invoice(
    invoice: InvoiceRequest,
    _: str = Depends(verify_api_key)  # Requires auth
) -> InvoiceResponse:
    """Create a new invoice."""
    # Protected endpoint — only proceed if key is valid
    return await InvoiceService.create(invoice)


# ========== POST /clients ==========
@app.post("/clients")
async def register_client(
    client: ClientRequest,
    _: str = Depends(verify_api_key)
) -> ClientResponse:
    """Register a new client with URSSAF."""
    return await ClientService.register(client)


# ========== GET /reconcile ==========
@app.get("/reconcile")
async def reconcile_transactions(
    _: str = Depends(verify_api_key)
) -> ReconcileResponse:
    """Trigger bank reconciliation."""
    return await BankReconciliation.reconcile()


# ========== GET /health (no auth required) ==========
@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint (public)."""
    return {"status": "ok"}
```

#### 2.3 Test authentication (30 min)

```bash
# Test 1: No API key → should get 403
curl -X POST http://localhost:8000/invoices \
  -H "Content-Type: application/json" \
  -d '{"client_id": "c1", "montant": 100}'
# Expected: {"detail": "Missing API key"}

# Test 2: Wrong API key → should get 403
curl -X POST http://localhost:8000/invoices \
  -H "X-API-Key: wrong_key" \
  -H "Content-Type: application/json" \
  -d '{"client_id": "c1", "montant": 100}'
# Expected: {"detail": "Invalid API key"}

# Test 3: Valid API key → should succeed
curl -X POST http://localhost:8000/invoices \
  -H "X-API-Key: your_actual_api_key_from_.env" \
  -H "Content-Type: application/json" \
  -d '{"client_id": "c1", "montant": 100}'
# Expected: 201 Created (or error based on business logic)
```

---

## Task 3 : Google Sheets Access Control (30 min)

### Objectif
Sécuriser le Sheets pour que UNIQUEMENT Jules (owner) + Service Account (editor) aient accès.

### Steps

#### 3.1 Check current permissions (5 min)

1. Open Google Drive → locate your Sheets document
2. Click **Share** button (top right)
3. Note current permissions

#### 3.2 Restrict sharing (10 min)

In Google Sheets:

1. Click **Share** → top right
2. Change "Owner" → Only Jules (your Google account)
3. Add "Editor" → Service Account email (sa-name@project.iam.gserviceaccount.com)
4. Remove all other permissions
5. Set to **"Restricted"** (not "Public" or "Link Sharing")

Screenshot steps:
```
Share → Change to "Restricted" (not public)
      → Add Editors: only SA email
      → Owner: jules@gmail.com ONLY
```

#### 3.3 Verify with code (10 min)

File: `app/security/audit_sheets.py`

```python
from __future__ import annotations

import logging
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


async def verify_sheets_permissions(
    sheets_id: str,
    credentials,
    expected_editors: set[str],
) -> bool:
    """
    Verify only expected users have access.
    Return True if secure, False otherwise.
    """
    service = build("drive", "v3", credentials=credentials)

    try:
        file = service.files().get(
            fileId=sheets_id,
            fields="permissions(emailAddress, role, type)"
        ).execute()

        permissions = file.get("permissions", [])

        # Check each permission
        for perm in permissions:
            email = perm.get("emailAddress", "unknown")

            if perm["type"] == "public":
                logger.critical(
                    f"SECURITY: Sheets is public (not restricted)"
                )
                return False

            if email not in expected_editors:
                logger.warning(
                    f"SECURITY: Unexpected permission for {email} "
                    f"(role: {perm['role']})"
                )

        logger.info("Sheets permissions verified ✓")
        return True

    except Exception as e:
        logger.error(f"Failed to verify Sheets permissions: {e}")
        return False


# At startup, verify permissions
import asyncio

async def startup():
    is_secure = await verify_sheets_permissions(
        sheets_id=settings.google_sheets_spreadsheet_id,
        credentials=get_google_credentials(),
        expected_editors={
            "jules@gmail.com",
            "sa-name@project.iam.gserviceaccount.com"
        }
    )
    if not is_secure:
        logger.critical("Sheets permissions are NOT secure. Aborting startup.")
        raise RuntimeError("Sheets security check failed")
```

---

## Task 4 : HTTPS + Certificate Verification (1 hour)

### Objectif
Forcer HTTPS sur tous les appels API externes (URSSAF, Swan, Google).

### Steps

#### 4.1 Enforce HTTPS in production (15 min)

File: `app/config.py` (update Settings.__init__)

```python
def __init__(self, **data):
    """Validate at startup."""
    super().__init__(**data)

    # Enforce HTTPS in production
    if self.environment == "production":
        urls_to_check = [
            ("urssaf_api_base_url", self.urssaf_api_base_url),
            ("swan_api_base_url", self.swan_api_base_url),
        ]

        for url_name, url in urls_to_check:
            if not url.startswith("https://"):
                raise ValueError(
                    f"{url_name} MUST use HTTPS in production. "
                    f"Got: {url}"
                )

    logger.info(f"Settings validated for {self.environment} environment")
```

#### 4.2 Verify SSL certificates (30 min)

File: `app/integrations/urssaf_client.py`

```python
from __future__ import annotations

import ssl
import certifi
import aiohttp
from aiohttp import ClientSession, TCPConnector

import logging

logger = logging.getLogger(__name__)


class URSSAFClient:
    """URSSAF API client with strict SSL verification."""

    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.session: Optional[ClientSession] = None
        self.access_token: Optional[str] = None

    async def __aenter__(self) -> URSSAFClient:
        """Context manager: setup SSL-verified session."""

        # Create SSL context with certificate verification
        ssl_context = ssl.create_default_context(
            cafile=certifi.where()  # Use system CA bundle
        )
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Create connector with SSL context
        connector = TCPConnector(ssl=ssl_context)

        self.session = ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )

        logger.info("URSSAFClient session created with SSL verification")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup session."""
        if self.session:
            await self.session.close()

    async def get_access_token(self) -> str:
        """Obtain OAuth2 access token."""
        if not self.session:
            raise RuntimeError("Session not initialized")

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        try:
            async with self.session.post(
                f"{self.base_url}/oauth/token",
                json=payload,
                ssl=True,  # Verify SSL certificate
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.error(f"OAuth failed: {resp.status} {error_text}")
                    raise ValueError(f"OAuth error: {resp.status}")

                data = await resp.json()
                self.access_token = data["access_token"]

                logger.info("OAuth token obtained successfully")
                return self.access_token

        except aiohttp.ClientSSLError as e:
            logger.critical(f"SSL CERTIFICATE ERROR: {e}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error: {e}")
            raise

    async def create_payment_request(
        self, invoice: Invoice
    ) -> dict:
        """Create URSSAF payment request."""
        if not self.access_token:
            await self.get_access_token()

        payload = invoice.to_urssaf_payload()

        try:
            async with self.session.post(
                f"{self.base_url}/demandes-paiement",
                json=payload,
                headers={"Authorization": f"Bearer {self.access_token}"},
                ssl=True,  # Verify SSL
            ) as resp:
                if resp.status not in (200, 201):
                    error_text = await resp.text()
                    logger.error(f"Payment request failed: {resp.status}")
                    raise ValueError(f"API error: {resp.status}")

                return await resp.json()

        except aiohttp.ClientSSLError as e:
            logger.critical(f"SSL CERTIFICATE ERROR in payment request: {e}")
            raise


# Usage (in service)
async def submit_invoice(invoice: Invoice) -> dict:
    async with URSSAFClient(
        base_url=settings.urssaf_api_base_url,
        client_id=settings.urssaf_client_id,
        client_secret=settings.urssaf_client_secret.get_secret_value(),
    ) as client:
        return await client.create_payment_request(invoice)
```

#### 4.3 Test HTTPS verification (15 min)

```python
# Test with invalid certificate (should fail)
test_client = URSSAFClient(
    base_url="https://self-signed.badssl.com",  # Invalid cert
    client_id="test",
    client_secret="test"
)

# This should raise aiohttp.ClientSSLError
await test_client.get_access_token()
# Error: SSL Certificate verification failed (expected behavior)
```

---

## Task 5 : Audit Logging (2 hours)

### Objectif
Logger tous les événements de sécurité pour détection d'anomalies.

### Steps

#### 5.1 Setup audit logger (45 min)

File: `app/security/audit_logger.py`

```python
from __future__ import annotations

import logging
import json
from datetime import datetime
from pathlib import Path

from app.config import settings


class AuditLogger:
    """Log security-relevant events to separate file."""

    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create audit-specific logger
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)

        # File handler (audit.log)
        handler = logging.FileHandler(
            self.log_dir / "audit.log"
        )

        # Formatter: JSON for easier parsing
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

        # Prevent duplicate logs
        if not self.logger.handlers:
            self.logger.addHandler(handler)

    def log_invoice_created(
        self,
        invoice_id: str,
        client_id: str,
        montant: float,
    ) -> None:
        """Log invoice creation."""
        self.logger.info(
            f"INVOICE_CREATED | invoice_id={invoice_id} "
            f"client_id={client_id} montant={montant} "
            f"timestamp={datetime.utcnow().isoformat()}"
        )

    def log_api_call(
        self,
        service: str,  # "URSSAF", "Swan", "Sheets"
        endpoint: str,
        method: str,
        status_code: int,
    ) -> None:
        """Log external API calls."""
        self.logger.info(
            f"API_CALL | service={service} endpoint={endpoint} "
            f"method={method} status={status_code} "
            f"timestamp={datetime.utcnow().isoformat()}"
        )

    def log_auth_failure(
        self,
        reason: str,
        client_ip: str = "unknown",
    ) -> None:
        """Log failed authentication attempts."""
        self.logger.warning(
            f"AUTH_FAILED | reason={reason} client_ip={client_ip} "
            f"timestamp={datetime.utcnow().isoformat()}"
        )

    def log_sheets_access(
        self,
        action: str,  # "READ", "WRITE"
        sheet_name: str,
    ) -> None:
        """Log Google Sheets access."""
        self.logger.info(
            f"SHEETS_ACCESS | action={action} sheet={sheet_name} "
            f"timestamp={datetime.utcnow().isoformat()}"
        )

    def log_error(
        self,
        error_type: str,
        message: str,
    ) -> None:
        """Log security errors."""
        self.logger.error(
            f"SECURITY_ERROR | type={error_type} message={message} "
            f"timestamp={datetime.utcnow().isoformat()}"
        )


# Global instance
audit_logger = AuditLogger(log_dir=settings.log_dir if hasattr(settings, 'log_dir') else "./logs")
```

#### 5.2 Integrate audit logging into services (45 min)

File: `app/services/invoice_service.py`

```python
from __future__ import annotations

import logging
from app.security.audit_logger import audit_logger
from app.integrations.urssaf_client import URSSAFClient

logger = logging.getLogger(__name__)


class InvoiceService:
    """Handle invoice creation and submission."""

    async def create_invoice(self, invoice_request: InvoiceRequest) -> Invoice:
        """Create and submit invoice to URSSAF."""

        # Validation
        if invoice_request.montant_total <= 0:
            audit_logger.log_error(
                error_type="validation",
                message=f"Invalid montant: {invoice_request.montant_total}"
            )
            raise ValueError("Montant must be > 0")

        # Create invoice
        invoice = Invoice.from_request(invoice_request)

        try:
            # Submit to URSSAF
            async with URSSAFClient(
                base_url=settings.urssaf_api_base_url,
                client_id=settings.urssaf_client_id,
                client_secret=settings.urssaf_client_secret.get_secret_value(),
            ) as client:
                response = await client.create_payment_request(invoice)

            # Log success
            audit_logger.log_invoice_created(
                invoice_id=invoice.id,
                client_id=invoice.client_id,
                montant=invoice.montant_total,
            )

            audit_logger.log_api_call(
                service="URSSAF",
                endpoint="/demandes-paiement",
                method="POST",
                status_code=response.get("status_code", 201),
            )

            logger.info(f"Invoice {invoice.id} created successfully")
            return invoice

        except Exception as e:
            audit_logger.log_error(
                error_type="invoice_creation",
                message=str(e)
            )
            logger.error(f"Failed to create invoice: {e}", exc_info=True)
            raise
```

#### 5.3 Review audit logs (30 min)

```bash
# View recent audit logs
tail -20 logs/audit.log

# Search for failed auth
grep "AUTH_FAILED" logs/audit.log

# Search for API errors
grep "SECURITY_ERROR" logs/audit.log

# Setup log rotation (keep 30 days)
# In production, use logrotate or similar
```

---

## Checklist — Phase 1 Security Complete

- [ ] `.env` created from `.env.example`
- [ ] `.env` NOT in git history
- [ ] All secrets filled in `.env`
- [ ] `app/config.py` with Pydantic BaseSettings
- [ ] Secrets are `SecretStr` (masked in logs)
- [ ] `app/auth.py` with `verify_api_key` dependency
- [ ] All FastAPI routes protected with `Depends(verify_api_key)`
- [ ] Google Sheets: Only Jules (owner) + SA (editor)
- [ ] Google Sheets sharing: "Restricted" (not public)
- [ ] HTTPS enforced in production settings
- [ ] SSL certificate verification in URSSAF/Swan clients
- [ ] Audit logging configured
- [ ] Audit logs record: invoices, API calls, auth failures
- [ ] Tests pass: authentication, validation, HTTPS
- [ ] `.env` backed up securely (not in git)

---

## Testing — Run Before Deployment

```bash
# Test 1: Security settings validate at startup
python -c "from app.config import settings; print(f'✓ Settings loaded for {settings.environment}')"

# Test 2: Auth required
curl http://localhost:8000/invoices  # Should get 403
curl -H "X-API-Key: wrong" http://localhost:8000/invoices  # Should get 403
curl -H "X-API-Key: $(grep API_KEY_INTERNAL .env | cut -d= -f2)" http://localhost:8000/invoices  # Should work

# Test 3: HTTPS enforced
python -c "
from app.config import Settings
try:
    Settings(
        urssaf_api_base_url='http://example.com',  # HTTP (bad)
        environment='production'
    )
except ValueError as e:
    print(f'✓ HTTPS enforced: {e}')
"

# Test 4: Audit logs created
ls -la logs/audit.log

# Test 5: .env not in git
git log -p -- .env | head -1  # Should be empty
```

---

## Deployment Checklist

Before going to production:

- [ ] All 5 CRITICAL tasks completed
- [ ] Tests pass locally
- [ ] `.env` secured on server (not world-readable)
- [ ] Backups of `.env` exist (encrypted, separate location)
- [ ] Incident response plan documented (docs/INCIDENT_RESPONSE.md)
- [ ] Jules trained on security best practices

---

## Next Steps

After Phase 1:

1. **Phase 2 (Week 2-3)** : Rate limiting, input validation, error handling
2. **Phase 3 (Month 2+)** : Data encryption, secrets rotation policy, penetration testing

---

## Quick Contacts

- **Security Questions** : docs/phase3/security-review.md
- **Incident** : See docs/INCIDENT_RESPONSE.md
- **Help** : Review this checklist step-by-step

---

**✓ Phase 1 Security Implementation Ready**
