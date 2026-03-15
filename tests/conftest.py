"""
Pytest configuration and shared fixtures.

Usage: pytest auto-discovers and uses these fixtures
Reference: docs/phase3/test-strategy.md section 2
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Test configuration."""
    return Settings(
        SPREADSHEET_ID="test-sheet-id",
        URSSAF_CLIENT_ID="test-urssaf-id",
        URSSAF_CLIENT_SECRET="test-urssaf-secret",
        SWAN_API_KEY="test-swan-key",
        SWAN_ACCOUNT_ID="test-swan-account",
        SMTP_HOST="localhost",
        SMTP_USERNAME="test",
        SMTP_PASSWORD="test",
    )


@pytest.fixture
def app(test_settings: Settings):
    """FastAPI test app."""
    return create_app(test_settings)


@pytest.fixture
def client(app):
    """FastAPI test client."""
    return TestClient(app)
