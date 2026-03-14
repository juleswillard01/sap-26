from __future__ import annotations

import json
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure Python 3.11+ compatibility for models that use StrEnum
from app.database import Base
from app.models.audit_log import AuditLog
from app.services.audit_service import AuditService


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


@pytest.fixture()
def audit_service(db_session: Session) -> AuditService:
    """Create an audit service with a test database session."""
    return AuditService(db=db_session)


class TestAuditService:
    """Tests for the AuditService."""

    def test_log_action_creates_record(
        self, audit_service: AuditService, db_session: Session
    ) -> None:
        """Test that log_action creates a record in the database."""
        audit_log = audit_service.log_action(
            action="CREATE",
            entity_type="invoice",
            entity_id="inv-123",
            user_id="user-456",
        )

        assert audit_log.id is not None
        assert audit_log.action == "CREATE"
        assert audit_log.entity_type == "invoice"
        assert audit_log.entity_id == "inv-123"
        assert audit_log.user_id == "user-456"

        # Verify it's actually in the database
        fetched = db_session.query(AuditLog).filter_by(id=audit_log.id).first()
        assert fetched is not None
        assert fetched.action == "CREATE"

    def test_log_action_serializes_json(self, audit_service: AuditService) -> None:
        """Test that old_value and new_value are serialized as JSON when dict."""
        old_value = {"status": "draft", "amount": 100.50}
        new_value = {"status": "submitted", "amount": 100.50}

        audit_log = audit_service.log_action(
            action="UPDATE",
            entity_type="invoice",
            entity_id="inv-123",
            user_id="user-456",
            old_value=old_value,
            new_value=new_value,
        )

        # Verify JSON serialization
        assert audit_log.old_value is not None
        assert json.loads(audit_log.old_value) == old_value

        assert audit_log.new_value is not None
        assert json.loads(audit_log.new_value) == new_value

    def test_log_action_with_metadata(self, audit_service: AuditService) -> None:
        """Test that metadata is serialized as JSON."""
        metadata = {"source": "api", "version": "v1", "duration_ms": 123}

        audit_log = audit_service.log_action(
            action="SUBMIT_URSSAF",
            entity_type="payment_request",
            entity_id="pr-789",
            user_id="user-456",
            metadata=metadata,
        )

        assert audit_log.metadata_json is not None
        assert json.loads(audit_log.metadata_json) == metadata

    def test_log_action_with_ip_address(self, audit_service: AuditService) -> None:
        """Test that IP address is stored correctly."""
        ip_address = "192.168.1.100"

        audit_log = audit_service.log_action(
            action="LOGIN",
            entity_type="user",
            entity_id="user-456",
            user_id="user-456",
            ip_address=ip_address,
        )

        assert audit_log.ip_address == ip_address

    def test_log_action_all_action_types(self, audit_service: AuditService) -> None:
        """Test that all valid action types can be logged."""
        valid_actions = ["CREATE", "UPDATE", "DELETE", "SUBMIT_URSSAF", "LOGIN", "EXPORT"]

        for action in valid_actions:
            audit_log = audit_service.log_action(
                action=action,
                entity_type="entity",
                entity_id="entity-123",
                user_id="user-456",
            )
            assert audit_log.action == action

    def test_log_action_invalid_action_raises(self, audit_service: AuditService) -> None:
        """Test that an invalid action type raises ValueError."""
        with pytest.raises(ValueError):
            audit_service.log_action(
                action="INVALID_ACTION",  # type: ignore
                entity_type="invoice",
                entity_id="inv-123",
                user_id="user-456",
            )

    def test_log_action_with_string_old_new_values(self, audit_service: AuditService) -> None:
        """Test that old_value and new_value can be strings."""
        audit_log = audit_service.log_action(
            action="UPDATE",
            entity_type="invoice",
            entity_id="inv-123",
            user_id="user-456",
            old_value="old string value",
            new_value="new string value",
        )

        assert audit_log.old_value == "old string value"
        assert audit_log.new_value == "new string value"

    def test_log_action_without_optional_fields(self, audit_service: AuditService) -> None:
        """Test that optional fields can be omitted."""
        audit_log = audit_service.log_action(
            action="DELETE",
            entity_type="client",
        )

        assert audit_log.entity_id is None
        assert audit_log.user_id is None
        assert audit_log.old_value is None
        assert audit_log.new_value is None
        assert audit_log.metadata_json is None
        assert audit_log.ip_address is None

    def test_log_action_with_complex_metadata(self, audit_service: AuditService) -> None:
        """Test logging with nested and complex metadata."""
        metadata = {
            "nested": {"level": 2, "data": [1, 2, 3]},
            "list": ["a", "b", "c"],
            "number": 42,
            "boolean": True,
            "null": None,
        }

        audit_log = audit_service.log_action(
            action="EXPORT",
            entity_type="invoice",
            entity_id="inv-123",
            user_id="user-456",
            metadata=metadata,
        )

        assert audit_log.metadata_json is not None
        assert json.loads(audit_log.metadata_json) == metadata

    def test_log_action_persistence(self, audit_service: AuditService, db_session: Session) -> None:
        """Test that logged actions persist in the database."""
        actions = [
            ("CREATE", "invoice", "inv-1"),
            ("UPDATE", "invoice", "inv-1"),
            ("SUBMIT_URSSAF", "invoice", "inv-1"),
        ]

        for action, entity_type, entity_id in actions:
            audit_service.log_action(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id="user-456",
            )

        # Query all logs
        logs = db_session.query(AuditLog).filter_by(entity_id="inv-1").all()
        assert len(logs) == 3
        assert [log.action for log in logs] == ["CREATE", "UPDATE", "SUBMIT_URSSAF"]
