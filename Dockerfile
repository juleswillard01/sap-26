FROM python:3.12-slim

# WeasyPrint + Playwright system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencies first (layer cache)
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev
RUN uv run playwright install --with-deps chromium

# Source
COPY src/ src/
COPY io/ io/

# Credentials mounted at runtime via docker secret
# NEVER copy service_account.json into the image

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["uv", "run", "python", "-m", "src.cli"]
