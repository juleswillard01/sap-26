from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.payment_request import PaymentRequest, PaymentRequestStatus

logger = logging.getLogger(__name__)


class PaymentRequestRepository:
    """Repository for PaymentRequest data access."""

    def __init__(self, db: Session) -> None:
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session.
        """
        self._db = db

    def create(self, invoice_id: str, amount: float) -> PaymentRequest:
        """Create a new payment request.

        Args:
            invoice_id: Associated invoice ID.
            amount: Payment amount.

        Returns:
            Created PaymentRequest instance.

        Raises:
            ValueError: If amount is invalid.
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive: {amount}")

        payment_request = PaymentRequest(
            invoice_id=invoice_id,
            amount=amount,
            status=PaymentRequestStatus.PENDING,
        )

        self._db.add(payment_request)
        self._db.commit()
        self._db.refresh(payment_request)

        logger.info(
            "Payment request created",
            extra={"payment_request_id": payment_request.id, "invoice_id": invoice_id},
        )

        return payment_request

    def get_by_invoice_id(self, invoice_id: str) -> PaymentRequest | None:
        """Get payment request by invoice ID.

        Args:
            invoice_id: Invoice ID.

        Returns:
            PaymentRequest instance or None if not found.
        """
        stmt = select(PaymentRequest).where(PaymentRequest.invoice_id == invoice_id)
        return self._db.scalar(stmt)

    def get_by_id(self, payment_request_id: str) -> PaymentRequest | None:
        """Get payment request by ID.

        Args:
            payment_request_id: Payment request ID.

        Returns:
            PaymentRequest instance or None if not found.
        """
        stmt = select(PaymentRequest).where(PaymentRequest.id == payment_request_id)
        return self._db.scalar(stmt)

    def list_pending(self) -> list[PaymentRequest]:
        """List all pending payment requests.

        Returns:
            List of PaymentRequest instances with PENDING status.
        """
        stmt = select(PaymentRequest).where(PaymentRequest.status == PaymentRequestStatus.PENDING)
        return list(self._db.scalars(stmt))

    def list_submitted(self) -> list[PaymentRequest]:
        """List all submitted payment requests (PENDING or not yet resolved).

        Returns:
            List of PaymentRequest instances with non-final statuses.
        """
        final_statuses = [
            PaymentRequestStatus.PAID,
            PaymentRequestStatus.REJECTED,
            PaymentRequestStatus.EXPIRED,
        ]
        stmt = select(PaymentRequest).where(~PaymentRequest.status.in_(final_statuses))
        return list(self._db.scalars(stmt))

    def update_status(
        self,
        payment_request_id: str,
        status: PaymentRequestStatus,
        raw_response: str | None = None,
    ) -> PaymentRequest:
        """Update payment request status.

        Args:
            payment_request_id: Payment request ID.
            status: New status.
            raw_response: Optional raw API response to store.

        Returns:
            Updated PaymentRequest instance.

        Raises:
            ValueError: If payment request not found.
        """
        payment_request = self.get_by_id(payment_request_id)
        if not payment_request:
            raise ValueError(f"Payment request not found: {payment_request_id}")

        old_status = payment_request.status
        payment_request.status = status
        payment_request.updated_at = datetime.utcnow()

        if raw_response is not None:
            payment_request.raw_response = raw_response

        self._db.commit()
        self._db.refresh(payment_request)

        logger.info(
            "Payment request status updated",
            extra={
                "payment_request_id": payment_request_id,
                "old_status": old_status.value,
                "new_status": status.value,
            },
        )

        return payment_request

    def increment_retry_count(self, payment_request_id: str) -> PaymentRequest:
        """Increment retry count for a payment request.

        Args:
            payment_request_id: Payment request ID.

        Returns:
            Updated PaymentRequest instance.

        Raises:
            ValueError: If payment request not found.
        """
        payment_request = self.get_by_id(payment_request_id)
        if not payment_request:
            raise ValueError(f"Payment request not found: {payment_request_id}")

        payment_request.retry_count += 1
        payment_request.updated_at = datetime.utcnow()

        self._db.commit()
        self._db.refresh(payment_request)

        logger.debug(
            "Retry count incremented",
            extra={
                "payment_request_id": payment_request_id,
                "retry_count": payment_request.retry_count,
            },
        )

        return payment_request

    def set_error(
        self,
        payment_request_id: str,
        error_message: str,
    ) -> PaymentRequest:
        """Set error state on payment request.

        Args:
            payment_request_id: Payment request ID.
            error_message: Error message.

        Returns:
            Updated PaymentRequest instance.

        Raises:
            ValueError: If payment request not found.
        """
        payment_request = self.get_by_id(payment_request_id)
        if not payment_request:
            raise ValueError(f"Payment request not found: {payment_request_id}")

        payment_request.status = PaymentRequestStatus.ERROR
        payment_request.error_message = error_message
        payment_request.updated_at = datetime.utcnow()

        self._db.commit()
        self._db.refresh(payment_request)

        logger.error(
            "Payment request error set",
            extra={
                "payment_request_id": payment_request_id,
                "error_message": error_message,
            },
        )

        return payment_request
