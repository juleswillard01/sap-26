# SAP-Facture Setup Guide

## System Requirements

### Local Development
- Python 3.10 or higher
- Docker and Docker Compose
- Git
- Make
- 2GB+ RAM
- 10GB+ disk space

### Production VPS
- Ubuntu 22.04 LTS or similar
- Docker and Docker Compose
- 2+ CPU cores
- 2GB+ RAM
- 20GB+ disk space
- Internet connectivity

## Local Development Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd sap-facture
```

### 2. Create Environment File

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=sqlite:///./data/sap.db

# URSSAF API (use sandbox by default)
URSSAF_API_BASE=https://portailapi-sandbox.urssaf.fr
URSSAF_CLIENT_ID=<your-sandbox-id>
URSSAF_CLIENT_SECRET=<your-sandbox-secret>

# Swan API (use sandbox by default)
SWAN_API_URL=https://api.swan.io/sandbox-partner/graphql
SWAN_ACCESS_TOKEN=<your-sandbox-token>

# Encryption
FERNET_KEY=<generate-with-python-cryptography>

# Email (optional for development)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=<your-email>
SMTP_PASSWORD=<your-app-password>
SMTP_FROM=noreply@sap-facture.fr

# Application
APP_ENV=development
APP_SECRET_KEY=<strong-random-key>
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=DEBUG
```

### 3. Generate Encryption Key

If `FERNET_KEY` is not set:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output to `.env`:

```env
FERNET_KEY=<output-from-above>
```

### 4. Generate Secret Key

For development, generate a strong secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Update `.env`:

```env
APP_SECRET_KEY=<output-from-above>
```

### 5. Install Dependencies (Optional)

For local development without Docker:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install

# Or manually
pip install -e ".[dev]"
```

### 6. Start Development Environment

Using Docker (recommended):

```bash
# Start all services
make dev

# This will:
# - Build Docker image
# - Start FastAPI app on port 8000
# - Mount volumes for hot-reload
# - Read environment from .env
```

Without Docker:

```bash
# Run migrations
make migrate

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Verify Setup

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/api/docs

# Should return: {"status": "healthy"}
```

## Production Setup on VPS

### 1. Install Docker

```bash
# Ubuntu 22.04
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group (optional, for non-root execution)
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Create Application Directory

```bash
# Create directory
sudo mkdir -p /opt/sap-facture
cd /opt/sap-facture

# Clone repository
sudo git clone <repository-url> .

# Create sap user
sudo useradd -m -d /home/sap sap
sudo chown -R sap:sap /opt/sap-facture

# Create data and storage directories
sudo mkdir -p /opt/sap-facture/data /opt/sap-facture/storage
sudo chown -R sap:sap /opt/sap-facture/data /opt/sap-facture/storage

# Create certs directory for SSL
sudo mkdir -p /opt/sap-facture/certs
sudo chown -R sap:sap /opt/sap-facture/certs
```

### 3. Configure Environment

```bash
# Copy environment template
sudo cp .env.example /opt/sap-facture/.env

# Change ownership
sudo chown sap:sap /opt/sap-facture/.env

# Set secure permissions
sudo chmod 600 /opt/sap-facture/.env

# Edit with your configuration
sudo -u sap nano /opt/sap-facture/.env
```

Update with production values:

```env
# Database (PostgreSQL recommended for production)
DATABASE_URL=postgresql://user:password@db-host:5432/sap_facture

# URSSAF API (production)
URSSAF_API_BASE=https://portailapi.urssaf.fr
URSSAF_CLIENT_ID=<your-production-id>
URSSAF_CLIENT_SECRET=<your-production-secret>

# Swan API (production)
SWAN_API_URL=https://api.swan.io/partner/graphql
SWAN_ACCESS_TOKEN=<your-production-token>

# Encryption
FERNET_KEY=<strong-random-key>

# Email
SMTP_HOST=<production-smtp-server>
SMTP_PORT=587
SMTP_USER=<your-email>
SMTP_PASSWORD=<app-password>
SMTP_FROM=noreply@sap-facture.fr

# Application
APP_ENV=production
APP_SECRET_KEY=<very-strong-random-key>
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
```

### 4. Install SSL Certificates

For Let's Encrypt (free):

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate (before nginx starts)
sudo certbot certonly --standalone -d your-domain.com

# Copy to app directory
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem \
    /opt/sap-facture/certs/sap-facture.crt
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem \
    /opt/sap-facture/certs/sap-facture.key

