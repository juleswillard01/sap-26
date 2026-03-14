from __future__ import annotations

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReconciliationStatus(enum.StrEnum):
    MATCHED = "MATCHED"
    PARTIAL = "PARTIAL"
    UNMATCHED = "UNMATCHED"


class PaymentReconciliation(Base):
    __tablename__ = "payment_reconciliations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    payment_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("payment_requests.id"), nullable=False, index=True
    )
    bank_transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bank_transactions.id"), nullable=False, index=True
    )

    status: Mapped[ReconciliationStatus] = mapped_column(
        Enum(ReconciliationStatus), default=ReconciliationStatus.UNMATCHED, nullable=False
    )
    match_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Reconciliation {self.status.value} confidence={self.match_confidence}>"
