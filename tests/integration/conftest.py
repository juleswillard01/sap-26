"""Shared fixtures for integration tests.

Provides a real AIS adapter connected to the production AIS API.
Requires AIS_EMAIL and AIS_PASSWORD environment variables.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from src.adapters.ais_adapter import AISAPIAdapter
from src.config import Settings

if TYPE_CHECKING:
    from collections.abc import Generator

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def ais_settings() -> Settings:
    """Load settings from environment for integration tests.

    AIS_EMAIL and AIS_PASSWORD must be set in the environment or .env file.
    """
    return Settings()


@pytest.fixture(scope="module")
def ais_adapter(ais_settings: Settings) -> Generator[AISAPIAdapter, None, None]:
    """Real AIS adapter connected to production API.

    Module-scoped to reuse the same authenticated session across all tests
    in a module, avoiding repeated logins against the real API.
    """
    adapter = AISAPIAdapter(ais_settings)
    adapter.connect()
    logger.info("AIS integration test adapter connected")
    yield adapter
    adapter.close()
    logger.info("AIS integration test adapter closed")
