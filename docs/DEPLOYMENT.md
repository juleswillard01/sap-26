# SAP-Facture Deployment Guide

## Overview

SAP-Facture uses Docker for containerization and can be deployed to a VPS using the provided deployment infrastructure. This guide covers local development, Docker builds, and production deployment.

## Project Structure

```
/home/jules/Documents/3-git/SAP/main/
├── Dockerfile              # Multi-stage Docker build
├── docker-compose.yml      # Development compose setup
├── docker-compose.prod.yml # Production compose setup
├── .dockerignore           # Files excluded from Docker build
├── Makefile               # Development commands
├── deploy/
│   ├── nginx.conf         # Nginx reverse proxy configuration
│   ├── sap-facture.service # systemd service file
│   └── deploy.sh          # Automated deployment script
├── app/
│   ├── main.py            # FastAPI application with scheduler integration
│   ├── config.py          # Configuration management
│   ├── database.py        # Database setup
│   └── tasks/
│       └── scheduler.py    # APScheduler configuration
└── pyproject.toml         # Python project configuration
```

## Local Development

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development without Docker)
- Make

### Quick Start

```bash
# Install dependencies
make install

# Start development environment with Docker
make dev

# Run tests with coverage
make test

# Check code quality
make lint
make mypy

# Format code
make format

# View logs
make logs

# Open shell in container
make shell
```

### Available Make Commands

```bash
make help          # Show all available commands
make dev           # Start development environment
make dev-down      # Stop development environment
make test          # Run tests with coverage
make lint          # Run linter (ruff)
make format        # Format code
make mypy          # Type check code
make check         # Run all checks (lint + mypy)
make migrate       # Run database migrations
make clean         # Clean cache and build files
make deploy        # Run deployment script
```

## Docker Build

### Building the Image

The `Dockerfile` uses a multi-stage build:

1. **Builder Stage**: Compiles Python dependencies and includes build tools
2. **Runtime Stage**: Lean production image with only runtime dependencies

Key features:
- Python 3.11-slim base image
- Weasyprint system dependencies (libpango, libcairo)
- Non-root user (`sap`) for security
- Minimal final image size (<500MB)
- Health check endpoint
- 4 Uvicorn workers

```bash
# Build locally
docker compose build

# Build for production
docker compose -f docker-compose.prod.yml build
```

### Running Locally

Development:
```bash
docker compose up --build
```

Production simulation:
```bash
docker compose -f docker-compose.prod.yml up --build
```

## Production Deployment

### Prerequisites

- VPS with Docker and Docker Compose installed
- SSL/TLS certificates for HTTPS
- Git repository access
- systemd service support

### Deployment Steps

#### 1. Initial Setup on VPS

```bash
# SSH into VPS
ssh user@your-vps-ip

# Create application directory
sudo mkdir -p /opt/sap-facture
cd /opt/sap-facture

# Clone repository
git clone https://github.com/your-org/sap-facture.git .

# Create non-root user for app
sudo useradd -m sap
sudo chown -R sap:sap /opt/sap-facture

# Create data and storage directories
sudo mkdir -p /opt/sap-facture/data /opt/sap-facture/storage
sudo chown -R sap:sap /opt/sap-facture/data /opt/sap-facture/storage

# Create certificates directory
sudo mkdir -p /opt/sap-facture/certs
sudo chown -R sap:sap /opt/sap-facture/certs
```

#### 2. Configure SSL Certificates

Copy SSL certificates to `/opt/sap-facture/certs/`:
- `sap-facture.crt` - SSL certificate
- `sap-facture.key` - SSL private key

Update paths in `deploy/nginx.conf` if using different names.

#### 3. Setup Environment Variables

```bash
# Copy environment template
sudo cp .env.example /opt/sap-facture/.env
sudo chown sap:sap /opt/sap-facture/.env
sudo chmod 600 /opt/sap-facture/.env

# Edit with production values
sudo nano /opt/sap-facture/.env
```

