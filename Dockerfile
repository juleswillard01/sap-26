# Multi-stage build for SAP-Facture
# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies and system packages for weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.9 \
    libpango-1.0-0=1.50.9+ds-1 \
    libpangoft2-1.0-0=1.50.9+ds-1 \
    libcairo2=1.16.0-7+b2 \
    libffi-dev=3.4.4-1 \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml pyproject.toml

# Install Python dependencies
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install --no-cache-dir .

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies for weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0=1.50.9+ds-1 \
    libpangoft2-1.0-0=1.50.9+ds-1 \
    libcairo2=1.16.0-7+b2 \
    curl=7.88.1-10+deb12u5 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 sap && \
    mkdir -p /app/data /app/storage && \
    chown -R sap:sap /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=sap:sap . .

USER sap

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
