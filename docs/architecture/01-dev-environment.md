# Guide d'Environnement de Développement — SAP-Facture

**Auteur**: Winston (DevOps Architect)
**Date**: Mars 2026
**Scope**: Configuration complète pour développement local et déploiement
**Phase**: Phase 3 — Préparation environnement technique

---

## 1. Prérequis

### 1.1 Environnement Local

#### Python
- **Version requise**: Python 3.11+
- **Vérifier installation**:
  ```bash
  python3 --version
  # Output: Python 3.11.x or higher
  ```
- **Installation (Linux/macOS)**:
  ```bash
  # Ubuntu/Debian
  sudo apt update && sudo apt install python3.11 python3.11-venv python3.11-dev

  # macOS (brew)
  brew install python@3.11
  ```

#### Git
- **Installation**:
  ```bash
  # Ubuntu/Debian
  sudo apt install git

  # macOS
  brew install git
  ```

#### Docker & Docker Compose
- **Docker Desktop** (recommandé pour dev local)
  - Linux: `sudo apt install docker.io docker-compose`
  - macOS/Windows: [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Versions**:
  - Docker: 20.10+
  - Docker Compose: 2.0+

### 1.2 Comptes & Credentials Google Cloud

#### Google Cloud Project
1. Créer un projet sur [Google Cloud Console](https://console.cloud.google.com)
   - Nom: `SAP-Facture-Dev` (ou `SAP-Facture-Prod`)
   - ID projet: `sap-facture-xxx`

2. Activer les APIs:
   - Google Sheets API v4
   - Google Drive API
   - Service Accounts API

3. Créer un Service Account:
   ```
   Google Cloud Console → Service Accounts
   → Create Service Account
   → Name: `sap-facture-app`
   → Grant roles: Editor (ou custom: Sheets Editor, Drive Editor)
   → Create JSON key
   ```

4. Télécharger le JSON et sauvegarder:
   ```bash
   # Ne JAMAIS committer cette clé
   cp ~/Downloads/sap-facture-app-key.json ~/.sap/google-credentials.json
   chmod 600 ~/.sap/google-credentials.json
   ```

5. Créer le Google Spreadsheet (voir section 3)

#### Créer et Partager le Spreadsheet
1. Accéder à [Google Sheets](https://sheets.google.com)
2. Créer une nouvelle feuille de calcul: `SAP-Facture-DEV`
3. Copier l'ID depuis l'URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
   ```
4. Partager avec le Service Account:
   - Clic droit sur le sheet → Partager
   - Email du SA: `sap-facture-app@project.iam.gserviceaccount.com`
   - Rôle: Editeur

### 1.3 Comptes API Externes

#### URSSAF Sandbox
1. Contacter support URSSAF pour accès bac à sable
2. Obtenir credentials:
   - `URSSAF_CLIENT_ID`
   - `URSSAF_CLIENT_SECRET`
   - Endpoint: `https://portailapi.urssaf.fr` (ou sandbox)

3. Tester la connexion:
   ```bash
   curl -X POST https://portailapi.urssaf.fr/oauth/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "client_id=YOUR_ID&client_secret=YOUR_SECRET&grant_type=client_credentials"
   ```

#### Swan Sandbox (Bancaire)
1. Créer compte sur [Swan Sandbox](https://sandbox.swan.io)
2. Obtenir `SWAN_API_KEY` depuis le dashboard
3. Créer un compte bancaire de test

#### Compte SMTP
- **Option 1: Gmail** (simple pour dev)
  - Compte Gmail avec App Password (2FA activé)
  - Ajouter dans `.env`: `SMTP_USER=your@gmail.com`, `SMTP_PASSWORD=xxxx`

- **Option 2: Mailtrap.io** (recommandé, gratuit)
  1. Créer compte sur [Mailtrap](https://mailtrap.io)
  2. Créer inbox de test
  3. Copier credentials SMTP (host, port, user, password)

---

## 2. Structure Projet Cible

### 2.1 Arborescence de Fichiers

```
sap-facture/
├── app/
│   ├── __init__.py
│   ├── main.py                          # Point d'entrée FastAPI
│   ├── config.py                        # Configuration (Pydantic Settings)
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── client.py                    # Modèles: Client, ClientStatus
│   │   ├── invoice.py                   # Modèles: Invoice, InvoiceStatus
│   │   ├── transaction.py               # Modèles: Transaction
│   │   ├── reconciliation.py            # Modèles: Reconciliation, MatchResult
│   │   └── notification.py              # Modèles: EmailNotification
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── sheets_adapter.py            # SheetsAdapter (gspread)
│   │   ├── invoice_service.py           # InvoiceService
│   │   ├── client_service.py            # ClientService
│   │   ├── payment_tracker.py           # PaymentTracker (polling)
│   │   ├── bank_reconciliation.py       # BankReconciliation
│   │   ├── notification_service.py      # NotificationService
│   │   └── nova_reporting.py            # NovaReporting
│   │
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── urssaf_client.py             # URSSAFClient (OAuth2 + REST)
│   │   ├── swan_client.py               # SwanClient (GraphQL)
│   │   ├── pdf_generator.py             # PDFGenerator (WeasyPrint)
│   │   └── email_notifier.py            # EmailNotifier (SMTP)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── invoices.py              # GET/POST /api/v1/invoices
│   │   │   ├── clients.py               # GET/POST /api/v1/clients
│   │   │   ├── reconciliation.py        # POST /api/v1/reconcile
│   │   │   ├── metrics.py               # GET /api/v1/metrics
│   │   │   └── health.py                # GET /health
│   │   │
│   │   └── schemas.py                   # Pydantic request/response models
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── routes.py                    # Routes SSR (FastAPI)
│   │   └── templates/
│   │       ├── base.html
│   │       ├── dashboard.html
│   │       ├── invoice_form.html
│   │       ├── reconciliation.html
│   │       ├── clients.html
│   │       └── metrics.html
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   └── commands.py                  # Click CLI commands
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                    # Logging configuré
│       ├── validators.py                # Validations métier
│       └── constants.py                 # Constantes
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Fixtures pytest
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_invoice_service.py
│   │   ├── test_client_service.py
│   │   ├── test_sheets_adapter.py
│   │   ├── test_payment_tracker.py
│   │   └── test_bank_reconciliation.py
│   │
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_urssaf_integration.py   # Mock API URSSAF
│   │   ├── test_swan_integration.py     # Mock API Swan
│   │   └── test_sheets_integration.py   # Mock Google Sheets
│   │
│   └── fixtures/
│       ├── __init__.py
│       ├── sample_invoices.json
│       ├── sample_clients.json
│       └── sample_transactions.json
│
├── scripts/
│   ├── init_sheets.py                   # Script pour initialiser Google Sheets
│   ├── seed_dev_data.py                 # Importer données de test
│   ├── migrate.py                       # Futures migrations (si DB)
│   └── health_check.py                  # Vérifier connexions externes
│
├── .env.example                         # Template variables environnement
├── .env                                 # JAMAIS COMMITTER (local only)
├── .env.test                            # Pour tests
│
├── pyproject.toml                       # Dépendances et config Python
├── Dockerfile                           # Image production
├── Dockerfile.dev                       # Image dev (optional)
├── docker-compose.yml                   # Services (prod)
├── docker-compose.dev.yml               # Services dev
├── .dockerignore                        # Fichiers à ignorer dans image
│
├── Makefile                             # Commandes courantes
├── .github/
│   └── workflows/
│       ├── lint.yml                     # GitHub Actions: ruff + mypy
│       ├── test.yml                     # GitHub Actions: pytest
│       └── deploy.yml                   # GitHub Actions: déploiement
│
├── .pre-commit-config.yaml              # Pre-commit hooks
├── .gitignore                           # Fichiers à ignorer git
├── README.md                            # Documentation générale
├── CONTRIBUTING.md                      # Guide contribution
│
└── docs/
    ├── DEVELOPMENT.md                   # Ce fichier
    ├── API.md                           # Documentation API
    ├── ARCHITECTURE.md                  # Décisions architecture
    └── DEPLOYMENT.md                    # Déploiement production
```

### 2.2 Initialiser le Dépôt Local

```bash
# Cloner le repository
git clone https://github.com/your-org/sap-facture.git
cd sap-facture

# Créer et activer virtualenv
python3.11 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou: venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -U pip setuptools wheel
pip install -e ".[dev]"  # Installe avec dépendances dev

# Configurer pré-commit hooks
pre-commit install
```

---

## 3. Configuration Google Sheets

### 3.1 Créer le Spreadsheet avec 8 Onglets

Exécuter le script d'initialisation:

```bash
python scripts/init_sheets.py
```

Ceci crée automatiquement:
- 8 onglets avec headers
- Formules pour les 5 onglets calculés
- Partage avec Service Account

### 3.2 Structure de Chaque Onglet

#### Onglet 1: **Clients** (Données brutes)
| Colonne | Type | Requis | Notes |
|---------|------|--------|-------|
| A | client_id | Texte | UUID ou NUM séquenciel |
| B | nom | Texte | Nom du client (élève) |
| C | prenom | Texte | Prénom du client |
| D | email | Email | Email pour URSSAF |
| E | telephone | Texte | Optionnel |
| F | adresse | Texte | Rue + numéro |
| G | code_postal | Texte | 5 chiffres |
| H | ville | Texte | Ville |
| I | urssaf_id | Texte | ID technique URSSAF (après inscription) |
| J | statut_urssaf | Texte | BROUILLON / INSCRIT / ERREUR |
| K | date_inscription | Date | ISO8601 |
| L | actif | Bool | TRUE / FALSE |

**Exemple de ligne**:
```
client_001 | Jean | Dupont | jean@ex.com | | 12 rue de Paris | 75001 | Paris | urssaf_123 | INSCRIT | 2026-01-15 | TRUE
```

#### Onglet 2: **Factures** (Données brutes)
| Colonne | Type | Requis | Notes |
|---------|------|--------|-------|
| A | facture_id | Texte | Numéro facture unique |
| B | client_id | Texte | Ref Clients.A |
| C | type_unite | Texte | "HEURE", "JOUR", etc. |
| D | nature_code | Texte | Code nature travail (ex: "course") |
| E | quantite | Nombre | Heures ou jours |
| F | montant_unitaire | Devise | € (ex: 25.50) |
| G | montant_total | Devise | **Formule**: =E2*F2 |
| H | date_debut | Date | Début prestation ISO8601 |
| I | date_fin | Date | Fin prestation ISO8601 |
| J | description | Texte | Description travail |
| K | statut | Texte | BROUILLON / SOUMIS / CREE / EN_ATTENTE / VALIDE / PAYE / EXPIRE / REJETE / RAPPROCHE / ANNULE |
| L | urssaf_demande_id | Texte | ID demande paiement URSSAF |
| M | date_soumission | Date | Quand soumis URSSAF |
| N | date_validation_client | Date | Quand client valide |
| O | date_paiement | Date | Quand URSSAF paie |
| P | pdf_drive_id | Texte | ID fichier Google Drive |

**Exemple**:
```
FAC-2026-001 | client_001 | HEURE | course | 5 | 25.50 | 127.50 | 2026-01-10 | 2026-01-10 | Cours particulier maths | PAYE | urssaf_req_999 | 2026-01-11 | 2026-01-12 | 2026-01-15 | drive_id_xyz
```

#### Onglet 3: **Transactions** (Données brutes)
| Colonne | Type | Notes |
|---------|------|-------|
| A | transaction_id | UUID ou ID Swan |
| B | swan_id | ID depuis API Swan |
| C | date_valeur | Date virement |
| D | montant | Devise (€) |
| E | libelle | Description virement |
| F | type | DEBIT / CREDIT |
| G | source | URSSAF / AUTRE |
| H | facture_id | Ref Factures.A (pour lettrage) |
| I | statut_lettrage | AUTO / A_VERIFIER / PAS_DE_MATCH |
| J | date_import | Date import depuis Swan |

#### Onglet 4: **Lettrage** (Calculé — Formules)
**Note**: Lecture seule (formules server-side)

| Colonne | Formule | Purpose |
|---------|---------|---------|
| A | facture_id | =Factures!A:A |
| B | montant_facture | =Factures!G:G |
| C | txn_id | =IFERROR(INDEX(Transactions!A:A, MATCH(A2, Transactions!H:H, 0)), "") |
| D | txn_montant | =IFERROR(INDEX(Transactions!D:D, MATCH(A2, Transactions!H:H, 0)), "") |
| E | ecart | =ABS(B2 - D2) |
| F | score_confiance | =IF(E2=0, 100, IF(E2<10, 80, IF(E2<50, 50, 0))) |
| G | statut | =IF(C2="", "PAS_DE_MATCH", IF(F2>=80, "AUTO", "A_VERIFIER")) |

#### Onglet 5: **Balances** (Calculé — Formules)
**Note**: Résumé mensuel ou trimestriel

| Colonne | Formule |
|---------|---------|
| A | mois |
| B | nb_factures | =COUNTIFS(Factures!H:H, ">="&DATE(2026, A2, 1), Factures!H:H, "<"&DATE(2026, A2+1, 1)) |
| C | ca_total | =SUMIFS(Factures!G:G, Factures!H:H, ">="&DATE(2026, A2, 1)) |
| D | recu_urssaf | =SUMIFS(Transactions!D:D, Transactions!C:C, ">="&DATE(2026, A2, 1)) |
| E | solde | =D2 - C2 |
| F | nb_non_lettrees | =COUNTIFS(Transactions!I:I, "PAS_DE_MATCH", Transactions!C:C, ">="&DATE(2026, A2, 1)) |
| G | nb_en_attente | =COUNTIFS(Factures!K:K, "EN_ATTENTE", Factures!H:H, ">="&DATE(2026, A2, 1)) |

#### Onglet 6: **Metrics NOVA** (Calculé)
Pour déclaration trimestrielle NOVA

| Colonne | Formule |
|---------|---------|
| A | trimestre |
| B | nb_intervenants | =1 |
| C | heures_effectuees | =SUMIFS(Factures!E:E, Factures!H:H, ">="&DATE(2026, (A2-1)*3+1, 1)) |
| D | nb_particuliers | =COUNTA(UNIQUE(Factures!B:B)) |
| E | ca_trimestre | =SUMIFS(Factures!G:G, Factures!K:K, "PAYE") |
| F | deadline_saisie | =EDATE(DATE(2026, (A2-1)*3+1, 1), 1) |

#### Onglet 7: **Cotisations** (Calculé)
Charges sociales mensuelles (25.8% pour micro-entrepreneur)

| Colonne | Formule |
|---------|---------|
| A | mois |
| B | ca_encaisse | =Balances!C2 |
| C | taux_charges | =0.258 |
| D | montant_charges | =B2 * C2 |
| E | date_limite | =DATE(YEAR(A2), MONTH(A2)+1, 15) |
| F | cumul_ca | =SUM($B$2:B2) |
| G | net_apres_charges | =F2 - SUM($D$2:D2) |

#### Onglet 8: **Fiscal IR** (Calculé)
Simulation impôt annuel (micro-BNC)

| Colonne | Formule |
|---------|---------|
| A | revenu_apprentissage | =0 (ou valeur manuelle) |
| B | seuil_exoneration | =5000 |
| C | ca_micro | =SUM(Balances!C:C) |
| D | abattement_bnc | =C3 * 0.34 |
| E | revenu_imposable | =C3 - D3 - A3 |
| F | tranche_ir | =IF(E3<10225, 0, IF(E3<26070, 0.11, 0.30)) |
| G | taux_marginal | =F3 |
| H | simulation_vl | =E3 * 0.022 |

### 3.3 Partager le Spreadsheet avec Service Account

```bash
# Script pour partager automatiquement
python scripts/init_sheets.py --share-with-sa
```

Ou manuellement:
1. Ouvrir le Spreadsheet dans Google Sheets
2. Clic "Partager" (en haut à droite)
3. Ajouter: `sap-facture-app@project.iam.gserviceaccount.com`
4. Rôle: **Éditeur**

---

## 4. Setup Docker

### 4.1 Dockerfile (Production)

**Fichier**: `Dockerfile`

```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy poetry/requirements
COPY pyproject.toml .

# Build wheels
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -e .

# ===== RUNTIME =====
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Copy wheels from builder
COPY --from=builder /build/wheels /wheels
COPY --from=builder /build/pyproject.toml .

# Install wheels
RUN pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Copy app code
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser scripts/ ./scripts/

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4.2 docker-compose.yml (Production)

**Fichier**: `docker-compose.yml`

```yaml
version: '3.9'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: sap-facture-app
    ports:
      - "8000:8000"
    environment:
      # Credentials Google
      GOOGLE_CREDENTIALS_JSON: ${GOOGLE_CREDENTIALS_JSON}
      SHEETS_SPREADSHEET_ID: ${SHEETS_SPREADSHEET_ID}
      SHEETS_DRIVE_FOLDER_ID: ${SHEETS_DRIVE_FOLDER_ID}

      # URSSAF API
      URSSAF_CLIENT_ID: ${URSSAF_CLIENT_ID}
      URSSAF_CLIENT_SECRET: ${URSSAF_CLIENT_SECRET}
      URSSAF_API_BASE_URL: ${URSSAF_API_BASE_URL}

      # Swan API
      SWAN_API_KEY: ${SWAN_API_KEY}
      SWAN_API_BASE_URL: ${SWAN_API_BASE_URL}

      # Email
      SMTP_HOST: ${SMTP_HOST}
      SMTP_PORT: ${SMTP_PORT}
      SMTP_USER: ${SMTP_USER}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
      SMTP_FROM_EMAIL: ${SMTP_FROM_EMAIL}

      # App
      APP_ENVIRONMENT: production
      APP_LOG_LEVEL: INFO
      APP_DEBUG: "false"

    volumes:
      - ./logs:/app/logs

    restart: unless-stopped

    networks:
      - sap-network

networks:
  sap-network:
    driver: bridge
```

### 4.3 docker-compose.dev.yml (Développement)

**Fichier**: `docker-compose.dev.yml`

```yaml
version: '3.9'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: sap-facture-dev
    ports:
      - "8000:8000"
    environment:
      # Credentials Google
      GOOGLE_CREDENTIALS_JSON: ${GOOGLE_CREDENTIALS_JSON}
      SHEETS_SPREADSHEET_ID: ${SHEETS_SPREADSHEET_ID}
      SHEETS_DRIVE_FOLDER_ID: ${SHEETS_DRIVE_FOLDER_ID}

      # URSSAF API (sandbox)
      URSSAF_CLIENT_ID: ${URSSAF_CLIENT_ID}
      URSSAF_CLIENT_SECRET: ${URSSAF_CLIENT_SECRET}
      URSSAF_API_BASE_URL: https://portailapi.urssaf.fr  # Ou sandbox

      # Swan API (sandbox)
      SWAN_API_KEY: ${SWAN_API_KEY}
      SWAN_API_BASE_URL: https://sandbox.swan.io

      # Email (Mailtrap ou Gmail)
      SMTP_HOST: ${SMTP_HOST}
      SMTP_PORT: ${SMTP_PORT}
      SMTP_USER: ${SMTP_USER}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
      SMTP_FROM_EMAIL: dev@sap-facture.local

      # App
      APP_ENVIRONMENT: development
      APP_LOG_LEVEL: DEBUG
      APP_DEBUG: "true"

    volumes:
      - .:/app
      - /app/venv
      - ./logs:/app/logs

    command: >
      bash -c "
        pip install -e . &&
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
      "

    networks:
      - sap-network

networks:
  sap-network:
    driver: bridge
```

### 4.4 .dockerignore

**Fichier**: `.dockerignore`

```
.git
.gitignore
.github
.pre-commit-config.yaml
.pytest_cache
.mypy_cache
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
venv/
.venv/
.env
.env.local
.env.test
*.db
*.sqlite3
data/
logs/
.coverage
htmlcov/
.DS_Store
*.swp
*.swo
*~
Makefile
README.md
docs/
tests/
```

### 4.5 Dockerfile.dev (Développement avec Reload)

**Fichier**: `Dockerfile.dev`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
RUN pip install --upgrade pip setuptools wheel

# Pre-install dev dependencies
COPY pyproject.toml .
RUN pip install -e ".[dev]"

# Copy source (será overridé par volume)
COPY . .

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Run with hot reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

---

## 5. Configuration Fichier `.env`

### 5.1 Template .env.example

**Fichier**: `.env.example`

```bash
# ===== GOOGLE CLOUD CREDENTIALS =====
# Télécharger depuis Google Cloud Console (Service Account JSON)
# Format: JSON stringifié ou chemin fichier
GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}'
# Alternatif: GOOGLE_CREDENTIALS_PATH=/path/to/creds.json

# Google Sheets ID (extraire de l'URL)
# https://docs.google.com/spreadsheets/d/SHEET_ID/edit
SHEETS_SPREADSHEET_ID=1a2b3c4d5e6f7g8h9i0j

# Folder ID Google Drive pour stocker PDFs factures
SHEETS_DRIVE_FOLDER_ID=0a1b2c3d4e5f6g7h8i

# ===== URSSAF API (SANDBOX) =====
URSSAF_CLIENT_ID=your_client_id
URSSAF_CLIENT_SECRET=your_client_secret
URSSAF_API_BASE_URL=https://portailapi.urssaf.fr
# Pour bac à sable: https://api-sandbox.urssaf.fr

# ===== SWAN BANKING API (SANDBOX) =====
SWAN_API_KEY=your_swan_api_key
SWAN_API_BASE_URL=https://sandbox.swan.io
# Prod: https://api.swan.io

# ===== EMAIL SMTP =====
# Option 1: Gmail (avec App Password)
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your@gmail.com
# SMTP_PASSWORD=your_app_password

# Option 2: Mailtrap (recommandé pour dev)
SMTP_HOST=live.smtp.mailtrap.io
SMTP_PORT=587
SMTP_USER=your_mailtrap_user@example.com
SMTP_PASSWORD=your_mailtrap_password
SMTP_FROM_EMAIL=noreply@sap-facture.local

# ===== APP CONFIGURATION =====
APP_ENVIRONMENT=development
# Options: development, staging, production
APP_LOG_LEVEL=DEBUG
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
APP_DEBUG=true

# API Keys internes
SECRET_KEY=your-secret-key-change-in-prod-min-32-chars

# Polling URSSAF
PAYMENT_POLLING_INTERVAL_HOURS=4

# Timeout API (secondes)
API_TIMEOUT_SECONDS=30

# ===== DATABASE (optionnel, futur) =====
# DATABASE_URL=sqlite:///./sap.db
# DATABASE_URL=postgresql://user:password@localhost:5432/sap_facture

# ===== LOGGING & MONITORING =====
LOG_FILE_PATH=./logs/app.log
LOG_RETENTION_DAYS=30

# Sentry (optionnel, pour error tracking)
# SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0

# ===== FEATURE FLAGS =====
ENABLE_BANK_RECONCILIATION=true
ENABLE_EMAIL_REMINDERS=true
ENABLE_NOVA_REPORTING=true

# ===== CORS (pour frontend local) =====
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 5.2 Charger les Credentials

Dans `app/config.py`:

```python
from __future__ import annotations

import os
import json
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application configuration from environment."""

    # Google Cloud
    google_credentials_json: Optional[str] = None
    sheets_spreadsheet_id: str
    sheets_drive_folder_id: str

    # URSSAF
    urssaf_client_id: str
    urssaf_client_secret: str
    urssaf_api_base_url: str

    # Swan
    swan_api_key: str
    swan_api_base_url: str

    # Email
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    smtp_from_email: str

    # App
    app_environment: str = "development"
    app_log_level: str = "INFO"
    app_debug: bool = False
    secret_key: str = "change-me-in-prod"

    # Polling
    payment_polling_interval_hours: int = 4
    api_timeout_seconds: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def google_credentials(self) -> dict:
        """Parse Google credentials from JSON or file."""
        if self.google_credentials_json:
            # Si c'est un JSON string
            if self.google_credentials_json.startswith("{"):
                return json.loads(self.google_credentials_json)
            # Si c'est un chemin fichier
            else:
                path = Path(self.google_credentials_json)
                if path.exists():
                    return json.load(open(path))
        raise ValueError("GOOGLE_CREDENTIALS_JSON not set or invalid")

settings = Settings()
```

---

## 6. Configuration CI/CD — GitHub Actions

### 6.1 Lint Workflow (.github/workflows/lint.yml)

```yaml
name: Lint & Type Check

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run ruff check
        run: ruff check --fix app/ tests/ scripts/

      - name: Run ruff format
        run: ruff format --check app/ tests/ scripts/

      - name: Run mypy (strict)
        run: mypy --strict app/ tests/

      - name: Create PR comment if issues
        if: failure()
        run: |
          echo "⚠️ Lint or type check failed. Run locally: make lint"
```

### 6.2 Test Workflow (.github/workflows/test.yml)

```yaml
name: Tests & Coverage

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run pytest
        env:
          SHEETS_SPREADSHEET_ID: test-id
          URSSAF_CLIENT_ID: test-id
          URSSAF_CLIENT_SECRET: test-secret
          SWAN_API_KEY: test-key
        run: |
          pytest tests/ \
            --cov=app \
            --cov-fail-under=80 \
            --cov-report=xml \
            --cov-report=term-missing

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

### 6.3 Deploy Workflow (.github/workflows/deploy.yml)

```yaml
name: Deploy

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: |
          docker build -t sap-facture:${{ github.sha }} .
          docker tag sap-facture:${{ github.sha }} sap-facture:latest

      - name: Push to registry
        env:
          DOCKER_REGISTRY: your-registry
          DOCKER_USERNAME: ${{ secrets.DOCKER_USERNAME }}
          DOCKER_PASSWORD: ${{ secrets.DOCKER_PASSWORD }}
        run: |
          echo $DOCKER_PASSWORD | docker login -u $DOCKER_USERNAME --password-stdin
          docker push sap-facture:${{ github.sha }}
          docker push sap-facture:latest

      - name: Deploy (optionnel)
        run: |
          # Script déploiement (VPS, K8s, etc.)
          bash scripts/deploy.sh
```

---

## 7. Pre-Commit Hooks

**Fichier**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic
          - pydantic-settings
          - gspread
          - google-auth-oauthlib
        args: [--strict]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: detect-private-key
      - id: end-of-file-fixer
      - id: trailing-whitespace

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.2
    hooks:
      - id: gitleaks
```

---

## 8. Makefile

**Fichier**: `Makefile`

```makefile
.PHONY: help install dev test lint format type-check clean docker-build docker-run init-sheets seed-data

help:
	@echo "SAP-Facture Development Commands"
	@echo "================================="
	@echo "make install        # Install dependencies (dev + prod)"
	@echo "make dev            # Run FastAPI dev server (hot reload)"
	@echo "make test           # Run pytest avec coverage"
	@echo "make test-watch     # Run pytest en watch mode"
	@echo "make lint           # Lint + format (ruff)"
	@echo "make type-check     # Type checking (mypy strict)"
	@echo "make format         # Auto-format code (ruff)"
	@echo "make clean          # Remove cache, build artifacts"
	@echo "make cli            # Run CLI (sap command)"
	@echo "make docker-build   # Build Docker image"
	@echo "make docker-run     # Run Docker container"
	@echo "make init-sheets    # Initialize Google Sheets"
	@echo "make seed-data      # Seed test data"
	@echo "make health-check   # Check external API connections"

install:
	python -m venv venv 2>/dev/null || true
	. venv/bin/activate && pip install -U pip setuptools wheel
	. venv/bin/activate && pip install -e ".[dev]"
	pre-commit install

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest tests/ --cov=app --cov-fail-under=80 --cov-report=term-missing

test-watch:
	pytest-watch -- tests/ --cov=app

lint:
	ruff check --fix app/ tests/ scripts/
	ruff format app/ tests/ scripts/

format:
	ruff format app/ tests/ scripts/

type-check:
	mypy --strict app/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov dist build *.egg-info
	rm -rf .coverage

cli:
	python -m app.cli.commands

docker-build:
	docker build -t sap-facture:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env sap-facture:latest

docker-dev:
	docker-compose -f docker-compose.dev.yml up

init-sheets:
	python scripts/init_sheets.py

seed-data:
	python scripts/seed_dev_data.py

health-check:
	python scripts/health_check.py
```

---

## 9. Dépendances — pyproject.toml

**Fichier**: `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sap-facture"
version = "0.1.0"
description = "Plateforme facturation URSSAF pour micro-entrepreneurs"
authors = [
    {name = "Jules Willard", email = "contact@sap-facture.com"}
]
requires-python = ">=3.11"
license = {text = "MIT"}

dependencies = [
    # Web Framework
    "fastapi==0.109.0",
    "uvicorn[standard]==0.27.0",
    "pydantic==2.5.0",
    "pydantic-settings==2.1.0",

    # Google APIs
    "gspread==6.1.1",
    "google-auth-oauthlib==1.2.0",
    "google-auth-httplib2==0.2.0",
    "google-api-python-client==2.101.0",

    # HTTP Client
    "httpx==0.25.2",
    "aiohttp==3.9.1",

    # PDF Generation
    "weasyprint==60.1",

    # Email
    "aiosmtplib==3.0.1",

    # CLI
    "click==8.1.7",

    # Logging
    "python-json-logger==2.0.7",

    # Data Validation
    "email-validator==2.1.0",

    # Utilities
    "python-dateutil==2.8.2",
    "pytz==2024.1",
]

[project.optional-dependencies]
dev = [
    # Testing
    "pytest==7.4.3",
    "pytest-asyncio==0.23.2",
    "pytest-cov==4.1.0",
    "pytest-watch==4.2.0",
    "pytest-mock==3.12.0",

    # Mocking
    "responses==0.24.1",
    "faker==22.2.0",
    "factory-boy==3.3.0",

    # Linting & Formatting
    "ruff==0.2.0",
    "mypy==1.7.1",
    "mypy-extensions==1.0.0",

    # Type stubs
    "types-python-dateutil==2.8.19.14",

    # Pre-commit
    "pre-commit==3.6.0",

    # Documentation
    "mkdocs==1.5.3",
    "mkdocs-material==9.5.3",
]

[project.scripts]
sap = "app.cli.commands:cli"

[tool.setuptools]
packages = ["app"]

[tool.pytest.ini_options]
minversion = "7.0"
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = """
    -ra
    --strict-markers
    --strict-config
    --cov-branch
    --cov-report=term-missing:skip-covered
"""
markers = [
    "slow: marks tests as slow",
    "integration: marks tests as integration",
    "unit: marks tests as unit",
]

[tool.coverage.run]
branch = true
omit = [
    "tests/*",
    "app/main.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict = true
plugins = ["pydantic.mypy"]

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "C",    # flake8-comprehensions
    "B",    # flake8-bugbear
    "UP",   # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by formatter)
    "B008",  # do not perform function calls in argument defaults
]

[tool.ruff.lint.isort]
known-first-party = ["app"]
```

---

## 10. Commandes Courantes

### Installation & Setup

```bash
# 1. Cloner et setup
git clone https://github.com/your-org/sap-facture.git
cd sap-facture

# 2. Installer dépendances
make install

# 3. Copier et remplir .env
cp .env.example .env
# Éditer .env avec credentials Google, URSSAF, Swan, SMTP

# 4. Initialiser Google Sheets
make init-sheets

# 5. Seed données de test (optionnel)
make seed-data

# 6. Vérifier connexions externes
make health-check
```

### Développement

```bash
# Lancer le serveur dev (hot reload)
make dev
# Accessible: http://localhost:8000

# Tests avec couverture
make test

# Lint + format automatique
make lint
make format

# Type checking
make type-check

# Nettoyer cache
make clean
```

### CLI

```bash
# Créer et soumettre une facture
python -m app.cli.commands submit \
  --client-id client_001 \
  --hours 5 \
  --rate 25.50 \
  --date-start 2026-01-10

# Synchroniser les statuts URSSAF
python -m app.cli.commands sync

# Lancer lettrage bancaire
python -m app.cli.commands reconcile

# Exporter factures en CSV
python -m app.cli.commands export --format csv --output factures.csv
```

### Docker

```bash
# Build image
make docker-build

# Run production container
make docker-run

# Dev avec docker-compose
make docker-dev

# Arrêter services
docker-compose -f docker-compose.dev.yml down
```

---

## 11. Checklist Démarrage

- [ ] Python 3.11+ installé
- [ ] Virtual environment créé et activé
- [ ] Google Cloud project créé, Service Account configuré
- [ ] `.env` rempli avec credentials (Google, URSSAF, Swan, SMTP)
- [ ] Google Spreadsheet créé et partagé avec SA
- [ ] `make install` exécuté sans erreurs
- [ ] `make init-sheets` exécuté (8 onglets créés)
- [ ] `make health-check` réussi (connexions externes OK)
- [ ] `make dev` lance le serveur sans erreurs
- [ ] Tests passent: `make test` (couverture 80%+)
- [ ] Pre-commit hooks configurés: `pre-commit install`
- [ ] Docker build fonctionne: `make docker-build`
- [ ] Documentation lue: `README.md` + `CONTRIBUTING.md`

---

## 12. Dépannage Courant

### Erreur: "ModuleNotFoundError: No module named 'app'"
```bash
# Solution: Réinstaller en mode éditable
pip install -e .
```

### Erreur: "GOOGLE_CREDENTIALS_JSON not valid"
```bash
# Vérifier format du JSON
cat ~/.sap/google-credentials.json | python -m json.tool

# Ou utiliser chemin fichier dans .env:
GOOGLE_CREDENTIALS_PATH=~/.sap/google-credentials.json
```

### Erreur: "gspread.exceptions.APIError: 403 Forbidden"
```bash
# Vérifier: Service Account a accès au Spreadsheet
# Via Google Sheets UI: Partager → ajouter SA email avec rôle Éditeur
```

### Erreur: "URSSAF authentication failed"
```bash
# Vérifier credentials dans .env
# Tester OAuth2 manuellement:
curl -X POST https://portailapi.urssaf.fr/oauth/token \
  -d "client_id=YOUR_ID&client_secret=YOUR_SECRET"
```

### Tests échouent avec "KeyError: SHEETS_SPREADSHEET_ID"
```bash
# Créer .env.test
cp .env.example .env.test
# Remplir avec credentials de test
```

---

## 13. Ressources Externes

- **Google Sheets API**: https://developers.google.com/sheets/api
- **gspread Docs**: https://docs.gspread.org
- **FastAPI**: https://fastapi.tiangolo.com
- **Pydantic**: https://docs.pydantic.dev
- **URSSAF API**: https://portailapi.urssaf.fr (docs)
- **Swan API**: https://docs.swan.io
- **WeasyPrint**: https://weasyprint.org
- **Click CLI**: https://click.palletsprojects.com

---

**Document Version**: 1.0
**Dernière mise à jour**: Mars 2026
**Mainteneur**: Winston (BMAD DevOps Architect)
