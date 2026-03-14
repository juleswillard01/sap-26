from __future__ import annotations

import enum
import sys
from collections.abc import Generator

# Compatibility shim for Python <3.11 - must be before importing models
if sys.version_info < (3, 11):
    if not hasattr(enum, "StrEnum"):

        class StrEnum(str, enum.Enum):  # type: ignore
            """Compatibility implementation of enum.StrEnum for Python <3.11."""

            pass

        enum.StrEnum = StrEnum

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
