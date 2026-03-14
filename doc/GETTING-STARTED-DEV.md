# Getting Started - SAP-Facture Development

**Pour**: Développeur assigné à SAP-Facture
**De**: Winston (System Architect)
**Objective**: Lancer dev en 1-2 semaines basé sur architecture

---

## Phase 0: Setup Initial (30 min)

### 0.1 Créer repo + structure

```bash
cd ~/projects
git init sap-facture
cd sap-facture

# Structure
mkdir -p app/{web/templates,web/static,services,repositories,models,integrations,cli,tasks} \
         alembic/{versions} \
         tests \
         storage/{pdfs,logos,exports} \
         data \
         scripts \
         docs

touch .gitignore Dockerfile docker-compose.yml pyproject.toml README.md
```

### 0.2 `.gitignore`

```
# Environment
.env
.env.local
.env.*.local

# Database
*.db
*.sqlite
*.sqlite3
data/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
.venv/
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Storage
storage/pdfs/*
storage/logos/*
storage/exports/*
!storage/pdfs/.gitkeep
!storage/logos/.gitkeep
!storage/exports/.gitkeep

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db
```

### 0.3 `pyproject.toml`

```toml
[tool.poetry]
name = "sap-facture"
version = "0.1.0"
description = "Platform URSSAF pour micro-entrepreneurs SAP"
authors = ["Jules Willard <jules@example.fr>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.109"
uvicorn = "^0.27"
sqlalchemy = "^2.0"
alembic = "^1.13"
pydantic = "^2.5"
pydantic-settings = "^2.1"
httpx = "^0.25"
gql = "^3.4"
cryptography = "^42.0"
weasyprint = "^59.0"
jinja2 = "^3.1"
typer = "^0.9"
apscheduler = "^3.10"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4"
pytest-asyncio = "^0.21"
pytest-cov = "^4.1"
black = "^23.12"
ruff = "^0.1"
mypy = "^1.7"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

### 0.4 Initialiser Poetry

```bash
poetry install
poetry run pip install --upgrade pip
```

---

## Phase 1: Database & Models (1 jour)

### 1.1 SQLAlchemy Base Setup

**`app/database.py`**:

```python
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/sap.db")

# Sync engine for alembic migrations
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 1.2 Models de Base

**`app/models/__init__.py`**:

```python
from .user import User
from .client import Client
from .invoice import Invoice
from .payment_request import PaymentRequest
from .bank_transaction import BankTransaction
from .payment_reconciliation import PaymentReconciliation
from .audit_log import AuditLog
from .email_queue import EmailQueue

__all__ = [
    "User",
    "Client",
    "Invoice",
    "PaymentRequest",
    "BankTransaction",
    "PaymentReconciliation",
    "AuditLog",
    "EmailQueue",
]
```

**`app/models/user.py`** (exemple):

```python
from __future__ import annotations

from sqlalchemy import Column, String, DateTime, Text, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    siren = Column(String(14), unique=True, nullable=False)
    nova = Column(String(20), unique=True, nullable=False)

    # Encrypted fields
    urssaf_client_id = Column(String(500), nullable=True)  # Encrypted
    urssaf_client_secret = Column(String(500), nullable=True)  # Encrypted
    swan_api_key = Column(String(500), nullable=True)  # Encrypted

    logo_file_path = Column(String(500), nullable=True)

    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(TIMESTAMP, nullable=True)  # Soft delete

    # Relationships
    clients = relationship("Client", back_populates="user")
    invoices = relationship("Invoice", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
```

### 1.3 Alembic Setup

```bash
poetry run alembic init -t async alembic
```

**`alembic/env.py`** (à configurer pour SQLite):

