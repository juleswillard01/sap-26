"""Configuration via pydantic-settings et variables d'environnement."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration de l'application SAP-Facture."""

    # Google Sheets
    google_sheets_spreadsheet_id: str = ""
    google_service_account_file: Path = Path("./credentials/service_account.json")
    google_scopes: list[str] = ["spreadsheets", "drive"]
    sheets_cache_ttl: int = 30
    sheets_rate_limit: int = 60
    sheets_timeout: int = 30

    # Circuit breaker
    circuit_breaker_fail_max: int = 5
    circuit_breaker_reset_timeout: int = 60

    # Date format
    date_format: str = "ISO"

    # Fiscalite micro-entrepreneur — CDC §8
    taux_charges_micro: float = 0.258
    abattement_bnc: float = 0.34
    credit_impot_client: float = 0.50

    # Timers — CDC §2.3
    reminder_hours: int = 36
    expiration_hours: int = 48
    polling_interval_hours: int = 4

    # SMTP
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    notification_email: str = ""

    # Indy
    indy_email: str = ""
    indy_password: str = ""

    # AIS (Avance Immédiate Services)
    ais_email: str = ""
    ais_password: str = ""
    ais_base_url: str = "https://app.avance-immediate.fr"

    # App
    app_env: str = "development"
    app_port: int = 8000
    export_output_dir: Path = Path("./io/exports")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Retourne l'instance de configuration."""
    return Settings()
