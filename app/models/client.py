"""Client data models (Pydantic)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field

# Python 3.10 compatible string literal type for status
URSSAFStatus = Literal["NOT_REGISTERED", "PENDING", "ACTIVE", "ERROR"]


class Client(BaseModel):
    """Client entity (from Google Sheets: Clients onglet)."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique client ID")
    nom: str = Field(min_length=1, max_length=100, description="Last name")
    prenom: str = Field(min_length=1, max_length=100, description="First name")
    email: EmailStr = Field(description="Email address")
    telephone: str | None = Field(None, max_length=20, description="Phone number")
    adresse: str | None = Field(None, max_length=255, description="Street address")
    code_postal: str | None = Field(None, max_length=10, description="Postal code")
    ville: str | None = Field(None, max_length=100, description="City")

    # URSSAF integration
    urssaf_id: str | None = Field(None, description="URSSAF registration ID")
    urssaf_status: URSSAFStatus = Field(default="NOT_REGISTERED", description="URSSAF status")
    date_urssaf_registration: datetime | None = Field(None, description="URSSAF registration date")

    # Metadata
    active: bool = Field(default=True, description="Is client active")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "cli_123456",
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@example.com",
                "telephone": "+33612345678",
                "adresse": "123 Rue de la Paix",
                "code_postal": "75001",
                "ville": "Paris",
                "urssaf_id": None,
                "urssaf_status": "NOT_REGISTERED",
                "active": True,
                "created_at": "2026-03-15T10:00:00",
                "updated_at": "2026-03-15T10:00:00",
            }
        }


class ClientCreateRequest(BaseModel):
    """Request body for creating a client."""

    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    email: EmailStr
    telephone: str | None = None
    adresse: str | None = None
    code_postal: str | None = None
    ville: str | None = None

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "nom": "Dupont",
                "prenom": "Alice",
                "email": "alice@example.com",
                "telephone": "+33612345678",
            }
        }


class ClientUpdateRequest(BaseModel):
    """Request body for updating a client."""

    nom: str | None = None
    prenom: str | None = None
    email: EmailStr | None = None
    telephone: str | None = None
    adresse: str | None = None
    code_postal: str | None = None
    ville: str | None = None
    active: bool | None = None