# Fix ownership
sudo chown sap:sap /opt/sap-facture/certs/*
```

Or use existing certificates:

```bash
# Copy your certificates
sudo cp /path/to/cert.crt /opt/sap-facture/certs/sap-facture.crt
sudo cp /path/to/key.key /opt/sap-facture/certs/sap-facture.key

# Set permissions
sudo chown sap:sap /opt/sap-facture/certs/*
sudo chmod 600 /opt/sap-facture/certs/*
```

### 5. Install systemd Service

```bash
# Copy service file
sudo cp /opt/sap-facture/deploy/sap-facture.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable sap-facture
sudo systemctl start sap-facture

# Check status
sudo systemctl status sap-facture

# View logs
sudo journalctl -u sap-facture -f
```

### 6. Configure Firewall

```bash
# Enable UFW if not already
sudo ufw enable

# Allow SSH (critical!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check rules
sudo ufw status
```

### 7. Test Production Setup

```bash
# Check service status
sudo systemctl status sap-facture

# Test health endpoint
curl http://localhost:8000/health
# Or via nginx/production
curl https://your-domain.com/health

# View application logs
sudo journalctl -u sap-facture -n 50 -f

# Check container status
docker compose -f /opt/sap-facture/docker-compose.prod.yml ps
```

## Database Setup

### SQLite (Development, Single-user)

Default setup, no additional configuration needed.

Database file: `/app/data/sap.db`

### PostgreSQL (Production, Multi-user)

```bash
# Install PostgreSQL client
sudo apt-get install postgresql-client

# Create database (on PostgreSQL server)
createdb sap_facture

# Update .env
DATABASE_URL=postgresql://user:password@db-host:5432/sap_facture
```

### Run Migrations

```bash
# Development
make migrate

# Production (in container)
cd /opt/sap-facture
docker compose -f docker-compose.prod.yml run --rm app alembic upgrade head

# Or via deployment script
./deploy/deploy.sh --migrate
```

## Verify Installation

### Development

```bash
# Make sure Docker is running
docker --version

# Test build
docker compose build

# Test container
docker compose up -d
sleep 5
curl http://localhost:8000/health
docker compose down
```

### Production

```bash
# Check service
sudo systemctl status sap-facture

# Check containers
docker ps

# Test endpoint
curl https://your-domain.com/health

# Check logs
sudo journalctl -u sap-facture --since "1 hour ago"
```

## Troubleshooting

### Cannot connect to Docker daemon

```bash
# Start Docker service
sudo systemctl start docker

# Or add current user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Permission denied errors

```bash
# Fix permissions (development)
chmod +x ./deploy/deploy.sh
chmod 644 ./.env
chmod 755 ./data ./storage

# Fix permissions (production)
sudo chown -R sap:sap /opt/sap-facture
sudo chmod -R u+w /opt/sap-facture/data /opt/sap-facture/storage
```

### Environment variables not loaded

```bash
# Verify .env file exists and is readable
cat .env

# Check Docker logs
docker compose logs app | grep -i env

# Verify in environment
docker compose exec app env | grep APP_
```

### Port already in use

```bash
# Find process using port
lsof -i :8000

# Kill process or change port in .env
# Then restart
docker compose down
docker compose up
```

### Database connection errors

```bash
# Test database connection
python3 -c "from sqlalchemy import create_engine; \
  engine = create_engine('sqlite:///./data/sap.db'); \
  print(engine.connect())"

# Check database file exists
ls -la data/sap.db

# Reset database (delete and recreate)
rm data/sap.db
make migrate
```

## Next Steps

1. Review [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment procedures
2. Check [Makefile](./Makefile) for available development commands
3. Read [API documentation](http://localhost:8000/api/docs) once running
4. Configure integrations (URSSAF, Swan, SMTP)
5. Create initial users and configure permissions
6. Setup monitoring and backups
7. Plan database migration strategy (if using PostgreSQL)

## Security Checklist

Before production deployment:

- [ ] Strong `APP_SECRET_KEY` generated and set
- [ ] SSL/TLS certificates installed and valid
- [ ] `.env` file with secure permissions (600)
- [ ] Firewall configured to allow only necessary ports
- [ ] Database credentials rotated and strong
- [ ] Regular backups scheduled
- [ ] Log aggregation configured
- [ ] Monitoring and alerting setup
- [ ] URSSAF/Swan API credentials in production mode
- [ ] Email service configured for notifications
- [ ] Database password in `DATABASE_URL` is secure
- [ ] No secrets committed to version control

## Support

For issues during setup:
1. Check logs: `docker compose logs app` or `sudo journalctl -u sap-facture -f`
2. Verify `.env` configuration
3. Test connectivity: `curl http://localhost:8000/health`
4. Review [DEPLOYMENT.md](./DEPLOYMENT.md) troubleshooting section
5. Contact support team with logs and error messages
