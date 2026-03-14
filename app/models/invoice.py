from __future__ import annotations

import enum
from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InvoiceStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    VALIDATED = "VALIDATED"
    PAID = "PAID"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class InvoiceType(enum.StrEnum):
    HEURE = "HEURE"
    FORFAIT = "FORFAIT"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id"), nullable=False, index=True
    )

    # Invoice details
    invoice_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    invoice_type: Mapped[InvoiceType] = mapped_column(Enum(InvoiceType), nullable=False)
    nature_code: Mapped[str] = mapped_column(String(10), default="100")  # SAP cours particuliers

    # Dates
    date_service_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_service_to: Mapped[date] = mapped_column(Date, nullable=False)

    # Amounts
    amount_ht: Mapped[float] = mapped_column(Float, nullable=False)
    tva_rate: Mapped[float] = mapped_column(Float, default=0.0)  # Micro-entreprise = 0% TVA
    amount_ttc: Mapped[float] = mapped_column(Float, nullable=False)

    # Status
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus), default=InvoiceStatus.DRAFT, nullable=False, index=True
    )

    # PDF
    pdf_file_path: Mapped[str | None] = mapped_column(String(500))

    # URSSAF reference
    payment_request_id: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="invoices")
    client: Mapped[Client] = relationship("Client", back_populates="invoices")
    payment_requests: Mapped[list[PaymentRequest]] = relationship(
        "PaymentRequest", back_populates="invoice"
    )

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number} {self.status.value}>"
