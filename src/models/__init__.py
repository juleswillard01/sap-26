"""Models — invoices, clients, transactions, Google Sheets."""

from __future__ import annotations

from .client import Client, ClientStatus
from .invoice import VALID_TRANSITIONS, InvalidTransitionError, Invoice, InvoiceStatus
from .sheets import (
    CALC_MODELS,
    DATA_MODELS,
    SHEET_NAMES,
    BalancesSheet,
    ClientSheet,
    ClientStatutURSSAF,
    CotisationsSheet,
    FactureSheet,
    FactureStatut,
    FiscalIRSheet,
    LettrageSheet,
    LettrageStatut,
    MetricsNovaSheet,
    TransactionSheet,
    TransactionType,
)
from .transaction import (
    LettrageResult,
    LettrageStatus,
    Transaction,
    compute_matching_score,
)

__all__ = [
    "CALC_MODELS",
    "DATA_MODELS",
    "SHEET_NAMES",
    "VALID_TRANSITIONS",
    "BalancesSheet",
    "Client",
    "ClientSheet",
    "ClientStatus",
    "ClientStatutURSSAF",
    "CotisationsSheet",
    "FactureSheet",
    "FactureStatut",
    "FiscalIRSheet",
    "InvalidTransitionError",
    "Invoice",
    "InvoiceStatus",
    "LettrageResult",
    "LettrageSheet",
    "LettrageStatus",
    "LettrageStatut",
    "MetricsNovaSheet",
    "Transaction",
    "TransactionSheet",
    "TransactionType",
    "compute_matching_score",
]
