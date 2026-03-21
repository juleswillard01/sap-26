"""Adapter layer — Google Sheets, Indy, PDF, Email."""

from __future__ import annotations

from .exceptions import SheetsError
from .sheets_adapter import SheetsAdapter
from .write_queue import WriteOp, WriteQueueWorker

__all__ = ["SheetsAdapter", "SheetsError", "WriteOp", "WriteQueueWorker"]
