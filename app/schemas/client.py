from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ClientCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=5, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    siret: str | None = Field(default=None, max_length=14)

    @field_validator("siret")
    @classmethod
    def validate_siret(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.replace(" ", "")
            if not v.isdigit() or len(v) != 14:
                msg = "SIRET must be exactly 14 digits"
                raise ValueError(msg)
        return v


class ClientUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=255)
    last_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    siret: str | None = Field(default=None, max_length=14)


class ClientResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    address: str | None
    siret: str | None
    urssaf_registered: bool
    created_at: datetime

    model_config = {"from_attributes": True}
