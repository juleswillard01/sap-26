"""Invoice data models (Pydantic)."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class InvoiceStatus(StrEnum):
    """Invoice lifecycle status."""

    DRAFT = "DRAFT"  # Created, not submitted
    SUBMITTED = "SUBMITTED"  # Submitted to URSSAF, waiting validation
    VALIDATED = "VALIDATED"  # Validated by URSSAF, payment pending
    PAID = "PAID"  # Payment received and reconciled
    CANCELLED = "CANCELLED"  # Cancelled or refunded


class InvoiceLineItem(BaseModel):
    """Line item in an invoice."""

    description: str = Field(min_length=1, max_length=255, description="Service description")
    quantity: float = Field(gt=0, description="Quantity (hours, units)")
    unit_price: float = Field(gt=0, description="Unit price in EUR")

    @property
    def total(self) -> float:
        """Calculate line total."""
        return self.quantity * self.unit_price

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "description": "Cours particuliers - Mathématiques",
                "quantity": 2.0,
                "unit_price": 25.00,
            }
        }


class Invoice(BaseModel):
    """Invoice entity (from Google Sheets: Factures onglet)."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique invoice ID")
    client_id: str = Field(min_length=1, description="Associated client ID")
    items: list[InvoiceLineItem] = Field(min_length=1, description="Line items")
    montant_total: float = Field(gt=0, le=100000, description="Total invoice amount in EUR")

    # Status tracking
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT, description="Invoice status")
    date_emission: date = Field(description="Emission date")
    date_due: date | None = Field(None, description="Due date (auto: emission + 30j)")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    submitted_at: datetime | None = Field(None, description="Submission to URSSAF timestamp")
    validated_at: datetime | None = Field(None, description="URSSAF validation timestamp")
    paid_at: datetime | None = Field(None, description="Payment received timestamp")

    # URSSAF integration
    urssaf_declaration_id: str | None = Field(None, description="URSSAF declaration ID after submission")
    urssaf_error: str | None = Field(None, description="URSSAF error message if submission failed")

    # Metadata
    notes: str | None = Field(None, max_length=500, description="Internal notes")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "inv_123456",
                "client_id": "cli_789012",
                "items": [
                    {
                        "description": "Cours particuliers - Mathématiques",
                        "quantity": 2.0,
                        "unit_price": 25.00,
                    }
                ],
                "montant_total": 50.00,
                "status": "DRAFT",
                "date_emission": "2026-03-15",
                "created_at": "2026-03-15T10:00:00",
            }
        }


class InvoiceCreateRequest(BaseModel):
    """Request body for creating an invoice."""

    client_id: str = Field(min_length=1)
    items: list[InvoiceLineItem] = Field(min_length=1)
    montant_total: float = Field(gt=0, le=100000)
    date_emission: date
    notes: str | None = None

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "client_id": "cli_789012",
                "items": [
                    {
                        "description": "Cours particuliers - Mathématiques",
                        "quantity": 2.0,
                        "unit_price": 25.00,
                    }
                ],
                "montant_total": 50.00,
                "date_emission": "2026-03-15",
                "notes": "Paiement dans les 30 jours",
            }
        }
