from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class InvoiceCreate(BaseModel):
    client_id: str = Field(min_length=1)
    description: str = Field(min_length=5, max_length=500)
    invoice_type: Literal["HEURE", "FORFAIT"]
    nature_code: str = Field(default="100", max_length=10)
    date_service_from: date
    date_service_to: date
    amount_ht: float = Field(gt=0, le=100000)
    tva_rate: float = Field(default=0.0, ge=0, le=1)

    @field_validator("date_service_to")
    @classmethod
    def validate_dates(cls, v: date, info: object) -> date:
        from_date = info.data.get("date_service_from")  # type: ignore[union-attr]
        if from_date and v < from_date:
            msg = "date_service_to must be >= date_service_from"
            raise ValueError(msg)
        if from_date and (v.year, v.month) != (from_date.year, from_date.month):
            msg = "Invoice period must be within 1 calendar month (URSSAF rule)"
            raise ValueError(msg)
        return v


class InvoiceResponse(BaseModel):
    id: str
    invoice_number: str
    client_id: str
    description: str
    invoice_type: str
    status: str
    amount_ht: float
    tva_rate: float
    amount_ttc: float
    date_service_from: date
    date_service_to: date
    pdf_file_path: str | None
    payment_request_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