Required environment variables:
```
APP_ENV=production
APP_SECRET_KEY=<strong-random-key>
DATABASE_URL=<production-db-url>
URSSAF_CLIENT_ID=<urssaf-production-id>
URSSAF_CLIENT_SECRET=<urssaf-production-secret>
SWAN_ACCESS_TOKEN=<swan-production-token>
FERNET_KEY=<encryption-key>
SMTP_HOST=<smtp-server>
SMTP_PORT=587
SMTP_USER=<email>
SMTP_PASSWORD=<app-password>
```

#### 4. Install systemd Service

```bash
# Copy and enable service
sudo cp deploy/sap-facture.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sap-facture

# Start the service
sudo systemctl start sap-facture

# Check status
sudo systemctl status sap-facture

# View logs
sudo journalctl -u sap-facture -f
```

#### 5. Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Verify (optional)
sudo ufw status
```

### Automated Deployment

Use the deployment script for updates:

```bash
# Deploy with all options (build, migrate, restart)
cd /opt/sap-facture
./deploy/deploy.sh --build --migrate --restart

# Or individual options
./deploy/deploy.sh --build          # Rebuild Docker image
./deploy/deploy.sh --migrate        # Run database migrations
./deploy/deploy.sh --restart        # Restart service

# Default (no image rebuild)
./deploy/deploy.sh
```

The script:
1. Pulls latest code from Git
2. Builds Docker image (if `--build`)
3. Runs migrations (if `--migrate`)
4. Restarts service (if `--restart`)
5. Performs health check (curl /health)
6. Rolls back on failure

### Manual Commands

```bash
# Check service status
sudo systemctl status sap-facture

# Start service
sudo systemctl start sap-facture

# Stop service
sudo systemctl stop sap-facture

# Restart service
sudo systemctl restart sap-facture

# View logs
sudo journalctl -u sap-facture -f

# View recent logs (last 100 lines)
sudo journalctl -u sap-facture -n 100

