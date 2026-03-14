from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    siren: Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    nova: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    # Encrypted fields (Fernet)
    urssaf_client_id_enc: Mapped[str | None] = mapped_column(String(500))
    urssaf_client_secret_enc: Mapped[str | None] = mapped_column(String(500))
    swan_api_key_enc: Mapped[str | None] = mapped_column(String(500))

    logo_file_path: Mapped[str | None] = mapped_column(String(500))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    clients: Mapped[list[Client]] = relationship("Client", back_populates="user")
    invoices: Mapped[list[Invoice]] = relationship("Invoice", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email}>"
