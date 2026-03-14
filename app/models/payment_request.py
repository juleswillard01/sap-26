from __future__ import annotations

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PaymentRequestStatus(enum.StrEnum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    PAID = "PAID"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ERROR = "ERROR"


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id"), nullable=False, index=True
    )

    # URSSAF reference
    urssaf_request_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    status: Mapped[PaymentRequestStatus] = mapped_column(
        Enum(PaymentRequestStatus), default=PaymentRequestStatus.PENDING, nullable=False
    )

    # Payment details from URSSAF
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    validation_deadline: Mapped[datetime | None] = mapped_column(DateTime)
    payout_date: Mapped[datetime | None] = mapped_column(DateTime)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(default=0)

    # Raw URSSAF response
    raw_response: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="payment_requests")

    def __repr__(self) -> str:
        return f"<PaymentRequest {self.urssaf_request_id} {self.status.value}>"
