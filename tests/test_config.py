"""Tests pour la configuration — CDC §1."""

from pathlib import Path

from src.config import Settings, get_settings


class TestSettings:
    """Tests pour la classe Settings."""

    def test_default_taux_charges_micro(self) -> None:
        settings = Settings()
        assert settings.taux_charges_micro == 0.258

    def test_default_abattement_bnc(self) -> None:
        settings = Settings()
        assert settings.abattement_bnc == 0.34

    def test_default_credit_impot_client(self) -> None:
        settings = Settings()
        assert settings.credit_impot_client == 0.50

    def test_default_reminder_hours(self) -> None:
        settings = Settings()
        assert settings.reminder_hours == 36

    def test_default_expiration_hours(self) -> None:
        settings = Settings()
        assert settings.expiration_hours == 48

    def test_default_polling_interval(self) -> None:
        settings = Settings()
        assert settings.polling_interval_hours == 4

    def test_sheets_rate_limit(self) -> None:
        settings = Settings()
        assert settings.sheets_rate_limit == 60

    def test_export_output_dir_is_path(self) -> None:
        settings = Settings()
        assert isinstance(settings.export_output_dir, Path)

    def test_get_settings_returns_instance(self) -> None:
        settings = get_settings()
        assert isinstance(settings, Settings)
