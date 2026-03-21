"""Unit tests for SheetsAdapter infrastructure components.

Tests for:
- TokenBucketRateLimiter (rate_limiter.py)
- WriteQueueWorker (write_queue.py)
- Custom exception classes (exceptions.py)
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import Mock

from src.adapters.exceptions import (
    CircuitOpenError,
    RateLimitError,
    SheetsError,
    SheetValidationError,
    SpreadsheetNotFoundError,
    WorksheetNotFoundError,
)
from src.adapters.rate_limiter import TokenBucketRateLimiter
from src.adapters.write_queue import WriteOp, WriteQueueWorker


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter."""

    def test_acquire_within_limit(self) -> None:
        """Five requests succeed immediately when limit is 10."""
        limiter = TokenBucketRateLimiter(max_requests=10, window_seconds=60.0)
        for _ in range(5):
            limiter.acquire()
        assert limiter.available_tokens == 5

    def test_available_tokens_decreases(self) -> None:
        """Available tokens decrease after each acquire."""
        limiter = TokenBucketRateLimiter(max_requests=5, window_seconds=60.0)
        assert limiter.available_tokens == 5
        limiter.acquire()
        assert limiter.available_tokens == 4
        limiter.acquire()
        assert limiter.available_tokens == 3

    def test_try_acquire_returns_false_when_exhausted(self) -> None:
        """try_acquire returns False when max_requests=2 and third call made."""
        limiter = TokenBucketRateLimiter(max_requests=2, window_seconds=60.0)
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False

    def test_try_acquire_returns_true_when_available(self) -> None:
        """try_acquire returns True when slots available."""
        limiter = TokenBucketRateLimiter(max_requests=3, window_seconds=60.0)
        assert limiter.try_acquire() is True
        assert limiter.available_tokens == 2

    def test_wait_time_zero_when_available(self) -> None:
        """wait_time returns 0.0 when slots available."""
        limiter = TokenBucketRateLimiter(max_requests=5, window_seconds=60.0)
        assert limiter.wait_time() == 0.0

    def test_wait_time_positive_when_exhausted(self) -> None:
        """wait_time returns positive value when limit exhausted."""
        limiter = TokenBucketRateLimiter(max_requests=1, window_seconds=60.0)
        limiter.acquire()
        wait = limiter.wait_time()
        assert wait > 0
        assert wait <= 60.0

    def test_tokens_replenish_after_window(self) -> None:
        """Tokens replenish after window expires (0.1s window)."""
        limiter = TokenBucketRateLimiter(max_requests=1, window_seconds=0.1)
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is False
        time.sleep(0.15)
        assert limiter.try_acquire() is True

    def test_available_tokens_calculation(self) -> None:
        """available_tokens correctly reflects current state."""
        limiter = TokenBucketRateLimiter(max_requests=10, window_seconds=60.0)
        assert limiter.available_tokens == 10
        for i in range(3):
            limiter.try_acquire()
            assert limiter.available_tokens == 10 - (i + 1)

    def test_multiple_rapid_acquires(self) -> None:
        """Rapid acquires all succeed up to limit."""
        limiter = TokenBucketRateLimiter(max_requests=100, window_seconds=60.0)
        for _ in range(100):
            assert limiter.try_acquire() is True
        assert limiter.available_tokens == 0