# View logs for specific date
sudo journalctl -u sap-facture --since "2026-03-14 00:00:00"
```

## Nginx Configuration

The Nginx reverse proxy (`deploy/nginx.conf`):

- **Ports**: 80 (HTTP) → 443 (HTTPS redirect)
- **SSL**: TLS 1.2+, strong ciphers
- **Security Headers**: HSTS, X-Frame-Options, CSP, etc.
- **Rate Limiting**: 10 req/s general, 20 req/s for API
- **Compression**: gzip for text/JSON
- **Static Files**: Served directly from `/static/`
- **Proxying**: Requests forwarded to app container on port 8000

Key endpoints:
- `/health` - Liveness probe (no rate limiting)
- `/api/*` - API endpoints (stricter rate limiting)
- `/static/*` - Static files (7-day cache)
- `/` - All other requests proxied to backend

## APScheduler Configuration

Scheduled jobs run automatically (see `app/tasks/scheduler.py`):

1. **Poll URSSAF Status** (every 4 hours)
   - Updates invoice status from URSSAF API
   - Job ID: `poll_urssaf_status`

2. **Send Invoice Reminders** (every 6 hours)
   - Reminds users about unvalidated invoices (36h+ old)
   - Job ID: `send_invoice_reminders`

3. **Sync Bank Transactions** (every 6 hours)
   - Fetches transactions from Swan bank API
   - Job ID: `sync_bank_transactions`

Jobs:
- Start automatically on app startup
- Persist in SQLite (`data/jobs.db`)
- Handle errors gracefully with logging
- Recover from missed executions (coalesce enabled)

Monitor scheduler:
```bash
# View Docker logs
docker compose logs app | grep -i scheduler

# Or on systemd
sudo journalctl -u sap-facture -f | grep -i scheduler
```

## Monitoring and Maintenance

### Health Checks

```bash
# Local development
curl http://localhost:8000/health

# Production (via Nginx)
curl https://your-domain.com/health

# Check Docker container health
docker compose ps
```

### Database Migrations

```bash
# Create new migration
make migrate-create MSG="add new table"

# View migration status
make migrate-status

# Apply migrations
make migrate

# Rollback last migration
make migrate-down

# Deploy with migrations
./deploy/deploy.sh --migrate
```

### Log Management

Development:
```bash
# Follow app logs
make logs

# View logs with grep
docker compose logs app | grep ERROR

# View logs from last hour
docker compose logs --since 1h app
```

Production:
```bash
# Follow systemd logs
sudo journalctl -u sap-facture -f

# Filter by level
sudo journalctl -u sap-facture -p err

# Export logs to file
sudo journalctl -u sap-facture > /tmp/sap-facture.log
```

### Disk Space

```bash
# Check storage usage
du -sh /opt/sap-facture/*

# Cleanup old Docker images
docker image prune -a --filter "until=72h"

# Cleanup old volumes
docker volume prune

# Full cleanup (caution: removes all unused images/volumes/networks)
docker system prune -a
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs app

# Verify configuration
cat /opt/sap-facture/.env

# Rebuild image
docker compose -f docker-compose.prod.yml build --no-cache
```

### Scheduler not running

```bash
# Check logs for scheduler errors
docker compose logs app | grep -i scheduler

# Verify SQLAlchemy job store
ls -la /opt/sap-facture/data/jobs.db

# Check job status
docker compose exec app sqlite3 /app/data/jobs.db "SELECT * FROM apscheduler_jobs;"
```

### Database issues

```bash
# Backup database
cp /opt/sap-facture/data/sap.db /opt/sap-facture/data/sap.db.backup

# Check database integrity
sqlite3 /opt/sap-facture/data/sap.db ".check"

# Run migrations
./deploy/deploy.sh --migrate
```

### High memory usage

Check `docker-compose.prod.yml` resource limits:
```yaml
deploy:
  resources:
    limits:
      cpus: "1"
      memory: 512M
```

Increase if needed and restart:
```bash
sudo systemctl restart sap-facture
```

### SSL certificate renewal

Replace certificates in `/opt/sap-facture/certs/` and restart Nginx:
```bash
# Copy new certificates
sudo cp /path/to/new/cert.crt /opt/sap-facture/certs/sap-facture.crt
sudo cp /path/to/new/key.key /opt/sap-facture/certs/sap-facture.key

# Reload Nginx (systemd)
sudo systemctl restart sap-facture
```

## Security Best Practices

1. **Environment Variables**: Never commit `.env` file
2. **Secrets**: Use strong random values for `APP_SECRET_KEY`
3. **SSL/TLS**: Always use HTTPS in production
4. **Backups**: Regular database backups before deployments
5. **Monitoring**: Setup log aggregation and alerts
6. **Updates**: Keep Docker base images updated
7. **Firewalls**: Use UFW or cloud provider firewalls
8. **Rate Limiting**: Configured in Nginx (10 req/s default)

## Performance Tuning

### Application
- Uvicorn workers: Adjust in `Dockerfile` (default: 4)
- Database connection pooling: Configure in `app/database.py`
- Async jobs: APScheduler handles concurrency

### Nginx
- Worker connections: Edit `deploy/nginx.conf` (default: 1024)
- Buffer sizes: Adjust for large uploads
- Gzip compression: Enabled for common types

### Docker
- Container memory limit: Set in `docker-compose.prod.yml`
- CPU limit: Adjust based on VPS capacity
- Volume mounting: Use named volumes for persistence

## Rollback Procedure

The `deploy.sh` script automatically rolls back on failure:

```bash
# Manual rollback to previous commit
cd /opt/sap-facture
git checkout <previous-commit-hash>
./deploy/deploy.sh --restart

# View commit history
git log --oneline -10
```

## Support and Maintenance

For issues:
1. Check logs: `sudo journalctl -u sap-facture -f`
2. Verify configuration: `cat /opt/sap-facture/.env`
3. Test connectivity: `curl https://your-domain.com/health`
4. Check Docker: `docker ps` and `docker logs`
5. Inspect database: `sqlite3 /opt/sap-facture/data/sap.db`

## Further Reading

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
