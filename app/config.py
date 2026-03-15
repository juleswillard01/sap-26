"""
Configuration management using Pydantic Settings.

Reads from .env files per environment:
- .env.local (development)
- .env.staging
- .env.production
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All secrets must be configured via .env files (never hardcoded).
    """

    # API Configuration
    API_TITLE: str = "SAP-Facture API"
    API_VERSION: str = "0.1.0"
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Google Sheets
    SPREADSHEET_ID: str  # Required: spreadsheet ID in Google Drive
    GOOGLE_SERVICE_ACCOUNT_PATH: str = "secrets/service-account.json"

    # URSSAF API (OAuth2)
    URSSAF_CLIENT_ID: str  # Required
    URSSAF_CLIENT_SECRET: str  # Required
    URSSAF_API_BASE_URL: str = "https://api.matrice.urssaf.fr"

    # Swan Bank API
    SWAN_API_KEY: str  # Required
    SWAN_API_BASE_URL: str = "https://api.swan.io"
    SWAN_ACCOUNT_ID: str  # Required: account receiving invoices

    # SMTP Configuration
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str = "noreply@sap-facture.com"

    # Cache Configuration
    CACHE_TTL_SECONDS: int = 300  # 5 minutes default

    # Sentry (error tracking)
    SENTRY_DSN: str | None = None

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