class TestWriteQueueWorker:
    """Tests for WriteQueueWorker."""

    def test_submit_and_execute(self) -> None:
        """Submit WriteOp and verify executor is called."""
        executor_mock = Mock()
        worker = WriteQueueWorker(executor=executor_mock)
        worker.start()

        op = WriteOp(
            sheet_name="Sheet1",
            operation="append",
            data=[["col1", "col2"]],
        )
        worker.submit(op)
        time.sleep(0.1)
        worker.stop()

        executor_mock.assert_called_once_with(op)

    def test_multiple_ops_executed_in_order(self) -> None:
        """Submit 3 ops and verify executor called in order."""
        execution_order: list[str] = []

        def ordered_executor(op: WriteOp) -> None:
            execution_order.append(op.sheet_name)

        worker = WriteQueueWorker(executor=ordered_executor)
        worker.start()

        ops = [
            WriteOp(sheet_name="Sheet1", operation="append", data=[["a"]]),
            WriteOp(sheet_name="Sheet2", operation="append", data=[["b"]]),
            WriteOp(sheet_name="Sheet3", operation="update", data=[["c"]]),
        ]
        for op in ops:
            worker.submit(op)

        time.sleep(0.2)
        worker.stop()

        assert execution_order == ["Sheet1", "Sheet2", "Sheet3"]

    def test_stop_graceful(self) -> None:
        """Start, submit, stop, verify thread dead."""
        executor_mock = Mock()
        worker = WriteQueueWorker(executor=executor_mock)
        worker.start()
        assert worker.is_alive is True

        worker.stop(timeout=2.0)
        assert worker.is_alive is False

    def test_pending_count(self) -> None:
        """Submit 2 ops without starting, verify pending=2."""
        executor_mock = Mock()
        worker = WriteQueueWorker(executor=executor_mock)

        op1 = WriteOp(sheet_name="Sheet1", operation="append", data=[["a"]])
        op2 = WriteOp(sheet_name="Sheet2", operation="append", data=[["b"]])
        worker.submit(op1)
        worker.submit(op2)

        assert worker.pending == 2

    def test_executor_error_does_not_crash_worker(self) -> None:
        """Executor raises exception, next op still executes."""
        executed_sheets: list[str] = []

        def failing_executor(op: WriteOp) -> None:
            if op.sheet_name == "Sheet1":
                raise ValueError("Intentional error")
            executed_sheets.append(op.sheet_name)

        worker = WriteQueueWorker(executor=failing_executor)
        worker.start()

        op1 = WriteOp(sheet_name="Sheet1", operation="append", data=[["a"]])
        op2 = WriteOp(sheet_name="Sheet2", operation="append", data=[["b"]])
        worker.submit(op1)
        worker.submit(op2)

        time.sleep(0.2)
        worker.stop()

        assert "Sheet2" in executed_sheets
        assert worker.is_alive is False

    def test_callback_executed_after_op(self) -> None:
        """Callback is executed after write operation completes."""
        callback_executed = False

        def callback() -> None:
            nonlocal callback_executed
            callback_executed = True

        executor_mock = Mock()
        worker = WriteQueueWorker(executor=executor_mock)
        worker.start()

        op = WriteOp(
            sheet_name="Sheet1",
            operation="append",
            data=[["a"]],
            callback=callback,
        )
        worker.submit(op)

        time.sleep(0.1)
        worker.stop()

        assert callback_executed is True

    def test_multiple_callbacks_executed_in_order(self) -> None:
        """Multiple ops with callbacks execute callbacks in order."""
        callback_order: list[int] = []

        def make_callback(index: int) -> Any:
            def cb() -> None:
                callback_order.append(index)

            return cb

        executor_mock = Mock()
        worker = WriteQueueWorker(executor=executor_mock)
        worker.start()

        for i in range(3):
            op = WriteOp(
                sheet_name=f"Sheet{i}",
                operation="append",
                data=[["data"]],
                callback=make_callback(i),
            )
            worker.submit(op)

        time.sleep(0.2)
        worker.stop()

        assert callback_order == [0, 1, 2]

    def test_is_alive_false_before_start(self) -> None:
        """is_alive returns False before worker started."""
        executor_mock = Mock()
        worker = WriteQueueWorker(executor=executor_mock)
        assert worker.is_alive is False

    def test_is_alive_true_after_start(self) -> None:
        """is_alive returns True after worker started."""
        executor_mock = Mock()
        worker = WriteQueueWorker(executor=executor_mock)
        worker.start()
        assert worker.is_alive is True
        worker.stop()

    def test_pending_count_drains_after_execution(self) -> None:
        """pending_count drains as worker executes ops."""
        executor_mock = Mock()
        worker = WriteQueueWorker(executor=executor_mock)
        worker.start()

        for _ in range(3):
            worker.submit(WriteOp(sheet_name="Sheet1", operation="append", data=[["a"]]))

        time.sleep(0.2)
        assert worker.pending == 0
        worker.stop()


class TestSheetsError:
    """Tests for SheetsError exception."""

    def test_sheets_error_is_exception(self) -> None:
        """SheetsError is an Exception subclass."""
        error = SheetsError("Test error")
        assert isinstance(error, Exception)

    def test_sheets_error_stores_message(self) -> None:
        """SheetsError stores message."""
        error = SheetsError("Custom message")
        assert error.message == "Custom message"

    def test_sheets_error_stores_sheet_name(self) -> None:
        """SheetsError stores sheet_name when provided."""
        error = SheetsError("Error", sheet_name="MySheet")
        assert error.sheet_name == "MySheet"

    def test_sheets_error_default_message(self) -> None:
        """SheetsError has default message."""
        error = SheetsError()
        assert error.message == "An error occurred with Google Sheets"