```python
# ... standard alembic config

import os
from sqlalchemy import engine_from_config, pool

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = os.getenv("DATABASE_URL", "sqlite:///./data/sap.db")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = os.getenv("DATABASE_URL", "sqlite:///./data/sap.db")
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**Créer migration initiale**:

```bash
poetry run alembic revision --autogenerate -m "Initial schema"
poetry run alembic upgrade head
```

---

## Phase 2: URSSAF Integration (1 jour)

### 2.1 URSSAFClient

**`app/integrations/urssaf_client.py`**:

```python
from __future__ import annotations

import time
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class URSSAFError(Exception):
    """URSSAF API error"""
    pass


class URSSAFClient:
    """URSSAF Tiers de Prestation API wrapper"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        sandbox: bool = True
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.sandbox = sandbox
        self.base_url = (
            "https://portailapi-sandbox.urssaf.fr"
            if sandbox
            else "https://portailapi.urssaf.fr"
        )
        self.token: Optional[str] = None
        self.token_expires_at: float = 0

    async def authenticate(self) -> str:
        """Get OAuth2 token"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/oauth/authorize",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            self.token = data["access_token"]
            self.token_expires_at = time.time() + data.get("expires_in", 3600)
            logger.info("URSSAF token refreshed")
            return self.token

    async def _ensure_token(self) -> str:
        """Get token, refresh if expired"""
        if not self.token or time.time() > self.token_expires_at - 60:
            return await self.authenticate()
        return self.token

    async def register_particulier(
        self,
        email: str,
        first_name: str,
        last_name: str
    ) -> dict:
        """Register client with URSSAF"""
        token = await self._ensure_token()
        payload = {
            "email": email,
            "prenom": first_name,
            "nom": last_name
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/particuliers/register",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=30
            )
            if resp.status_code >= 400:
                error_data = resp.json()
                logger.error(
                    f"URSSAF register error: {resp.status_code}",
                    extra={"response": error_data, "email": email}
                )
                raise URSSAFError(f"URSSAF error: {error_data.get('error')}")
            return resp.json()

    async def submit_payment_request(
        self,
        intervenant_code: str,
        particulier_email: str,
        particulier_siret: str,
        date_debut: str,  # YYYY-MM-DD
        date_fin: str,
        montant: float,
        unite_travail: str,  # HEURE or FORFAIT
        code_nature: str,  # 100 for SAP courses
        reference: str,  # invoice number
    ) -> dict:
        """Submit invoice as payment request"""
        token = await self._ensure_token()
        payload = {
            "intervenant": {
                "code": intervenant_code,
                "type": "NOVA"
            },
            "particulier": {
                "email": particulier_email,
                "siret_numero": particulier_siret or ""
            },
            "services": [
                {
                    "date_debut": date_debut,
                    "date_fin": date_fin,
                    "montant": montant,
                    "unite_travail": unite_travail,
                    "code_nature": code_nature,
                }
            ],
            "reference": reference,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/payment-requests",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
                timeout=30
            )
            if resp.status_code >= 400:
                error_data = resp.json()
                logger.error(
                    f"URSSAF submit error: {resp.status_code}",
                    extra={"response": error_data, "reference": reference}
                )
                raise URSSAFError(f"Submission failed: {error_data}")
            return resp.json()

    async def get_payment_status(self, request_id: str) -> dict:
        """Get payment status from URSSAF"""
        token = await self._ensure_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/payment-requests/{request_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()
```

### 2.2 Pydantic Schemas

**`app/schemas/invoice.py`**:

```python
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from enum import Enum


class InvoiceType(str, Enum):
    HEURE = "HEURE"
    FORFAIT = "FORFAIT"


class InvoiceCreateRequest(BaseModel):
    client_id: str = Field(..., min_length=1)
    date_service_from: date
    date_service_to: date
    amount_ttc: float = Field(..., gt=0, le=100000)
    description: str = Field(..., min_length=5, max_length=500)
    invoice_type: InvoiceType

    @field_validator("date_service_to")
    @classmethod
    def validate_dates(cls, v: date, info) -> date:
        from_date = info.data.get("date_service_from")
        if from_date and v < from_date:
            raise ValueError("date_service_to must be >= date_service_from")
        # URSSAF rule: same month only
        if from_date and (v.year, v.month) != (from_date.year, from_date.month):
            raise ValueError("Invoice period must be within 1 calendar month")
        return v


class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    status: str
    amount_ttc: float
    created_at: datetime

    class Config:
        from_attributes = True
```

---

## Phase 3: Web Routes (1 jour)

### 3.1 FastAPI Main App

**`app/main.py`**:

```python
from __future__ import annotations

import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.web.routes import dashboard, invoices, clients

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Init
settings = Settings()
app = FastAPI(title="SAP-Facture", version="0.1.0")

# Static files
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

# Routes
app.include_router(dashboard.router, prefix="", tags=["dashboard"])
app.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
app.include_router(clients.router, prefix="/clients", tags=["clients"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 3.2 Dashboard Route (Exemple)

**`app/web/routes/dashboard.py`**:

```python
from __future__ import annotations

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.invoice_repository import InvoiceRepository
from app.web.templates import render_template

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard"""
    invoice_repo = InvoiceRepository(db)

    invoices = invoice_repo.list_all()
    total_amount = sum(inv.amount_ttc for inv in invoices)

    html = render_template(
        "dashboard.html",
        invoices=invoices,
        total_amount=total_amount,
        invoice_count=len(invoices)
    )
    return HTMLResponse(content=html)
```

---

## Phase 4: Testing Strategy (Done Alongside Dev)

### 4.1 Unit Test Example

**`tests/test_invoice_service.py`**:

```python
import pytest
from datetime import date, datetime
from app.services.invoice_service import InvoiceService
from app.models.invoice import Invoice


@pytest.fixture
def invoice_service():
    """Create service instance"""
    # Mock dependencies if needed
    return InvoiceService()


def test_validate_invoice_happy_path(invoice_service):
    """Test valid invoice passes validation"""
    invoice = {
        "client_id": "client-123",
        "date_service_from": date(2026, 3, 1),
        "date_service_to": date(2026, 3, 31),
        "amount_ttc": 150.0,
        "description": "Cours particuliers Math",
        "type": "HEURE"
    }
    # Should not raise
    result = invoice_service.validate_invoice(invoice)
    assert result is not None


def test_validate_invoice_exceeds_month_raises_error(invoice_service):
    """Test invoice spanning months raises error"""
    invoice = {
        "date_service_from": date(2026, 2, 28),
        "date_service_to": date(2026, 3, 1),
    }
    with pytest.raises(ValueError, match="calendar month"):
        invoice_service.validate_invoice(invoice)


def test_validate_invoice_zero_amount_raises_error(invoice_service):
    """Test zero amount raises error"""
    invoice = {
        "amount_ttc": 0,
    }
    with pytest.raises(ValueError, match="amount"):
        invoice_service.validate_invoice(invoice)
```

---

## Checklist de Démarrage (Jour 1)

- [ ] Repo créé + structure
- [ ] Poetry dépendances installées
- [ ] SQLite DB créée (`poetry run alembic upgrade head`)
- [ ] Tous les models ORM créés
- [ ] URSSAFClient testé (sandbox)
- [ ] FastAPI app lance sans erreur
- [ ] Routes basiques répondent (GET /, /health)
- [ ] Tests runners sans erreur

---

## Commandes Utiles

```bash
# Dev local
docker-compose up

# DB migrations
poetry run alembic revision --autogenerate -m "Describe change"
poetry run alembic upgrade head

# Tests
poetry run pytest tests/ -v --cov=app --cov-fail-under=80

# Linting
poetry run ruff check app/ --fix
poetry run black app/

# Type checking
poetry run mypy app/ --strict
```

---

**Next**: Architectu complète en `ARCHITECTURE.md` — consulter pour design detailé.

