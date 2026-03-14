from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(default="sqlite:///./data/sap.db")

    # URSSAF API
    urssaf_api_base: str = Field(default="https://portailapi-sandbox.urssaf.fr")
    urssaf_client_id: str = Field(default="")
    urssaf_client_secret: str = Field(default="")

    # Swan API
    swan_api_url: str = Field(default="https://api.swan.io/sandbox-partner/graphql")
    swan_access_token: str = Field(default="")

    # Encryption
    fernet_key: str = Field(default="")

    # SMTP
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from: str = Field(default="noreply@sap-facture.fr")

    # App
    app_env: str = Field(default="development")
    app_secret_key: str = Field(default="change-me-in-production")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    log_level: str = Field(default="INFO")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_sandbox(self) -> bool:
        return "sandbox" in self.urssaf_api_base
