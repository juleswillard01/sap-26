# Testing Guide -- SAP-Facture

## Overview

SAP-Facture uses two categories of tests:

| Category | Location | Runs in CI | External deps |
|----------|----------|-----------|---------------|
| Unit tests | `tests/test_*.py` | Yes | None (all mocked) |
| Integration tests | `tests/integration/` | No (manual) | Real AIS API |

## Unit Tests

Unit tests mock all external APIs (AIS, Indy, Google Sheets, SMTP) and run
without any credentials or network access.

### Run all unit tests

```bash
uv run pytest
```

This runs with the default addopts from `pyproject.toml`:
- `-x` -- stop on first failure
- `--tb=short` -- short tracebacks
- `--cov=src --cov-fail-under=80` -- 80% coverage gate
- `-m 'not integration_ais'` -- excludes integration tests

### Run a specific test file

```bash
uv run pytest tests/test_ais_api.py -v
```

### Run with full output

```bash
uv run pytest -v --tb=long -o "addopts="
```

## Integration Tests

Integration tests connect to real external services. They are excluded from
CI runs and require manual execution with proper credentials.

### AIS Integration Tests

**Location:** `tests/integration/test_ais_real.py`

**Marker:** `integration_ais`

These tests connect to the real AIS (Avance Immediate Services) REST API at
`https://3u7151jll8.execute-api.eu-west-3.amazonaws.com` and verify:

1. **Login** -- REST authentication returns a valid token
2. **Clients** -- `get_clients()` returns real customer data with correct field mapping
3. **Invoices** -- `get_invoice_statuses()` returns real bill data with correct fields
4. **Reminders** -- `get_pending_reminders()` correctly identifies stale EN_ATTENTE invoices
5. **Read-only** -- `register_client()` and `submit_invoice()` raise `NotImplementedError`

**These tests perform ZERO writes to AIS.** All operations are read-only.

### Prerequisites

1. An AIS professional account (SIREN 991552019)
2. Environment variables set:

```bash
export AIS_EMAIL="your-ais-email@example.com"
export AIS_PASSWORD="your-ais-password"
```

Or create a `.env` file at the project root:

```dotenv
AIS_EMAIL=your-ais-email@example.com
AIS_PASSWORD=your-ais-password
```

### Running AIS Integration Tests

```bash
# Run with marker override (credentials must be set)
uv run pytest tests/integration/test_ais_real.py -m integration_ais -v -o "addopts="

# Run with coverage disabled (integration tests don't count toward coverage gate)
uv run pytest tests/integration/ -m integration_ais -v -o "addopts=" --no-header
```

### Collect without running (verify test discovery)

```bash
uv run pytest tests/integration/ --collect-only -o "addopts="
```

### What to expect

- **Login:** If credentials are valid, all login tests pass immediately.
- **Clients:** Returns the list of customers registered via AIS. May be empty for
  new accounts (tests skip gracefully with `pytest.skip`).
- **Invoices:** Returns all bills (demandes). Tests validate field presence and types.
- **Reminders:** Returns invoices in EN_ATTENTE status older than 36 hours. Often
  empty if no invoices are pending.
- **Read-only:** Always passes -- these test the adapter's `NotImplementedError` guards.

## Pytest Markers

| Marker | Description | Default |
|--------|-------------|---------|
| `integration_ais` | Requires real AIS connection and credentials | Skipped |

Markers are configured in `pyproject.toml` under `[tool.pytest.ini_options]`.

The default `addopts` includes `-m 'not integration_ais'` to exclude integration
tests from regular `uv run pytest` runs.

## CI Configuration

### What runs in CI

- All unit tests (`tests/test_*.py`)
- Ruff linting and formatting check
- Pyright strict type checking
- Coverage gate (80% minimum)

### What does NOT run in CI

- Integration tests (`tests/integration/`) -- no credentials available
- Tests marked `integration_ais` -- explicitly excluded via marker expression

### CI command

```bash
uv run pytest --cov=src --cov-fail-under=80
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run pyright --strict src/
```

## Linting and Formatting

```bash
# Auto-fix lint issues
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/

# Type checking (strict mode, src/ only)
uv run pyright --strict src/
```

## Writing New Tests

### Unit tests

- Place in `tests/test_<module>.py`
- Mock all external APIs (use `respx` for httpx, `unittest.mock` for gspread)
- Follow naming: `test_<what>_<condition>_<expected>`
- Aim for 80%+ coverage on the module under test

### Integration tests

- Place in `tests/integration/test_<service>_real.py`
- Add appropriate marker (`integration_ais`, future: `integration_indy`, etc.)
- Use `pytest.mark.skipif` to skip when credentials are absent
- Module-scoped fixtures for authenticated sessions (avoid repeated logins)
- NEVER write data to external services from integration tests
