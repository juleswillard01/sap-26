"""Bank reconciliation models (Pydantic)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Python 3.10 compatible string literal type for confidence level
MatchConfidence = Literal["AUTO", "MANUAL"]


class ReconciliationMatch(BaseModel):
    """Matched transaction to invoice (Google Sheets: Lettrage onglet)."""

    invoice_id: str = Field(description="Associated invoice ID")
    transaction_id: str = Field(description="Swan transaction ID")
    montant: float = Field(gt=0, description="Matched amount in EUR")
    matched_at: datetime = Field(default_factory=datetime.utcnow, description="Match timestamp")
    confidence: MatchConfidence = Field(default="AUTO", description="Confidence level")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "invoice_id": "inv_123456",
                "transaction_id": "txn_789012",
                "montant": 50.00,
                "matched_at": "2026-03-15T14:30:00",
                "confidence": "AUTO",
            }
        }


class ReconciliationStatus(BaseModel):
    """Overall bank reconciliation status."""

    total_invoices: int = Field(ge=0, description="Total invoices created")
    total_matched: int = Field(ge=0, description="Invoices with matched transactions")
    match_percentage: float = Field(ge=0, le=100, description="Percentage matched (0-100)")
    total_invoiced: float = Field(ge=0, description="Total invoice amount in EUR")
    total_matched_amount: float = Field(ge=0, description="Total matched amount in EUR")
    unmatched_invoices: list[str] = Field(default_factory=list, description="Unmatched invoice IDs")
    last_sync: datetime | None = Field(None, description="Timestamp of last reconciliation sync")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "total_invoices": 10,
                "total_matched": 9,
                "match_percentage": 90.0,
                "total_invoiced": 500.00,
                "total_matched_amount": 450.00,
                "unmatched_invoices": ["inv_123456"],
                "last_sync": "2026-03-15T12:00:00",
            }
        }
