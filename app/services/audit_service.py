from __future__ import annotations

import json
import logging
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

ActionType = Literal["CREATE", "UPDATE", "DELETE", "SUBMIT_URSSAF", "LOGIN", "EXPORT"]


class AuditService:
    """Service for logging audit events to the audit_logs table."""

    def __init__(self, db: Session) -> None:
        """Initialize audit service with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self._db = db

    def log_action(
        self,
        action: ActionType,
        entity_type: str,
        entity_id: str | None = None,
        user_id: str | None = None,
        old_value: dict[str, Any] | str | None = None,
        new_value: dict[str, Any] | str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log an action to the audit log.

        Args:
            action: The action type (CREATE, UPDATE, DELETE, SUBMIT_URSSAF, LOGIN, EXPORT).
            entity_type: The type of entity being acted upon (e.g., "invoice", "user").
            entity_id: The ID of the entity (optional).
            user_id: The ID of the user performing the action (optional).
            old_value: The previous value(s) before the action (optional).
            new_value: The new value(s) after the action (optional).
            metadata: Additional metadata as a dictionary (optional).
            ip_address: Client IP address (optional).

        Returns:
            The created AuditLog instance.

        Raises:
            ValueError: If action is not a valid ActionType.
        """
        # Validate action
        valid_actions: tuple[ActionType, ...] = (
            "CREATE",
            "UPDATE",
            "DELETE",
            "SUBMIT_URSSAF",
            "LOGIN",
            "EXPORT",
        )
        if action not in valid_actions:
            raise ValueError(f"Invalid action: {action}. Must be one of {valid_actions}")

        # Serialize old_value if it's a dict
        old_value_str = None
        if old_value is not None:
            old_value_str = json.dumps(old_value) if isinstance(old_value, dict) else str(old_value)

        # Serialize new_value if it's a dict
        new_value_str = None
        if new_value is not None:
            new_value_str = json.dumps(new_value) if isinstance(new_value, dict) else str(new_value)

        # Serialize metadata
        metadata_str = None
        if metadata is not None:
            try:
                metadata_str = json.dumps(metadata)
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to serialize metadata: {e}", exc_info=False)
                metadata_str = None

        # Create audit log record
        audit_log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            old_value=old_value_str,
            new_value=new_value_str,
            metadata_json=metadata_str,
            ip_address=ip_address,
        )

        try:
            self._db.add(audit_log)
            self._db.commit()
            self._db.refresh(audit_log)
            logger.info(
                "Audit log created",
                extra={
                    "action": action,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "user_id": user_id,
                },
            )
        except Exception:
            self._db.rollback()
            logger.error("Failed to create audit log", exc_info=True)
            raise

        return audit_log
