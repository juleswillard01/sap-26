"""
Data access adapters and external integrations.

Reference: .claude/specs/02-system-architecture.md section 2.4 & 2.5
"""

from __future__ import annotations

from app.adapters.sheets_adapter import ClientRow, InvoiceRow, SheetsAdapter, TransactionRow

__all__ = ["SheetsAdapter", "ClientRow", "InvoiceRow", "TransactionRow"]
