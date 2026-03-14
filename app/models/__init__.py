from __future__ import annotations

import enum
import sys

# Compatibility shim for Python <3.11 - StrEnum added in 3.11
if sys.version_info < (3, 11):
    class StrEnum(str, enum.Enum):
        """StrEnum backport for Python <3.11."""
        def __str__(self) -> str:
            return str(self.value)
    enum.StrEnum = StrEnum

# NOW import models after shim is installed
from app.models.audit_log import AuditLog
from app.models.bank_transaction import BankTransaction
from app.models.client import Client
from app.models.email_queue import EmailQueue
from app.models.invoice import Invoice
from app.models.payment_reconciliation import PaymentReconciliation
from app.models.payment_request import PaymentRequest
from app.models.user import User

__all__ = [
    "AuditLog",
    "BankTransaction",
    "Client",
    "EmailQueue",
    "Invoice",
    "PaymentReconciliation",
    "PaymentRequest",
    "User",
]
