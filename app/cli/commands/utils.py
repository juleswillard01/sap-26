from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session
from tabulate import tabulate

from app.database import SessionLocal

logger = logging.getLogger(__name__)

# For testing - can be overridden
_test_db_session: Session | None = None


def get_db_session() -> Session:
    """Get a database session for CLI commands.

    Returns:
        SQLAlchemy session instance.
    """
    global _test_db_session
    if _test_db_session:
        return _test_db_session
    return SessionLocal()


def set_db_session(db: Session | None) -> None:
    """Set test database session for CLI commands.

    Args:
        db: Database session or None to reset.
    """
    global _test_db_session
    _test_db_session = db


def print_table(
    data: list[dict[str, Any]],
    headers: str = "keys",
    tablefmt: str = "grid",
) -> None:
    """Print data as a formatted table.

    Args:
        data: List of dictionaries to display.
        headers: Header format (keys, firstrow, etc).
        tablefmt: Table format (grid, simple, plain, etc).
    """
    if not data:
        print("No data to display.")
        return

    print(tabulate(data, headers=headers, tablefmt=tablefmt))


def print_json(data: Any) -> None:
    """Print data as JSON.

    Args:
        data: Data to serialize and print.
    """
    print(json.dumps(data, indent=2, default=str))


def get_or_create_default_user(db: Session) -> str:
    """Get first user ID or raise error if none exist.

    Args:
        db: Database session.

    Returns:
        First user ID.

    Raises:
        ValueError: If no users exist in database.
    """
    from sqlalchemy import select

    from app.models.user import User

    stmt = select(User).limit(1)
    user = db.scalar(stmt)

    if not user:
        raise ValueError(
            "No users found in database. Please set up a user first via the web interface."
        )

    return user.id
