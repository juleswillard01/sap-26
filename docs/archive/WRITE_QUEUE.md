# WriteQueueWorker — Threading-based Write Serialization

## Overview

The `WriteQueueWorker` serializes Google Sheets writes via a dedicated worker thread, preventing race conditions and ensuring FIFO ordering.

## Usage Example

```python
from src.adapters.write_queue import WriteOp, WriteQueueWorker

# Define executor (e.g., in SheetsAdapter)
def execute_write(op: WriteOp) -> None:
    """Execute a single write operation via gspread."""
    worksheet = get_worksheet(op.sheet_name)
    if op.operation == "append":
        worksheet.append_rows(op.data)
    elif op.operation == "update":
        worksheet.update(op.range_notation, op.data)

# Create and start worker
worker = WriteQueueWorker(executor=execute_write)
worker.start()

# Submit operations (non-blocking)
op = WriteOp(
    sheet_name="Clients",
    operation="append",
    data=[["Alice", "Dupont", "alice@example.com"]],
    callback=lambda: print("Write completed")
)
worker.submit(op)

# Graceful shutdown
worker.stop(timeout=5.0)
```

## API Reference

### WriteOp

Dataclass representing a single write operation.

**Fields:**
- `sheet_name: str` — Target worksheet name
- `operation: Literal["append", "update"]` — Write mode
- `data: list[list[str]]` — Rows to write (for append) or new cell values (for update)
- `range_notation: str = ""` — Range (e.g., "A2:D5") for update operations
- `callback: Callable[[], None] | None = None` — Optional completion callback

### WriteQueueWorker

Thread-safe worker for serialized sheet writes.

**Methods:**
- `__init__(executor: Callable[[WriteOp], None])` — Initialize with executor callback
- `start() -> None` — Start the worker thread
- `stop(timeout: float = 5.0) -> None` — Gracefully shutdown (sends sentinel, joins thread)
- `submit(op: WriteOp) -> None` — Enqueue a write operation (non-blocking)

**Properties:**
- `is_alive: bool` — True if worker thread is running
- `pending: int` — Approximate queue size

## Design Principles

1. **Thread Safety**: Uses `queue.Queue` (thread-safe by design)
2. **Non-blocking**: `submit()` returns immediately, work happens in background
3. **Graceful Shutdown**: Sentinel pattern (`None`) terminates worker cleanly
4. **Error Resilience**: Exceptions logged but don't crash worker; continues processing
5. **Daemon Thread**: Worker thread doesn't block process shutdown
6. **Dependency Injection**: Executor callback injected at init (loose coupling)

## Integration with SheetsAdapter

The `SheetsAdapter` will:
1. Create `WriteQueueWorker(executor=self._execute_write)` on init
2. Call `start()` in `__enter__` or during init
3. Submit writes via `queue.submit(WriteOp(...))` instead of direct gspread calls
4. Call `stop()` in `__exit__` or during cleanup

## Performance Characteristics

- **Submission**: O(1) — just enqueues to `queue.Queue`
- **Throughput**: Depends on gspread rate limit (60 req/min)
- **Memory**: Bounded by queue size (typically <100 pending ops)
- **Latency**: ~0-500ms per operation (network + gspread processing)
