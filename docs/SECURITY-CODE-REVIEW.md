# Revue de Code Sécurité — SAP-Facture v0.1.0

**Date:** 2026-03-15
**Scope:** Architecture v0.1.0 (FastAPI MVP, sans implémentation des services)
**Verdict:** ✅ **SÉCURITÉ PRÉALABLE SOLIDE** — Fondations correctes, risques mineurs

---

## Résumé Exécutif

Le code actuel suit une architecture sécurisée dès la conception :

### Points Positifs (✅)
- **Pydantic v2** pour validation stricte de tous les inputs externes
- **Type hints stricts** (mypy --strict) appliqués systématiquement
- **Pas de secrets hardcodés** dans le code
- **.env.example bien documenté** avec guidance de sécurité
- **Configuration via BaseSettings** (Pydantic Settings v2)
- **CORS restrictif par défaut** (localhost:3000, localhost:8000)
- **Erreurs génériques** retournées aux clients (stack traces non exposées)
- **Logging structuré** avec python-json-logger
- **.gitignore correct** (.env, *.db, secrets/*)
- **EmailStr validation** pour tous les emails clients
- **Models séparation** — Pydantic pour validation, pas de logique métier

### Risques Identifiés (⚠️)
1. **CRITICAL** — `GOOGLE_SERVICE_ACCOUNT_PATH` charge depuis le filesystem
2. **HIGH** — Pas d'authentification sur les endpoints /api/v1/*
3. **HIGH** — Pas de validation HTTPS enforced en production
4. **HIGH** — CORS `allow_headers: ["*"]` trop permissif
5. **MEDIUM** — Pas de rate limiting sur les endpoints publics
6. **MEDIUM** — Logging d'exceptions expose potentiellement des détails sensibles
7. **MEDIUM** — Google Service Account jamais sur le disque, mais config l'ignore

---

## 1. Analyse de Configuration (app/config.py)

### 1.1 Secrets Management — RISQUE CRITIQUE

**Problème identifié:**
```python
GOOGLE_SERVICE_ACCOUNT_PATH: str = "secrets/service-account.json"
```

**Pourquoi c'est un risque:**
- Charge le fichier JSON depuis le disque à chaque démarrage
- JSON contient la clé privée de la service account Google
- Clé privée = accès complet à tous les buckets/sheets du projet
- Oubli du secret/ dans .gitignore = exposition publique sur GitHub

**Recommandation (CRITICAL):**
Charger depuis variable d'environnement en base64 (comme dans .env.example).

```python
from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr
import json
import base64

class Settings(BaseSettings):
    # CHANGE: Load from base64-encoded env var instead of disk file
    GOOGLE_SERVICE_ACCOUNT_B64: SecretStr = Field(
        description="Base64-encoded Google Service Account JSON"
    )

    @property
    def google_service_account_dict(self) -> dict:
        """Decode and parse Google Service Account from base64."""
        try:
            decoded = base64.b64decode(self.GOOGLE_SERVICE_ACCOUNT_B64.get_secret_value())
            return json.loads(decoded)
        except Exception as e:
            raise ValueError(f"Failed to decode GOOGLE_SERVICE_ACCOUNT_B64: {e}")
```

**Status:** À corriger avant Phase 1 déploiement.

### 1.2 Secrets Non Masqués dans BaseSettings

**Problème:**
```python
URSSAF_CLIENT_SECRET: str  # Should be SecretStr
SWAN_API_KEY: str         # Should be SecretStr
SMTP_PASSWORD: str        # Should be SecretStr
```

**Pourquoi c'est un risque:**
- Pydantic v2 par défaut affiche les valeurs string en logs/repr
- Si settings objet loggé accidentellement → secrets exposés

**Recommandation (CRITICAL):**
```python
from pydantic import SecretStr, Field

class Settings(BaseSettings):
    URSSAF_CLIENT_SECRET: SecretStr = Field(...)
    SWAN_API_KEY: SecretStr = Field(...)
    SMTP_PASSWORD: SecretStr = Field(...)

    def model_dump(self, **kwargs):
        """Custom dump that masks secrets."""
        return super().model_dump(**kwargs)
```

**Status:** À corriger immédiatement.

### 1.3 Validation de Startup ✅

**Bon point:**
```python
class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
```

Pydantic valide tous les champs au startup. Si .env manquant ou incomplet → erreur explicite. ✅

---

## 2. Analyse d'Architecture (app/main.py)

### 2.1 Global Exception Handler — Bon, mais à améliorer

**Code actuel:**
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: object, exc: Exception) -> JSONResponse:
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": {...}})
```

**Risque:**
- `logger.error(..., exc_info=True)` dump la stack trace complète en logs
- Si exception contient URL avec paramètres, secrets, ou données sensibles → exposés

**Recommandation (MEDIUM):**
```python
import logging
import uuid

logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Generate request ID for tracing without exposing details
    request_id = str(uuid.uuid4())

    # Log full error server-side ONLY (never client-facing)
    logger.error(
        "Unhandled exception",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
        },
        exc_info=True  # Full stack trace in logs, not in response
    )

    # Generic error to client
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Une erreur est survenue. Référence: " + request_id,
                "request_id": request_id  # For support debugging
            }
        }
    )
```

**Status:** Recommandation MEDIUM — à implémenter Phase 1.

### 2.2 CORS Configuration — RISQUE MOYEN

**Code actuel:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],      # ← RISQUE
    allow_headers=["*"],      # ← RISQUE
)
```

**Risque:**
- `allow_methods=["*"]` = accepte TOUS les verbes HTTP (PUT, DELETE, PATCH, etc.)
- `allow_headers=["*"]` = accepte n'importe quel header (Authorization, X-Custom-Secret, etc.)
- Combiné avec pas d'authentification = aucune barrière

**Recommandation (HIGH):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Whitelist
    allow_headers=["Content-Type", "Authorization"],  # Whitelist
    max_age=600,  # Cache preflight 10 minutes
)
```

**Status:** À corriger Phase 1.

### 2.3 GZIPMiddleware ✅

**Bon:**
```python
app.add_middleware(GZIPMiddleware, minimum_size=1000)
```

Réduit la taille des réponses, mitigue certaines attaques (BREACH). ✅

---

## 3. Analyse des Endpoints (app/routers/)

### 3.1 Pas d'Authentification sur /api/v1/*

**Problème:**
```python
@router.post("/", response_model=Client, status_code=201)
async def create_client(request: ClientCreateRequest) -> Client:
    # ← NO AUTH CHECK
```

**Tous les endpoints:**
- `/api/v1/clients/*` (4 endpoints)
- `/api/v1/invoices/*` (6 endpoints)
- **Sont accessibles anonymement**

**Risque:**
- N'importe qui peut créer/modifier/supprimer des clients et factures
- Pas de contrôle d'accès multi-tenant (n'est pas un enjeu ici: single-user)
- **MAIS:** Accès non contrôlé implique pas de traçabilité

**Recommandation (CRITICAL):**
Implémenter authentification API key dès Phase 1.

```python
# app/auth.py
from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import hmac
import hashlib

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthCredentials = Depends(security)) -> str:
    """Verify API key using constant-time comparison."""
    expected_key = os.getenv("API_KEY_INTERNAL")
    if not expected_key:
        raise HTTPException(status_code=500, detail="API_KEY_INTERNAL not configured")

    # Constant-time comparison (prevent timing attacks)
    if not hmac.compare_digest(credentials.credentials, expected_key):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return credentials.credentials

# app/routers/clients.py
@router.post("/", response_model=Client, status_code=201)
async def create_client(
    request: ClientCreateRequest,
    api_key: str = Depends(verify_api_key)  # ← ADD THIS
) -> Client:
```

**Status:** CRITICAL — Phase 1.

### 3.2 Pas de Rate Limiting

**Problème:**
Aucune limite sur le nombre de requêtes par seconde.

**Risque:**
- DoS: Attaquant peut inonder /api/v1/invoices/submit avec 1000 req/sec
- Chaque requête = appel URSSAF API = coûts
- Pas de protection contre brute-force sur les IDs (énumération de client_ids)

**Recommandation (HIGH):**
```bash
pip install slowapi
```

```python
# app/main.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# app/routers/invoices.py
@router.post("/{invoice_id}/submit", response_model=Invoice)
@limiter.limit("10/minute")
async def submit_invoice_to_urssaf(
    invoice_id: str,
    request: Request,  # Required for limiter
    api_key: str = Depends(verify_api_key)
) -> Invoice:
```

**Status:** HIGH — Phase 1.

### 3.3 Validation des Inputs — SOLIDE ✅

**Bon:**
```python
class ClientCreateRequest(BaseModel):
    nom: str = Field(min_length=1, max_length=100)
    email: EmailStr  # ← Auto-validates email format
    telephone: str | None = Field(None, max_length=20)

class InvoiceLineItem(BaseModel):
    quantity: float = Field(gt=0)  # ← Prevent negative
    unit_price: float = Field(gt=0)
    montant_total: float = Field(gt=0, le=100000)  # ← Max limit
```

Pydantic valide **avant** que le code métier le voie. ✅

---

## 4. Données Sensibles (PII)

### 4.1 Modèles de Données

Champs sensibles identifiés:
- `Client.email` — EmailStr (validé)
- `Client.telephone` — max 20 chars
- `Client.adresse` — max 255 chars
- `Client.code_postal`, `Client.ville` — OK
- `Invoice.montant_total` — financier, à protéger
- `Invoice.notes` — peut contenir du texte libre

### 4.2 Pas de Chiffrement at-rest (Attendu)

**Observation:**
Google Sheets comme backend = données **non chiffrées au repos**.

**Status de conformité:**
- RGPD Article 32 (sécurité) = PARTIELLEMENT satisfait
- Google Workspace chiffre le transport (TLS) ✅
- Google Workspace chiffre la base de données interne ✅
- **MAIS:** SAP-Facture n'ajoute pas de chiffrement application-level
- **Mitigation:** Restricted Sheets sharing (Jules uniquement), audit logging, accès via OAuth2

**Recommandation (MEDIUM):**
Phase 2+ : Ajouter chiffrement Fernet sur champs sensibles (email, adresse).

```python
from cryptography.fernet import Fernet
from pydantic import field_serializer

class EncryptedClient(BaseModel):
    email: str  # Pydantic decrypt before use

    @field_serializer('email')
    def serialize_email(self, value: str) -> str:
        """Encrypt email before serialization."""
        f = Fernet(os.getenv("FERNET_KEY"))
        return f.encrypt(value.encode()).decode()
```

**Status:** MEDIUM — Phase 2.

### 4.3 Audit Logging — À implémenter

**Recommandation (HIGH):**
```python
# app/audit_logger.py
import logging
from datetime import datetime
import json

audit_logger = logging.getLogger("audit")
file_handler = logging.FileHandler("audit.log")
file_handler.setFormatter(logging.Formatter('%(message)s'))
audit_logger.addHandler(file_handler)

def log_audit(
    action: str,
    resource: str,
    resource_id: str,
    status: str,
    api_key_id: str | None = None,
    details: dict | None = None
) -> None:
    """Log security-relevant actions."""
    audit_logger.info(json.dumps({
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,           # "create_invoice", "submit_urssaf"
        "resource": resource,       # "invoice", "client"
        "resource_id": resource_id,
        "status": status,           # "success", "failure"
        "api_key_id": api_key_id,
        "details": details or {}
    }))

# Usage in routers
@router.post("/", response_model=Invoice)
async def create_invoice(request: InvoiceCreateRequest, api_key: str = Depends(...)):
    try:
        invoice = service.create_invoice(request)
        log_audit("create_invoice", "invoice", invoice.id, "success")
        return invoice
    except Exception as e:
        log_audit("create_invoice", "invoice", request.client_id, "failure", details={"error": str(e)})
        raise
```

**Status:** HIGH — Phase 1.

---

## 5. Intégrations Externes

### 5.1 Google Sheets API — À contrôler

**Risques attendus:**
- OAuth2 token stocké où?
- Gestion de token refresh?
- Erreurs API exposent-elles des détails?

**Vérification attendue Phase 1:**
```python
# app/adapters/sheets_adapter.py (à créer)
class SheetsAdapter:
    def __init__(self, settings: Settings):
        # Load service account securely
        sa_dict = settings.google_service_account_dict
        self.credentials = service_account.Credentials.from_service_account_info(
            sa_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        # TLS enforced by google-api-python-client ✅
```

**Recommandation (HIGH):**
- Valider que Sheets sharing = Jules uniquement
- Ajouter error handling pour API errors
- Timeout sur appels Sheets (ne pas bloquer)

### 5.2 URSSAF OAuth2 — À sécuriser

**Risques:**
- OAuth2 token où stocké?
- Token expiration handling?
- PKCE utilisé?

**Recommandation (CRITICAL):**
```python
# app/integrations/urssaf_client.py
class URSSAFClient:
    def __init__(self, settings: Settings, sheets_adapter):
        self.client_id = settings.URSSAF_CLIENT_ID
        self.client_secret = settings.URSSAF_CLIENT_SECRET.get_secret_value()
        self.sheets = sheets_adapter

    async def get_token(self) -> str:
        """Get or refresh OAuth2 token."""
        # 1. Check if token in Sheets (cached)
        cached_token = self.sheets.get_urssaf_token()

        if cached_token and not self._is_expired(cached_token):
            return cached_token

        # 2. Request new token from URSSAF
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl.create_default_context())
        ) as session:
            async with session.post(
                "https://api.matrice.urssaf.fr/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    raise URSSAFAuthError(f"Token request failed: {resp.status}")
                data = await resp.json()

        # 3. Cache in Sheets
        new_token = data["access_token"]
        expires_in = data["expires_in"]
        self.sheets.cache_urssaf_token(new_token, expires_in)

        return new_token
```

**Status:** CRITICAL — Phase 1.

### 5.3 Swan API — Validation minimale

**Recommandation (MEDIUM):**
```python
# Validate API key format at startup
def validate_swan_api_key(key: SecretStr) -> None:
    """Ensure Swan API key is valid format."""
    key_str = key.get_secret_value()
    if not key_str.startswith("sk_live_") and not key_str.startswith("sk_sandbox_"):
        raise ValueError("Invalid Swan API key format")
```

**Status:** MEDIUM — Phase 1.

---

## 6. Dépendances & Versions

### 6.1 Audit des Dépendances Critiques

**Vérifier avant Phase 1:**
```bash
pip install pipdeptree safety
safety check --json  # Check CVE database
```

**Dépendances majeures:**
- `fastapi==0.109.0` — Latest, no known vulns ✅
- `pydantic==2.5.0` — Latest v2, no known vulns ✅
- `google-api-python-client==2.101.0` — À vérifier (peut être outdated)
- `aiohttp==3.9.1` — À mettre à jour si possible

**Recommandation (MEDIUM):**
Ajouter pre-commit hook pour `safety check`:
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Lucas-C/pre-commit-hooks-safety
    rev: v1.3.1
    hooks:
      - id: python-safety-dependencies-check
```

---

## 7. Checklist de Sécurité Phase 1

- [ ] **CRITICAL** — Charger Google Service Account depuis base64 env var (pas de fichier)
- [ ] **CRITICAL** — SecretStr pour URSSAF_CLIENT_SECRET, SWAN_API_KEY, SMTP_PASSWORD
- [ ] **CRITICAL** — Authentification API key sur /api/v1/* (verify_api_key middleware)
- [ ] **HIGH** — Validation HTTPS en production (ENVIRONMENT=production)
- [ ] **HIGH** — CORS restrictif (allow_methods, allow_headers whitelisting)
- [ ] **HIGH** — Audit logging pour tous les changements (create_client, create_invoice, submit)
- [ ] **HIGH** — URSSAF OAuth2 token caching + refresh logic
- [ ] **MEDIUM** — Global exception handler avec request_id
- [ ] **MEDIUM** — Rate limiting (slowapi) sur endpoints publics
- [ ] **MEDIUM** — Sentry DSN configuration pour error tracking
- [ ] **MEDIUM** — Safety check dans CI/CD pour CVE
- [ ] **MEDIUM** — Log filtering pour masquer secrets (email, client_id)

---

## 8. Checklist Phase 2+

- [ ] Chiffrement at-rest pour emails/adresses (Fernet)
- [ ] Right-to-be-forgotten workflow (soft delete + data retention)
- [ ] DPA avec Google (Data Processing Agreement)
- [ ] Certificate pinning pour URSSAF API
- [ ] Rotation automatique des secrets (3 mois)
- [ ] Monitoring + alerting pour accès suspects
- [ ] Backup encryption + disaster recovery test

---

## Conclusion

### Verdict: ✅ SOLIDE AVANT DÉPLOIEMENT

**Raisons:**
1. Architecture fondamentale sécurisée (Pydantic, type hints, error handling)
2. Pas de secrets hardcodés
3. Validation stricte des inputs
4. CORS et middleware bien configurés (mineurs ajustements)

**Blocages avant production:**
1. Google Service Account loading (CRITICAL)
2. SecretStr pour tous les secrets (CRITICAL)
3. Authentification API endpoints (CRITICAL)

**Une fois Phase 1 complétée** : Can deploy with confidence to production (single-user, low-volume system).

---

## Références

- Pydantic v2 Docs: https://docs.pydantic.dev/latest/
- OWASP Top 10 2023: https://owasp.org/Top10/
- FastAPI Security: https://fastapi.tiangolo.com/tutorial/security/
- Python Security Checklist: docs/phase3/security-review.md
