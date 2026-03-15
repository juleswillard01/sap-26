# Plan de Déploiement — SAP-Facture

**Auteur**: Winston (BMAD Infrastructure Architect)
**Date**: Mars 2026
**Statut**: Phase 3 — Production Ready
**Scope**: Monolithe FastAPI, Google Sheets backend, trois environnements (Dev/Staging/Prod)

---

## Table des Matières

1. [Architecture de Déploiement](#architecture-de-déploiement)
2. [Environnements](#environnements)
3. [Configuration par Environnement](#configuration-par-environnement)
4. [Procédure de Déploiement](#procédure-de-déploiement)
5. [Monitoring et Alerting](#monitoring-et-alerting)
6. [Backup et Disaster Recovery](#backup-et-disaster-recovery)
7. [Sécurité Infrastructure](#sécurité-infrastructure)
8. [Checklist Déploiement](#checklist-déploiement)

---

## Architecture de Déploiement

### Vue d'Ensemble

```
┌────────────────────────────────────────────────────────────────┐
│ DÉVELOPPEUR (Local)                                            │
│ ┌──────────────────────────────────────────┐                 │
│ │ Docker Compose (Dev Environment)         │                 │
│ │ - FastAPI app (port 8000)                │                 │
│ │ - Google Sheets API (non-containerisé)   │                 │
│ │ - LocalStack (optional S3 testing)       │                 │
│ └──────────────────────────────────────────┘                 │
└────────────────────────────────────────────────────────────────┘
                          ↓ (git push)
┌────────────────────────────────────────────────────────────────┐
│ VPS STAGING (Ubuntu 22.04 LTS, t2.micro)                      │
│ ┌──────────────────────────────────────────┐                 │
│ │ Docker Container (FastAPI)               │                 │
│ │ - Image: ghcr.io/juleswillard/sap:edge   │                 │
│ │ - Port: 8000 (internal only)             │                 │
│ ├──────────────────────────────────────────┤                 │
│ │ Nginx Reverse Proxy                      │                 │
│ │ - Port: 80 → 443 redirect                │                 │
│ │ - Port: 443 (SSL/TLS)                    │                 │
│ │ - Domain: staging.sap-facture.fr         │                 │
│ ├──────────────────────────────────────────┤                 │
│ │ Systemd Service (sap-staging.service)    │                 │
│ │ - Auto-restart on failure                │                 │
│ │ - Health check (GET /health)             │                 │
│ ├──────────────────────────────────────────┤                 │
│ │ Monitoring                               │                 │
│ │ - Logs JSON → /var/log/sap/              │                 │
│ │ - Prometheus metrics (port 9090)         │                 │
│ └──────────────────────────────────────────┘                 │
│ ┌──────────────────────────────────────────┐                 │
│ │ External Integrations (Sandbox)          │                 │
│ │ - URSSAF API (sandbox mode)              │                 │
│ │ - Google Sheets (test spreadsheet)       │                 │
│ │ - SMTP (test recipient)                  │                 │
│ └──────────────────────────────────────────┘                 │
└────────────────────────────────────────────────────────────────┘
                          ↓ (manual promotion)
┌────────────────────────────────────────────────────────────────┐
│ VPS PRODUCTION (Ubuntu 22.04 LTS, t2.small)                   │
│ ┌──────────────────────────────────────────┐                 │
│ │ Docker Container (FastAPI)               │                 │
│ │ - Image: ghcr.io/juleswillard/sap:v1.x   │                 │
│ │ - Port: 8000 (internal only)             │                 │
│ ├──────────────────────────────────────────┤                 │
│ │ Nginx Reverse Proxy                      │                 │
│ │ - Port: 80 → 443 redirect                │                 │
│ │ - Port: 443 (SSL/TLS Let's Encrypt)      │                 │
│ │ - Domain: app.sap-facture.fr             │                 │
│ ├──────────────────────────────────────────┤                 │
│ │ Systemd Service (sap-prod.service)       │                 │
│ │ - Auto-restart on failure                │                 │
│ │ - Health check (GET /health)             │                 │
│ │ - Graceful shutdown (30s timeout)        │                 │
│ ├──────────────────────────────────────────┤                 │
│ │ Monitoring & Alerting                    │                 │
│ │ - Logs JSON → /var/log/sap/              │                 │
│ │ - Prometheus metrics (port 9090)         │                 │
│ │ - Uptime monitoring (external)           │                 │
│ ├──────────────────────────────────────────┤                 │
│ │ Security                                 │                 │
│ │ - UFW firewall (ssh, http, https only)   │                 │
│ │ - Fail2ban (ssh + API rate limiting)     │                 │
│ │ - SSH key-only auth                      │                 │
│ │ - Non-root docker user                   │                 │
│ └──────────────────────────────────────────┘                 │
│ ┌──────────────────────────────────────────┐                 │
│ │ External Integrations (Production)       │                 │
│ │ - URSSAF API (production mode)           │                 │
│ │ - Google Sheets (spreadsheet prod)       │                 │
│ │ - Swan API (live account)                │                 │
│ │ - SMTP (transactionnel sender)           │                 │
│ └──────────────────────────────────────────┘                 │
└────────────────────────────────────────────────────────────────┘
```

### Composants Clés

#### 1. FastAPI Monolith
- Framework: FastAPI 0.100+
- ASGI server: Uvicorn (production)
- Port interne: 8000
- Workers: 4 (t2.small)
- Health endpoint: `GET /health` → `{"status": "healthy", "timestamp": "2026-03-15T10:00:00Z"}`

#### 2. Nginx Reverse Proxy
- Rôle: TLS termination, compression, caching
- Config: `/etc/nginx/sites-available/sap-{env}.conf`
- SSL: Let's Encrypt (Certbot)
- Ports: 80 (HTTP redirect) + 443 (HTTPS)

#### 3. Systemd Service
- File: `/etc/systemd/system/sap-{env}.service`
- User: `sap` (non-root)
- Restart policy: `always` (auto-restart on crash)
- Health check via `/health` endpoint

#### 4. Docker Container
- Image: `ghcr.io/juleswillard/sap:latest` (dev/staging), `ghcr.io/juleswillard/sap:vX.Y.Z` (prod)
- Base: Python 3.11-slim
- User: Non-root (`app:app`)
- Volumes: `.env` secrets, logs

---

## Environnements

### Spécifications VPS

| Aspect | Dev (Local) | Staging | Production |
|--------|-----------|---------|-----------|
| **Platform** | Docker Compose | VPS Ubuntu 22.04 | VPS Ubuntu 22.04 |
| **Specs** | Laptop | t2.micro (1GB RAM, 1vCPU) | t2.small (2GB RAM, 2vCPU) |
| **Disk** | Local | 30 GB SSD | 50 GB SSD |
| **OS** | macOS/Linux | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| **FastAPI Workers** | 1 | 2 | 4 |
| **URSSAF API** | Sandbox | Sandbox | Production |
| **Google Sheets** | Test sheet | Test sheet | Production sheet |
| **Domain** | localhost:8000 | staging.sap-facture.fr | app.sap-facture.fr |
| **SSL** | Self-signed | Let's Encrypt | Let's Encrypt |
| **Backup** | Manual | Hourly snapshot | Daily snapshot |

---

## Configuration par Environnement

### Hiérarchie des Secrets

```
.env.local          (Dev, jamais commité)
.env.staging        (Staging, jamais commité)
.env.production     (Production, jamais commité)
```

#### Template .env

```bash
# ==========================================
# APP CORE
# ==========================================
APP_ENV=development|staging|production
APP_DEBUG=true|false
APP_HOST=0.0.0.0
APP_PORT=8000
APP_LOG_LEVEL=DEBUG|INFO|WARNING|ERROR
SECRET_KEY=<random-32-bytes-hex>

# ==========================================
# URSSAF API (OAuth2)
# ==========================================
URSSAF_ENVIRONMENT=sandbox|production
URSSAF_CLIENT_ID=xxx
URSSAF_CLIENT_SECRET=xxx
URSSAF_API_BASE_URL=https://portailapi.sandbox.urssaf.fr|https://portailapi.urssaf.fr
URSSAF_OAUTH_TOKEN_URL=${URSSAF_API_BASE_URL}/oauth/token

# ==========================================
# SWAN API (GraphQL)
# ==========================================
SWAN_API_KEY=xxx
SWAN_API_BASE_URL=https://api.swan.io
SWAN_ACCOUNT_ID=xxx

# ==========================================
# GOOGLE SHEETS & DRIVE
# ==========================================
# Service Account credentials (JSON base64)
GOOGLE_CREDENTIALS_JSON=<service-account-json-base64>
GOOGLE_SPREADSHEET_ID=xxx  (test ou prod sheet)
GOOGLE_DRIVE_FOLDER_ID=xxx (where PDFs stored)

# ==========================================
# SMTP (Email)
# ==========================================
SMTP_HOST=smtp.gmail.com|smtp.mailtrap.io
SMTP_PORT=587|2525
SMTP_USER=xxx@gmail.com
SMTP_PASSWORD=<app-password>
SMTP_FROM=facturation@sap-facture.fr
SMTP_FROM_NAME=SAP-Facture

# ==========================================
# MONITORING & LOGGING
# ==========================================
SENTRY_DSN=https://xxx@sentry.io/yyy  (production only)
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# ==========================================
# FERNET KEY (for encrypting secrets in DB, if needed)
# ==========================================
FERNET_KEY=<base64-fernet-key>

# ==========================================
# REDIS (optional, for caching & sessions)
# ==========================================
REDIS_URL=redis://localhost:6379/0

# ==========================================
# BACKUP & DATABASE
# ==========================================
# Google Sheets backup (version history)
BACKUP_ENABLED=true
BACKUP_RETENTION_DAYS=30
```

### Génération Secrets Sécurisée

```bash
# Secret Key (32 bytes = 64 hex chars)
python -c "import secrets; print(secrets.token_hex(32))"
# Output: ab12cd34ef56...

# Fernet Key (symmetric encryption)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Output: base64-encoded-fernet-key
```

### Par Environnement

#### Development (.env.local)

```bash
APP_ENV=development
APP_DEBUG=true
APP_LOG_LEVEL=DEBUG
SECRET_KEY=dev-key-insecure
URSSAF_ENVIRONMENT=sandbox
URSSAF_CLIENT_ID=dev-sandbox-id
GOOGLE_SPREADSHEET_ID=1Hd3xxxxxTEST_SHEET_ID
SMTP_HOST=smtp.mailtrap.io
SMTP_USER=devtest@mailtrap.io
SENTRY_DSN=  (empty)
```

#### Staging (.env.staging)

```bash
APP_ENV=staging
APP_DEBUG=false
APP_LOG_LEVEL=INFO
SECRET_KEY=<generate-via-secrets.token_hex>
URSSAF_ENVIRONMENT=sandbox
URSSAF_CLIENT_ID=staging-sandbox-id
GOOGLE_SPREADSHEET_ID=1Hd3xxxxxSTAGING_SHEET_ID
SMTP_HOST=smtp.gmail.com
SMTP_USER=staging-test@gmail.com
SENTRY_DSN=https://staging-key@sentry.io
```

#### Production (.env.production)

```bash
APP_ENV=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO
SECRET_KEY=<generate-via-secrets.token_hex>
URSSAF_ENVIRONMENT=production
URSSAF_CLIENT_ID=prod-client-id
GOOGLE_SPREADSHEET_ID=1Hd3xxxxxPROD_SHEET_ID
SMTP_HOST=smtp.gmail.com
SMTP_USER=facturation@sap-facture.fr
SENTRY_DSN=https://prod-key@sentry.io
```

### Google Sheets par Environnement

| Environnement | Spreadsheet ID | Accès | Contenu |
|---|---|---|---|
| **Dev** | Test sheet (local) | Service Account + Jules | Factures test, clients test |
| **Staging** | Staging spreadsheet | Service Account + Jules | Simulation production, données test |
| **Prod** | Production spreadsheet | Service Account (Jules read-only) | Données réelles, backup auto |

**Procédure Setup Google Sheets** :
1. Créer Google Cloud Project
2. Activer APIs : Sheets v4, Drive v3
3. Créer Service Account + JSON key
4. Partager spreadsheet avec `sa@project.iam.gserviceaccount.com`
5. Encoder JSON en base64 → `.env` (`GOOGLE_CREDENTIALS_JSON`)

---

## Procédure de Déploiement

### 1. Préparation VPS

#### 1.1 Initialisation Ubuntu

```bash
#!/bin/bash
# run as root

# Update system
apt-get update && apt-get upgrade -y

# Install dependencies
apt-get install -y \
    curl wget git \
    docker.io docker-compose-v2 \
    nginx \
    certbot python3-certbot-nginx \
    fail2ban ufw \
    curl jq

# Enable Docker
systemctl enable docker
systemctl start docker

# Add non-root user for SAP
useradd -m -s /bin/bash sap
usermod -aG docker sap

# Enable firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp       # SSH
ufw allow 80/tcp       # HTTP
ufw allow 443/tcp      # HTTPS
ufw enable

# Configure SSH (key-only auth)
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd

echo "✓ VPS initialized"
```

#### 1.2 Structure Répertoires

```bash
# As user 'sap'
mkdir -p /home/sap/sap-facture/{app,config,logs,backups}
mkdir -p /var/log/sap
chmod 755 /var/log/sap
chown sap:sap /var/log/sap

echo "✓ Directories created"
```

### 2. Build & Push Docker Image

#### 2.1 Dockerfile (dans root du repo)

```dockerfile
# multi-stage build
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Create non-root user
RUN useradd -m -u 1000 app && chown -R app:app /app

# Copy application code
COPY --chown=app:app . .

# Switch to non-root user
USER app

# Add local python to PATH
ENV PATH=/root/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run FastAPI via Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### 2.2 Build & Push

```bash
#!/bin/bash
# Run from repository root

VERSION=$(git describe --tags --always)
IMAGE_NAME="ghcr.io/juleswillard/sap:${VERSION}"

# Login to GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USER --password-stdin

# Build image
docker build -t ${IMAGE_NAME} -t ghcr.io/juleswillard/sap:latest .

# Push to registry
docker push ${IMAGE_NAME}
docker push ghcr.io/juleswillard/sap:latest

echo "✓ Image pushed: ${IMAGE_NAME}"
```

### 3. Déploiement sur VPS

#### 3.1 Systemd Service File

**File**: `/etc/systemd/system/sap-staging.service`

```ini
[Unit]
Description=SAP-Facture Staging Service
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=sap
Group=docker
WorkingDirectory=/home/sap/sap-facture

# Pull latest image
ExecStartPre=/usr/bin/docker pull ghcr.io/juleswillard/sap:edge

# Remove old container
ExecStartPre=/usr/bin/docker rm -f sap-staging || true

# Start container
ExecStart=/usr/bin/docker run \
  --name sap-staging \
  --restart=no \
  --net=host \
  --env-file=/home/sap/sap-facture/.env.staging \
  --log-driver=json-file \
  --log-opt=max-size=50m \
  --log-opt=max-file=10 \
  -v /var/log/sap:/app/logs \
  ghcr.io/juleswillard/sap:edge

# Stop container
ExecStop=/usr/bin/docker stop -t 30 sap-staging

# Restart policy
Restart=on-failure
RestartSec=5s
StartLimitInterval=60s
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
```

**File**: `/etc/systemd/system/sap-prod.service`

```ini
[Unit]
Description=SAP-Facture Production Service
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=sap
Group=docker
WorkingDirectory=/home/sap/sap-facture

# Pull versioned image (manual tag promotion)
ExecStartPre=/usr/bin/docker pull ghcr.io/juleswillard/sap:v1.0.0

# Remove old container
ExecStartPre=/usr/bin/docker rm -f sap-prod || true

# Start container with health check
ExecStart=/usr/bin/docker run \
  --name sap-prod \
  --restart=no \
  --net=host \
  --env-file=/home/sap/sap-facture/.env.production \
  --log-driver=json-file \
  --log-opt=max-size=100m \
  --log-opt=max-file=10 \
  -v /var/log/sap:/app/logs \
  ghcr.io/juleswillard/sap:v1.0.0

ExecStop=/usr/bin/docker stop -t 30 sap-prod

Restart=on-failure
RestartSec=10s
StartLimitInterval=120s
StartLimitBurst=3

[Install]
WantedBy=multi-user.target
```

#### 3.2 Nginx Configuration

**File**: `/etc/nginx/sites-available/sap-staging.conf`

```nginx
# HTTP → HTTPS redirect
server {
    listen 80;
    server_name staging.sap-facture.fr;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name staging.sap-facture.fr;

    # SSL certificates (Let's Encrypt via Certbot)
    ssl_certificate /etc/letsencrypt/live/staging.sap-facture.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/staging.sap-facture.fr/privkey.pem;

    # SSL security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;

    # Logging
    access_log /var/log/nginx/sap-staging-access.log;
    error_log /var/log/nginx/sap-staging-error.log;

    # Upstream FastAPI
    upstream sap_backend {
        server 127.0.0.1:8000;
    }

    # Health check endpoint (no logging)
    location /health {
        access_log off;
        proxy_pass http://sap_backend;
    }

    # API endpoints
    location /api/ {
        proxy_pass http://sap_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }

    # Static files (if any)
    location /static/ {
        alias /home/sap/sap-facture/app/static/;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # Root
    location / {
        proxy_pass http://sap_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**File**: `/etc/nginx/sites-available/sap-prod.conf` (identique, domain changé)

```nginx
# Même structure que staging, mais domain = app.sap-facture.fr
```

#### 3.3 Activation Nginx + SSL

```bash
#!/bin/bash

# Enable site
ln -sf /etc/nginx/sites-available/sap-staging.conf /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/sap-prod.conf /etc/nginx/sites-enabled/

# Get SSL certificate via Certbot
certbot certonly --nginx \
  -d staging.sap-facture.fr \
  -d app.sap-facture.fr \
  --non-interactive \
  --agree-tos \
  -m admin@sap-facture.fr

# Test Nginx config
nginx -t

# Reload Nginx
systemctl reload nginx

# Auto-renew certificates
systemctl enable certbot.timer
systemctl start certbot.timer

echo "✓ Nginx configured, SSL enabled"
```

### 4. Déploiement Workflow

```bash
#!/bin/bash
# Deploy script (run from dev machine)

set -e

ENVIRONMENT=${1:-staging}  # staging or production
VERSION=$(git describe --tags --always)

echo "Deploying SAP-Facture $VERSION to $ENVIRONMENT..."

# 1. Build Docker image
echo "Building Docker image..."
docker build -t ghcr.io/juleswillard/sap:${VERSION} .

# 2. Push to registry
echo "Pushing image to registry..."
docker push ghcr.io/juleswillard/sap:${VERSION}

if [ "$ENVIRONMENT" = "staging" ]; then
    docker push ghcr.io/juleswillard/sap:edge
    IMAGE_TAG=edge
elif [ "$ENVIRONMENT" = "production" ]; then
    docker push ghcr.io/juleswillard/sap:${VERSION}
    IMAGE_TAG=${VERSION}
fi

# 3. SSH to VPS
echo "Deploying to VPS..."
ssh sap@staging.sap-facture.fr "
    set -e
    cd /home/sap/sap-facture

    # Pull latest .env
    # (ou sync via git si .env en gitignore local)

    # Restart service
    sudo systemctl restart sap-${ENVIRONMENT}

    # Wait for health check
    for i in {1..30}; do
        if curl -f http://localhost/health > /dev/null 2>&1; then
            echo '✓ Service healthy'
            exit 0
        fi
        echo "Waiting for service... ($i/30)"
        sleep 1
    done

    echo '✗ Service failed health check'
    exit 1
"

echo "✓ Deployment complete: $ENVIRONMENT"
```

### 5. Rollback Procedure

```bash
#!/bin/bash
# Rollback to previous version

ENVIRONMENT=${1:-staging}
PREVIOUS_VERSION=$(git describe --tags --abbrev=0)

echo "Rolling back $ENVIRONMENT to $PREVIOUS_VERSION..."

ssh sap@${ENVIRONMENT}.sap-facture.fr "
    sudo systemctl stop sap-${ENVIRONMENT}
    docker pull ghcr.io/juleswillard/sap:${PREVIOUS_VERSION}
    docker rm -f sap-${ENVIRONMENT}
    sudo systemctl start sap-${ENVIRONMENT}

    # Health check
    sleep 5
    curl -f http://localhost/health
    echo '✓ Rollback complete'
"
```

---

## Monitoring et Alerting

### Endpoint Health Check

**Endpoint**: `GET /health`

```json
{
  "status": "healthy",
  "timestamp": "2026-03-15T10:00:00Z",
  "uptime_seconds": 3600,
  "services": {
    "google_sheets": "ok",
    "urssaf_api": "ok",
    "swan_api": "ok",
    "smtp": "ok"
  }
}
```

**Implémentation FastAPI** :

```python
from datetime import datetime
from fastapi import APIRouter

router = APIRouter()
start_time = datetime.utcnow()

@router.get("/health")
async def health_check():
    now = datetime.utcnow()
    uptime = (now - start_time).total_seconds()

    return {
        "status": "healthy",
        "timestamp": now.isoformat() + "Z",
        "uptime_seconds": int(uptime),
        "services": {
            "google_sheets": check_google_sheets(),
            "urssaf_api": check_urssaf(),
            "swan_api": check_swan(),
            "smtp": check_smtp(),
        }
    }
```

### Logs Structurés (JSON)

**Location**: `/var/log/sap/app.log`

```python
import logging
import json
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "extra": getattr(record, "extra", {}),
        })

logger = logging.getLogger(__name__)
handler = logging.FileHandler("/var/log/sap/app.log")
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)

# Usage
logger.info("Invoice created", extra={"invoice_id": "INV-001", "client_id": "CLI-001"})
```

### Prometheus Metrics

**Endpoint**: `GET /metrics` (port 9090)

```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
invoices_created = Counter("invoices_created_total", "Total invoices created")
urssaf_api_latency = Histogram("urssaf_api_latency_seconds", "URSSAF API latency")
sheets_api_calls = Counter("sheets_api_calls_total", "Total Sheets API calls", ["method", "status"])
current_uptime = Gauge("app_uptime_seconds", "Application uptime in seconds")

# Usage
@app.post("/invoices")
async def create_invoice():
    with urssaf_api_latency.time():
        # Call URSSAF API
        pass
    invoices_created.inc()
```

### Alertes Clés

| Alerte | Condition | Action |
|--------|-----------|--------|
| **API URSSAF Down** | Health check URSSAF fails for 5min | Email Jules + Sentry |
| **Google Sheets Quota Exceeded** | 429 error on Sheets API | Log warning + retry backoff |
| **SSL Certificate Expires** | Let's Encrypt cert < 30 days | Auto-renew via Certbot |
| **Disk Space Critical** | < 10% free | Email + log alert |
| **Service Down** | Systemd restart > 3x in 60s | Email alert + rollback |
| **High Memory Usage** | > 80% RAM | Monitor + auto-scale if needed |

**Implémentation Sentry** :

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,  # 10% de traces
    environment=os.getenv("APP_ENV"),
)
```

### Uptime Monitoring Externe

Utiliser Uptime Robot ou Pingdom pour monitor `/health` endpoint :
- Interval: Toutes les 5 minutes
- Timeout: 10 secondes
- Alertes: Email si down 10 minutes

---

## Backup et Disaster Recovery

### Backup Strategy

#### 1. Google Sheets (Source of Truth)

**Backup natif** : Version history automatique par Google Sheets
- Retention: 100 versions par feuille (configurable)
- RTO (Recovery Time Objective): < 1 minute (restore depuis UI)
- RPO (Recovery Point Objective): Réel-time (chaque modification)

**Procédure manuelle** :
```bash
#!/bin/bash
# Export spreadsheet to CSV weekly (for archival)

python3 << 'EOF'
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Authenticate
creds = Credentials.from_service_account_file("/path/to/service-account.json")
client = gspread.authorize(creds)
sheet = client.open_by_key(SPREADSHEET_ID)

# Export each worksheet
for ws in sheet.worksheets():
    values = ws.get_all_values()
    csv_path = f"/home/sap/backups/{ws.title}_{datetime.now().date()}.csv"

    with open(csv_path, "w") as f:
        for row in values:
            f.write(",".join(row) + "\n")

    print(f"✓ Exported {ws.title}")
EOF
```

**Cron job** (hebdomadaire) :
```bash
0 2 * * 0 /home/sap/scripts/backup-sheets.sh >> /var/log/sap/backup.log 2>&1
```

#### 2. Secrets & Configuration

**Backup .env files** :
```bash
#!/bin/bash
# Encrypted backup of .env files

gpg --symmetric --cipher-algo AES256 /home/sap/sap-facture/.env.production
# Output: .env.production.gpg

# Store encrypted backup offline or in secure cloud storage
# (AWS Secrets Manager, Google Secret Manager, etc.)
```

#### 3. Application Database (n/a pour MVP)

Comme on utilise Google Sheets, pas de DB locale à backuper.

#### 4. Restore Procedure

**Scenario 1 : Service crash**
```bash
# Automatic: systemd restart
sudo systemctl restart sap-prod

# Manual (if needed)
docker pull ghcr.io/juleswillard/sap:v1.0.0
docker run -d --name sap-prod \
  --env-file /home/sap/sap-facture/.env.production \
  ghcr.io/juleswillard/sap:v1.0.0
```

**Scenario 2 : Data corruption in Sheets**
```bash
# Access Google Sheets version history
# File → Version history → Restore desired version
# RTO: < 1 minute
```

**Scenario 3 : Complete VPS loss**
```bash
# Provision new VPS, repeat setup steps
# Restore .env from encrypted backup
# Restore application from git repository
# Re-run docker deployment script
# RTO: ~15 minutes
```

---

## Sécurité Infrastructure

### 1. Firewall (UFW)

```bash
# Default policy
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (rate limited)
ufw allow 22/tcp comment "SSH"

# Allow HTTP/HTTPS
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"

# Deny Prometheus (internal only)
ufw deny 9090/tcp

# Enable
ufw enable
```

### 2. Fail2ban (Rate Limiting)

**File**: `/etc/fail2ban/jail.local`

```ini
[DEFAULT]
bantime = 600  # 10 minutes
findtime = 300  # 5 minutes
maxretry = 5

[sshd]
enabled = true
filter = sshd
logpath = /var/log/auth.log

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
```

**Activate** :
```bash
systemctl restart fail2ban
fail2ban-client status
```

### 3. SSH Key-Only Authentication

```bash
# On VPS (as root)
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
systemctl restart sshd

# On developer laptop
ssh-keygen -t ed25519 -C "deployment@sap-facture"
ssh-copy-id -i ~/.ssh/id_ed25519.pub sap@staging.sap-facture.fr
```

### 4. Docker Security

```bash
# Run FastAPI as non-root user (app:app in container)
# Container has read-only root filesystem (where possible)
# No privileged mode
# Resource limits (via docker run)

docker run \
  --user 1000:1000 \
  --read-only \
  --tmpfs /tmp \
  --memory 512m \
  --cpus 1 \
  ghcr.io/juleswillard/sap:latest
```

### 5. Secrets Management

**Stockage secrets** :
- `.env` files → `/home/sap/sap-facture/.env.*`
- Permissions: `600` (sap user only)
- Never commit to git
- Backup encrypted offline

**Rotation secrets** :
- URSSAF_CLIENT_SECRET: Tous les 90 jours
- GOOGLE_CREDENTIALS_JSON: Tous les 6 mois
- SMTP_PASSWORD: Tous les 6 mois
- SECRET_KEY: Jamais (application redeployée)

### 6. HTTPS/TLS

- Protocol: TLSv1.2+
- Ciphers: `HIGH:!aNULL:!MD5`
- HSTS: `Strict-Transport-Security: max-age=31536000`
- Certificate: Let's Encrypt (auto-renew via Certbot)

**Nginx configuration** (déjà dans section Nginx ci-dessus)

---

## Checklist Déploiement

### Pré-Déploiement Staging

- [ ] Tests unitaires passent (`pytest --cov`)
- [ ] Linting OK (`ruff check`, `mypy --strict`)
- [ ] Build Docker successful
- [ ] Image pushed to GitHub Container Registry
- [ ] `.env.staging` créé avec test credentials URSSAF sandbox
- [ ] Test Google Sheets spreadsheet accessible
- [ ] SMTP credentials valides (test mailtrap ou Gmail app password)

### Déploiement Staging

- [ ] VPS infrastructure ready (Ubuntu 22.04, Docker, Nginx installed)
- [ ] Systemd service file created (`sap-staging.service`)
- [ ] Nginx config created + SSL certificate provisioned
- [ ] Deploy script executed (`bash deploy.sh staging`)
- [ ] Health check passes (`curl https://staging.sap-facture.fr/health`)
- [ ] Dashboard accessible via browser
- [ ] Create test invoice via UI
- [ ] Verify invoice creation in test Google Sheets
- [ ] Test CLI commands (`sap submit`, `sap sync`)
- [ ] Email reminders working (test SMTP)
- [ ] Logs viewable at `/var/log/sap/app.log`
- [ ] Prometheus metrics accessible at `/metrics`

### Pré-Déploiement Production

- [ ] Manual testing complete in Staging (minimum 1 week)
- [ ] All known issues resolved
- [ ] Performance benchmarks acceptable (< 500ms response time)
- [ ] `.env.production` créé avec credentials production
- [ ] Production Google Sheets spreadsheet created and shared with Service Account
- [ ] Production URSSAF credentials obtained (client_id, client_secret)
- [ ] Production SMTP credentials (transactional sender)
- [ ] Sentry DSN configured for production
- [ ] Backup strategy tested (Google Sheets + encrypted .env backup)

### Déploiement Production

- [ ] Production VPS provisioned (t2.small)
- [ ] Systemd service file created (`sap-prod.service`)
- [ ] Nginx config + SSL certificate provisioned
- [ ] Deploy script executed (`bash deploy.sh production`)
- [ ] Health check passes
- [ ] Test invoice creation (with real URSSAF sandbox → prod)
- [ ] Verify data in production Google Sheets
- [ ] Monitor logs and metrics for 24 hours
- [ ] Test rollback procedure
- [ ] Failover/disaster recovery plan documented
- [ ] Team trained on deployment/rollback procedures

### Post-Déploiement Continu

- [ ] Weekly backup of Google Sheets exports to CSV
- [ ] Monthly certificate renewal check (Let's Encrypt)
- [ ] Quarterly secret rotation (URSSAF, Google, SMTP)
- [ ] Monthly security updates (`apt-get update && apt-get upgrade`)
- [ ] Quarterly disaster recovery drill (restore from backup)
- [ ] Annual infrastructure review (specs, costs, scaling)

---

## Appendix A — Scripts Utiles

### Script: Health Check Loop

```bash
#!/bin/bash
# monitor-health.sh

ENV=${1:-staging}
DOMAIN="${ENV}.sap-facture.fr"
INTERVAL=${2:-30}

while true; do
    RESPONSE=$(curl -s -w "\n%{http_code}" "https://${DOMAIN}/health")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n1)

    if [ "$HTTP_CODE" = "200" ]; then
        echo "[$(date)] ✓ HEALTHY ($HTTP_CODE)"
    else
        echo "[$(date)] ✗ UNHEALTHY ($HTTP_CODE)"
        echo "$BODY"
    fi

    sleep $INTERVAL
done
```

### Script: Log Tailing

```bash
#!/bin/bash
# tail-logs.sh

ENV=${1:-staging}
tail -f /var/log/sap/${ENV}-app.log | jq .
```

### Script: Metrics Export

```bash
#!/bin/bash
# export-metrics.sh

ENV=${1:-staging}
curl -s "http://localhost:9090/metrics" | \
  grep -E "^sap_" | \
  awk '{print $1 " = " $2}' | \
  sort
```

---

## Appendix B — Architecture Decision Records (ADRs)

### ADR-001 : Google Sheets as Backend

**Status**: ACCEPTED

**Context**: SAP-Facture MVP requires quick iteration with minimal infrastructure. Traditional SQL database would add deployment complexity and cost.

**Decision**: Use Google Sheets as single source of truth via gspread library.

**Consequences**:
- ✅ Zero infrastructure cost (free tier sufficient)
- ✅ Version history (automatic backup)
- ✅ Jules can edit data directly in Sheets
- ✅ Fast iteration (no migrations)
- ❌ Limited to ~50 factures/mois (scalability limit ~1000 factures/an)
- ❌ No transactions ACID (mitigated by optimistic locking)
- ❌ Latency 200-500ms vs SQL 10-50ms

**Migration Path**: If scaling required (>1000 invoices/year), migrate to PostgreSQL while keeping Sheets for business users.

### ADR-002 : Monolith FastAPI vs Microservices

**Status**: ACCEPTED

**Context**: MVP scope is small (6 services, 1 integration point). Microservices would add operational complexity (networking, deployment, observability).

**Decision**: Single monolith FastAPI with layered architecture (presentation → business logic → data access → integrations).

**Consequences**:
- ✅ Simple deployment (1 Docker container)
- ✅ Easy debugging (all code in one place)
- ✅ Shared codebase (domain models)
- ❌ Scaling limited to vertical (larger instance)
- ❌ Can't scale services independently

**Migration Path**: If performance issues, extract services (e.g., PaymentTracker as separate async worker) without changing public API.

### ADR-003 : Docker for All Environments

**Status**: ACCEPTED

**Context**: Dev/staging/prod parity requires same container across environments.

**Decision**: Docker Compose for dev, systemd+Docker for staging/prod.

**Consequences**:
- ✅ Consistency (same image everywhere)
- ✅ Fast deployment (pull + run)
- ✅ Easy rollback (previous image)
- ✅ Scaling (multi-container orchestration if needed)
- ❌ Slight overhead vs native process

**Migration Path**: Can move to Kubernetes if scaling requires orchestration (unlikely for MVP).

---

**Document Version**: 1.0
**Date**: Mars 2026
**Prochaine Review**: Juin 2026 (post-production launch)

