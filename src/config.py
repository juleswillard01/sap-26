"""Configuration via pydantic-settings et variables d'environnement."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration de l'application SAP-Facture."""

    google_sheets_spreadsheet_id: str = ""
    google_service_account_file: Path = Path("./credentials/service_account.json")
    sheets_cache_ttl: int = 30
    sheets_rate_limit: int = 60
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notification_email: str = ""
    indy_email: str = ""
    indy_password: str = ""
    app_env: str = "development"
    app_port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Retourne l'instance de configuration."""
    return Settings()
