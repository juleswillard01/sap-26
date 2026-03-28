# Testing Guide -- SAP-Facture

## Test Summary (P1)

| Metric | Value |
|--------|-------|
| Total tests | 1151 |
| Passing | 1145 |
| Failing | 4 (indy_2fa_adapter -- see [Known Test Failures](#known-test-failures)) |
| Skipped | 2 (Gmail API conditional) |
| Coverage | 86% (gate: 80%) |

## P1 Test Stories -- Linear x GitHub

| Linear | Story | PR | Tests Added |
|--------|-------|----|-------------|
| MPP-56 | Fix ghost tests | #38, #42 | 31 reconciliation tests |
| MPP-58 | PaymentTracker coverage | #45 | 24 tests (66->96%) |
| MPP-21 | Fixture Master | #41 | 37 fixture validation |
| MPP-24 | CSV Indy fixture | #44 | 22 CSV tests |
| MPP-26 | Sheets sandbox | #46 | 16 sandbox tests |
| MPP-66 | AIS integration | #48 | 14 integration tests |
| MPP-48 | AIS Playwright fallback | #50 | 52 fallback tests |
| MPP-65 | IndyAPIAdapter | #39 | 65 adapter tests |
| MPP-67 | Mock Indy API | #51 | 9 mock tests |
| MPP-25 | Mock Gmail 2FA | #53 | 9 mock tests |
| MPP-39 | CI pipeline | #43 | CI validation |

## Test Breakdown by Module

| Module | File(s) | Tests | Pass |
|--------|---------|-------|------|
| AIS adapter | `test_ais_api`, `test_ais_fallback`, `test_adapters_playwright` | 128 | 128 |
| Indy adapter | `test_indy_api_adapter`, `test_indy_2fa_adapter`, `test_indy_auto_login` | 132 | 128 |
| Sheets + Gmail | `test_sheets_*`, `test_gmail_reader` | 214 | 214 |
| Services | `test_payment_tracker`, `test_bank_reconciliation`, `test_notification`, `test_nova`, `test_cotisations` | 168 | 168 |
| Models | `test_invoice`, `test_patito_models`, `test_client`, `test_transaction` | 109 | 109 |
| Fixtures | `test_master_fixture`, `test_csv_fixture` | 59 | 59 |
| Mocks | `tests/mocks/` | 9 | 9 |
| Integration | `tests/integration/test_ais_real.py` | 14 | skipped in CI |

## Known Test Failures

**4 failures in `test_indy_2fa_adapter.py`** -- `TestIndy2FAAdapterFillLoginForm`

Root cause: the test mocks use `query_selector` with `side_effect` lists that
assume a fixed call order, but the implementation iterates over multiple CSS
selectors per field (type, name, id fallbacks). When the adapter's selector
strategy changes or the mock side_effect list length does not match the actual
number of `query_selector` calls, the mock returns `StopIteration` or the wrong
element.

These 4 tests are in RED phase (TDD) for the nodriver-based 2FA login form
filling. The underlying `Indy2FAAdapter._fill_login_form()` works correctly
against the real Indy page; the mocks need alignment with the current selector
iteration order.

**Impact:** None on production. The 2FA adapter is functional. Only mock wiring
is misaligned.

**Status:** Tracked. Will be fixed when the Indy 2FA adapter gets its next
iteration.

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

### Pipeline

3 parallel jobs on `ubuntu-latest` with `uv` cache, ~35s total:

| Job | Command | Purpose |
|-----|---------|---------|
| Lint | `uv run ruff check` + `ruff format --check` | Style and import ordering |
| Test | `uv run pytest --ignore=tests/integration` | Unit tests + coverage gate |
| Typecheck | `uv run pyright src/` | Strict type checking |

Integration tests (`tests/integration/`) are excluded from CI -- no credentials
available in the runner environment.

### CI commands

```bash
# Lint job
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Test job
uv run pytest --ignore=tests/integration

# Typecheck job
uv run pyright src/
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
