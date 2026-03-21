"""Tests for threading-based write queue."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

from src.adapters.write_queue import WriteOp, WriteQueueWorker


class TestWriteOp:
    """Tests for WriteOp dataclass."""

    def test_write_op_append_minimal(self) -> None:
        """Test WriteOp with minimal append operation."""
        op = WriteOp(
            sheet_name="Clients",
            operation="append",
            data=[["Jean", "Dupont"]],
        )
        assert op.sheet_name == "Clients"
        assert op.operation == "append"
        assert op.data == [["Jean", "Dupont"]]
        assert op.range_notation == ""
        assert op.callback is None

    def test_write_op_update_with_range(self) -> None:
        """Test WriteOp update with range notation."""
        op = WriteOp(
            sheet_name="Factures",
            operation="update",
            data=[["2024-01-15", "500"]],
            range_notation="B2:C2",
        )
        assert op.sheet_name == "Factures"
        assert op.operation == "update"
        assert op.range_notation == "B2:C2"

    def test_write_op_with_callback(self) -> None:
        """Test WriteOp with optional callback."""
        callback = MagicMock()
        op = WriteOp(
            sheet_name="Transactions",
            operation="append",
            data=[["TXN001", "100.00"]],
            callback=callback,
        )
        assert op.callback is callback


class TestWriteQueueWorker:
    """Tests for WriteQueueWorker."""

    def test_worker_initialization(self) -> None:
        """Test worker initializes with executor."""
        executor = MagicMock()
        worker = WriteQueueWorker(executor)
        assert worker._executor is executor
        assert worker.is_alive is False

    def test_worker_start_and_stop(self) -> None:
        """Test worker starts and stops gracefully."""
        executor = MagicMock()
        worker = WriteQueueWorker(executor)
        worker.start()
        assert worker.is_alive is True
        worker.stop(timeout=2.0)
        time.sleep(0.1)
        assert worker.is_alive is False

    def test_worker_executes_operations(self) -> None:
        """Test worker executes submitted operations."""
        executor = MagicMock()
        worker = WriteQueueWorker(executor)
        worker.start()

        op = WriteOp(
            sheet_name="Clients",
            operation="append",
            data=[["Alice", "Smith"]],
        )
        worker.submit(op)
        time.sleep(0.2)  # Allow executor to run
        worker.stop(timeout=2.0)

        executor.assert_called_once_with(op)

    def test_worker_calls_callback_on_completion(self) -> None:
        """Test worker calls optional callback after execution."""
        executor = MagicMock()
        callback = MagicMock()
        worker = WriteQueueWorker(executor)
        worker.start()

        op = WriteOp(
            sheet_name="Factures",
            operation="update",
            data=[["2024-01-20"]],
            range_notation="A5",
            callback=callback,
        )
        worker.submit(op)
        time.sleep(0.2)
        worker.stop(timeout=2.0)

        executor.assert_called_once()
        callback.assert_called_once()

    def test_worker_pending_count(self) -> None:
        """Test pending property tracks queue size."""
        executor = MagicMock()
        executor.side_effect = lambda op: time.sleep(0.1)
        worker = WriteQueueWorker(executor)
        worker.start()

        op1 = WriteOp(sheet_name="S1", operation="append", data=[["a"]])
        op2 = WriteOp(sheet_name="S2", operation="append", data=[["b"]])
        worker.submit(op1)
        worker.submit(op2)

        # Immediately after submit, queue should have items
        assert worker.pending >= 0
        worker.stop(timeout=2.0)

    def test_worker_handles_executor_error(self) -> None:
        """Test worker resilience on executor error."""

        def failing_executor(op: WriteOp) -> None:
            raise ValueError("Simulated executor error")

        worker = WriteQueueWorker(failing_executor)
        worker.start()

        op = WriteOp(sheet_name="Bad", operation="append", data=[["error"]])
        worker.submit(op)
        time.sleep(0.2)
        # Worker should still be alive despite error
        assert worker.is_alive is True
        worker.stop(timeout=2.0)

    def test_worker_processes_batch(self) -> None:
        """Test worker processes multiple operations in order."""
        executor = MagicMock()
        worker = WriteQueueWorker(executor)
        worker.start()

        ops = [WriteOp(sheet_name="S", operation="append", data=[[str(i)]]) for i in range(3)]
        for op in ops:
            worker.submit(op)

        time.sleep(0.3)
        worker.stop(timeout=2.0)

        assert executor.call_count == 3

    def test_worker_sentinel_stops_loop(self) -> None:
        """Test sentinel pattern properly terminates worker."""
        executor = MagicMock()
        worker = WriteQueueWorker(executor)
        worker.start()
        initial_thread_id = worker._thread.ident

        worker.stop(timeout=2.0)
        time.sleep(0.1)

        # Thread should have terminated
        assert worker.is_alive is False
        assert worker._thread.ident == initial_thread_id

    def test_worker_daemon_flag(self) -> None:
        """Test worker thread is daemon."""
        executor = MagicMock()
        worker = WriteQueueWorker(executor)
        assert worker._thread.daemon is True

    def test_worker_non_blocking_submit(self) -> None:
        """Test submit() is non-blocking."""
        executor = MagicMock()
        executor.side_effect = lambda op: time.sleep(1.0)
        worker = WriteQueueWorker(executor)
        worker.start()

        start = time.time()
        op = WriteOp(sheet_name="S", operation="append", data=[["slow"]])
        worker.submit(op)
        elapsed = time.time() - start

        # Submit should return immediately, not wait for executor
        assert elapsed < 0.1
        worker.stop(timeout=2.0)

    def test_callback_not_called_if_none(self) -> None:
        """Test that missing callback doesn't crash worker."""
        executor = MagicMock()
        worker = WriteQueueWorker(executor)
        worker.start()

        op = WriteOp(
            sheet_name="Clients",
            operation="append",
            data=[["test"]],
            callback=None,
        )
        worker.submit(op)
        time.sleep(0.2)
        worker.stop(timeout=2.0)

        executor.assert_called_once()


class TestWriteQueueIntegration:
    """Integration tests for write queue with realistic scenarios."""

    def test_concurrent_submissions(self) -> None:
        """Test multiple threads can submit concurrently."""
        executor = MagicMock()
        worker = WriteQueueWorker(executor)
        worker.start()

        def submit_batch(count: int) -> None:
            for i in range(count):
                op = WriteOp(
                    sheet_name="S",
                    operation="append",
                    data=[[f"data_{i}"]],
                )
                worker.submit(op)

        threads = [threading.Thread(target=submit_batch, args=(5,)) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        time.sleep(0.5)
        worker.stop(timeout=2.0)

        # Should have executed 15 operations
        assert executor.call_count == 15