class TestSpreadsheetNotFoundError:
    """Tests for SpreadsheetNotFoundError exception."""

    def test_spreadsheet_not_found_is_sheets_error(self) -> None:
        """SpreadsheetNotFoundError is a SheetsError subclass."""
        error = SpreadsheetNotFoundError()
        assert isinstance(error, SheetsError)

    def test_spreadsheet_not_found_default_message(self) -> None:
        """SpreadsheetNotFoundError has default message."""
        error = SpreadsheetNotFoundError()
        assert "not found" in error.message.lower()

    def test_spreadsheet_not_found_custom_message(self) -> None:
        """SpreadsheetNotFoundError accepts custom message."""
        error = SpreadsheetNotFoundError("Spreadsheet ABC123 not accessible")
        assert error.message == "Spreadsheet ABC123 not accessible"


class TestWorksheetNotFoundError:
    """Tests for WorksheetNotFoundError exception."""

    def test_worksheet_not_found_is_sheets_error(self) -> None:
        """WorksheetNotFoundError is a SheetsError subclass."""
        error = WorksheetNotFoundError()
        assert isinstance(error, SheetsError)

    def test_worksheet_not_found_has_sheet_name(self) -> None:
        """WorksheetNotFoundError stores sheet_name."""
        error = WorksheetNotFoundError(sheet_name="MissingSheet")
        assert error.sheet_name == "MissingSheet"

    def test_worksheet_not_found_default_message(self) -> None:
        """WorksheetNotFoundError has default message."""
        error = WorksheetNotFoundError()
        assert "not found" in error.message.lower()


class TestSheetValidationError:
    """Tests for SheetValidationError exception."""

    def test_sheet_validation_error_is_sheets_error(self) -> None:
        """SheetValidationError is a SheetsError subclass."""
        error = SheetValidationError()
        assert isinstance(error, SheetsError)

    def test_sheet_validation_error_has_row_info(self) -> None:
        """SheetValidationError stores row_index and field_name."""
        error = SheetValidationError(
            message="Missing field",
            row_index=5,
            field_name="amount",
        )
        assert error.row_index == 5
        assert error.field_name == "amount"

    def test_sheet_validation_error_default_message(self) -> None:
        """SheetValidationError has default message."""
        error = SheetValidationError()
        assert "validation" in error.message.lower()

    def test_sheet_validation_error_row_index_optional(self) -> None:
        """SheetValidationError row_index is optional."""
        error = SheetValidationError(field_name="email")
        assert error.row_index is None
        assert error.field_name == "email"


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_rate_limit_error_is_sheets_error(self) -> None:
        """RateLimitError is a SheetsError subclass."""
        error = RateLimitError()
        assert isinstance(error, SheetsError)

    def test_rate_limit_error_has_retry_after(self) -> None:
        """RateLimitError stores retry_after attribute."""
        error = RateLimitError(retry_after=120.0)
        assert error.retry_after == 120.0

    def test_rate_limit_error_default_retry_after(self) -> None:
        """RateLimitError has default retry_after value."""
        error = RateLimitError()
        assert error.retry_after == 60.0

    def test_rate_limit_error_default_message(self) -> None:
        """RateLimitError has default message."""
        error = RateLimitError()
        assert "rate limit" in error.message.lower()


class TestCircuitOpenError:
    """Tests for CircuitOpenError exception."""

    def test_circuit_open_error_is_sheets_error(self) -> None:
        """CircuitOpenError is a SheetsError subclass."""
        error = CircuitOpenError()
        assert isinstance(error, SheetsError)

    def test_circuit_open_error_default_message(self) -> None:
        """CircuitOpenError has default message."""
        error = CircuitOpenError()
        assert "circuit" in error.message.lower()

    def test_circuit_open_error_custom_message(self) -> None:
        """CircuitOpenError accepts custom message."""
        error = CircuitOpenError("Circuit open due to repeated failures")
        assert error.message == "Circuit open due to repeated failures"

    def test_circuit_open_error_has_sheet_name(self) -> None:
        """CircuitOpenError stores sheet_name."""
        error = CircuitOpenError(sheet_name="Invoices")
        assert error.sheet_name == "Invoices"
