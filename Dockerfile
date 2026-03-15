# Multi-stage build
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy project metadata
COPY pyproject.toml .

# Build wheels
RUN pip install --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -e .

# ===== RUNTIME =====
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
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

# Create logs directory
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
