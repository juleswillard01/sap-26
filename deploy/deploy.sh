#!/bin/bash
set -euo pipefail

# SAP-Facture Deployment Script
# Usage: ./deploy.sh [--build] [--migrate] [--restart]

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/sap-facture"
COMPOSE_FILE="docker-compose.prod.yml"
SERVICE_NAME="sap-facture"
HEALTH_CHECK_URL="http://localhost:8000/health"
HEALTH_CHECK_TIMEOUT=60
MAX_RETRIES=10

# Flags
BUILD_IMAGE=false
RUN_MIGRATION=false
RESTART_SERVICE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_IMAGE=true
            shift
            ;;
        --migrate)
            RUN_MIGRATION=true
            shift
            ;;
        --restart)
            RESTART_SERVICE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--build] [--migrate] [--restart]"
            exit 1
            ;;
    esac
done

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Change to app directory
cd "$APP_DIR" || exit 1

log_info "Starting deployment from $APP_DIR"

# Save current state for rollback
CURRENT_COMMIT=$(git rev-parse HEAD)
log_info "Current commit: $CURRENT_COMMIT"

# Step 1: Pull latest code
log_info "Pulling latest code..."
if ! git pull origin main; then
    log_error "Failed to pull code"
    exit 1
fi

NEW_COMMIT=$(git rev-parse HEAD)
if [ "$CURRENT_COMMIT" != "$NEW_COMMIT" ]; then
    log_info "Code updated: $CURRENT_COMMIT -> $NEW_COMMIT"
else
    log_warn "No new commits to deploy"
fi

# Step 2: Build Docker image if requested
if [ "$BUILD_IMAGE" = true ]; then
    log_info "Building Docker image..."
    if ! docker compose -f "$COMPOSE_FILE" build --no-cache; then
        log_error "Failed to build Docker image"
        git checkout "$CURRENT_COMMIT"
        exit 1
    fi
    log_info "Docker image built successfully"
fi

# Step 3: Run migrations if requested
if [ "$RUN_MIGRATION" = true ]; then
    log_info "Running database migrations..."
    if ! docker compose -f "$COMPOSE_FILE" run --rm app alembic upgrade head; then
        log_error "Migration failed"
        git checkout "$CURRENT_COMMIT"
        exit 1
    fi
    log_info "Migrations completed"
fi

# Step 4: Restart service
if [ "$RESTART_SERVICE" = true ]; then
    log_info "Restarting systemd service..."
    if ! sudo systemctl restart "$SERVICE_NAME"; then
        log_error "Failed to restart service"
        git checkout "$CURRENT_COMMIT"
        exit 1
    fi
fi

# Step 5: Health check
log_info "Running health check..."
RETRY_COUNT=0
HEALTH_OK=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s -m 5 "$HEALTH_CHECK_URL" > /dev/null 2>&1; then
        HEALTH_OK=true
        log_info "Health check passed"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        log_warn "Health check attempt $RETRY_COUNT failed, retrying in 3s..."
        sleep 3
    fi
done

if [ "$HEALTH_OK" = false ]; then
    log_error "Health check failed after $MAX_RETRIES attempts"
    log_warn "Rolling back to previous commit: $CURRENT_COMMIT"

    git checkout "$CURRENT_COMMIT"
    if [ "$RESTART_SERVICE" = true ]; then
        sudo systemctl restart "$SERVICE_NAME"
    fi

    exit 1
fi

log_info "Deployment completed successfully"
log_info "New commit: $NEW_COMMIT"

# Optional: Clean up old Docker images
log_info "Cleaning up old Docker images..."
docker image prune -f --filter "until=72h" || true

exit 0
