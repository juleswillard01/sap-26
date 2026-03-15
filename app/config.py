"""
Configuration management using Pydantic Settings v2.

Reads from .env files per environment:
- .env.local (development)
- .env.staging
- .env.production

Security: All secrets masked via SecretStr, validated at startup.
"""

from __future__ import annotations

import base64
import json
import logging

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All secrets must be configured via .env files (never hardcoded).
    Sensitive values are masked in logs and repr output.
    """

    # API Configuration
    API_TITLE: str = "SAP-Facture API"
    API_VERSION: str = "0.1.0"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")

    # CORS — Restrictive by default
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Comma-separated list of allowed CORS origins",
    )

    # Google Sheets
    SPREADSHEET_ID: str = Field(description="Google Sheets spreadsheet ID")
    GOOGLE_SERVICE_ACCOUNT_B64: SecretStr = Field(
        description="Base64-encoded Google Service Account JSON (never store JSON file on disk)"
    )

    # URSSAF API (OAuth2)
    URSSAF_CLIENT_ID: str = Field(description="URSSAF OAuth2 client ID")
    URSSAF_CLIENT_SECRET: SecretStr = Field(description="URSSAF OAuth2 client secret (rotate quarterly)")
    URSSAF_API_BASE_URL: str = "https://api.matrice.urssaf.fr"

    # Swan Bank API
    SWAN_API_KEY: SecretStr = Field(description="Swan API key (grants banking access, rotate quarterly)")
    SWAN_API_BASE_URL: str = "https://api.swan.io"
    SWAN_ACCOUNT_ID: str = Field(description="Swan account ID for payment routing")

    # SMTP Configuration
    SMTP_HOST: str = Field(description="SMTP server host")
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = Field(description="SMTP username")
    SMTP_PASSWORD: SecretStr = Field(description="SMTP password (use Gmail App Password, not regular password)")
    SMTP_FROM_EMAIL: str = "noreply@sap-facture.com"

    # API Security
    API_KEY_INTERNAL: SecretStr = Field(
        description="Internal API key for authenticating requests (min 32 chars, generate with secrets.token_urlsafe(32))"
    )

    # Optional: Encryption at rest (Phase 2+)
    FERNET_ENCRYPTION_KEY: SecretStr | None = Field(
        default=None,
        description="Fernet encryption key for encrypting PII at rest (generate with Fernet.generate_key())",
    )

    # Cache Configuration
    CACHE_TTL_SECONDS: int = 300  # 5 minutes default

    # Sentry (error tracking)
    SENTRY_DSN: str | None = None

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

    @field_validator("API_KEY_INTERNAL", mode="before")
    @classmethod
    def validate_api_key_length(cls, v: SecretStr) -> SecretStr:
        """Ensure API_KEY_INTERNAL is sufficiently long."""
        if isinstance(v, SecretStr):
            key_str = v.get_secret_value()
        else:
            key_str = v

        if len(key_str) < 32:
            raise ValueError("API_KEY_INTERNAL must be at least 32 characters")
        return v

    @field_validator("URSSAF_CLIENT_SECRET", "SWAN_API_KEY", "SMTP_PASSWORD", mode="before")
    @classmethod
    def validate_secrets_not_placeholder(cls, v: SecretStr) -> SecretStr:
        """Ensure secrets are not placeholder values."""
        if isinstance(v, SecretStr):
            secret_str = v.get_secret_value()
        else:
            secret_str = v

        if secret_str.endswith("_here") or secret_str.endswith("_here_replace_me"):
            raise ValueError("Secret value appears to be placeholder — configure .env with real secret")

        return v

    def get_google_service_account_dict(self) -> dict:
        """
        Decode and parse Google Service Account from base64.

        Returns:
            Decoded service account dictionary

        Raises:
            ValueError: If decoding or JSON parsing fails
        """
        try:
            b64_str = self.GOOGLE_SERVICE_ACCOUNT_B64.get_secret_value()
            decoded = base64.b64decode(b64_str)
            sa_dict = json.loads(decoded)

            # Validate structure
            required_fields = ["type", "project_id", "private_key", "client_email"]
            if not all(field in sa_dict for field in required_fields):
                raise ValueError(f"Missing required fields: {required_fields}")

            return sa_dict
        except base64.binascii.Error as e:
            raise ValueError(f"GOOGLE_SERVICE_ACCOUNT_B64 is not valid base64: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"GOOGLE_SERVICE_ACCOUNT_B64 is not valid JSON: {e}")

    def __repr__(self) -> str:
        """Override repr to mask secrets."""
        return f"Settings(ENVIRONMENT={self.ENVIRONMENT}, API_KEY_INTERNAL=***)"
