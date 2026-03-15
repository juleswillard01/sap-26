# Guide Implémentation : IndyBrowserAdapter avec Playwright

**Date** : Mars 2026
**Auteur** : Winston (BMAD System Architect)
**Phase** : 2 (après MVP Phase 1)

---

## Objectif

Implémenter `IndyBrowserAdapter` pour automatiser l'extraction de transactions bancaires depuis Indy (app.indy.fr) via Playwright, avec fallback sur import manual CSV.

---

## Prérequis

### Dépendances Python
```bash
pip install playwright==1.40.0+
playwright install chromium  # Download browser binary
```

### Configuration .env
```bash
INDY_EMAIL=your_email@example.com
INDY_PASSWORD=your_secure_password
INDY_HEADLESS=true  # false pour debug
```

### Credentials Indy
- Email avec accès à app.indy.fr
- Mot de passe (stocké dans .env, jamais committé)

---

## Architecture du Composant

### Structure de Classe
```python
# src/adapters/indy_browser.py

from __future__ import annotations

import asyncio
import csv
import io
import logging
from datetime import date
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
)
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Transaction(BaseModel):
    """Transaction model (identical to Swan, only source changes)."""
    id: str = Field(min_length=1, max_length=100)
    date: date
    amount: float = Field(gt=0)
    label: str = Field(min_length=1)
    status: str = Field(default="COMPLETED")


class IndyBrowserAdapter:
    """
    Automate Indy transaction extraction via Playwright.

    Responsabilités:
    - Login Indy (email + password)
    - Navigate to Transactions page
    - Export CSV
    - Parse transactions
    - Error handling + fallback manual CSV
    """

    def __init__(
        self,
        email: str,
        password: str,
        headless: bool = True,
        timeout_ms: int = 30000,
    ):
        self.email = email
        self.password = password
        self.headless = headless
        self.timeout_ms = timeout_ms

        # Browser state (None until initialized)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def get_transactions(
        self,
        date_from: date,
        date_to: date,
    ) -> list[Transaction]:
        """
        Extract transactions from Indy.

        Flow:
        1. Setup browser
        2. Login
        3. Export CSV
        4. Parse
        5. Cleanup
        """
        try:
            await self._setup_browser()
            await self._login()
            transactions = await self._export_and_parse(date_from, date_to)
            logger.info(
                "Indy transactions extracted",
                extra={
                    "count": len(transactions),
                    "date_from": date_from.isoformat(),
                    "date_to": date_to.isoformat(),
                },
            )
            return transactions
        except Exception as e:
            logger.error(
                "Indy extraction failed",
                exc_info=True,
                extra={"error": str(e)},
            )
            # Capture screenshot for debugging
            if self.page:
                await self._capture_error_screenshot()
            raise
        finally:
            await self._cleanup()

    async def parse_csv_export(self, csv_path: str) -> list[Transaction]:
        """
        Parse transactions from manual CSV export (fallback).

        CSV format expected:
        ID,Date,Montant,Libellé,Status
        TXN001,2026-03-15,150.00,URSSAF Virement,COMPLETED
        """
        transactions = []
        csv_file = Path(csv_path)

        if not csv_file.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
                try:
                    txn = Transaction(
                        id=row.get("ID", "").strip(),
                        date=self._parse_date(row.get("Date", "")),
                        amount=float(row.get("Montant", 0)),
                        label=row.get("Libellé", "").strip(),
                        status=row.get("Status", "COMPLETED").strip(),
                    )
                    transactions.append(txn)
                except Exception as e:
                    logger.warning(
                        f"CSV parse error at row {row_num}",
                        exc_info=True,
                        extra={"row": row},
                    )

        logger.info(f"Parsed {len(transactions)} from CSV: {csv_path}")
        return transactions

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _setup_browser(self) -> None:
        """Initialize Playwright browser."""
        logger.info("Setting up Playwright browser")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless
        )
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def _login(self) -> None:
        """Login to Indy with email + password."""
        logger.info(f"Logging in to Indy as {self.email}")
        assert self.page is not None

        # Navigate to login page
        await self.page.goto("https://app.indy.fr/login", wait_until="load")

        # Fill email
        await self.page.fill(
            'input[type="email"]',
            self.email,
            timeout=self.timeout_ms,
        )

        # Fill password
        await self.page.fill(
            'input[type="password"]',
            self.password,
            timeout=self.timeout_ms,
        )

        # Click login button
        await self.page.click(
            'button[type="submit"]',
            timeout=self.timeout_ms,
        )

        # Wait for dashboard to load (redirected after login)
        await self.page.wait_for_url(
            "https://app.indy.fr/**",
            timeout=self.timeout_ms,
        )

        logger.info("Login successful")

    async def _export_and_parse(
        self,
        date_from: date,
        date_to: date,
    ) -> list[Transaction]:
        """Navigate to Transactions and export CSV."""
        assert self.page is not None

        logger.info(f"Extracting transactions: {date_from} to {date_to}")

        # Navigate to Transactions page
        await self.page.goto(
            "https://app.indy.fr/transactions",
            wait_until="load",
            timeout=self.timeout_ms,
        )

        # Wait for table to appear
        await self.page.wait_for_selector(
            "table tbody tr",
            timeout=self.timeout_ms,
        )

        # [Optional] Filter by date range if UI supports
        # (Adjust selectors based on actual Indy UI)
        try:
            await self.page.fill(
                'input[aria-label="Date From"]',
                date_from.isoformat(),
                timeout=5000,
            )
            await self.page.fill(
                'input[aria-label="Date To"]',
                date_to.isoformat(),
                timeout=5000,
            )
            await self.page.click('button:has-text("Apply")', timeout=5000)
            await self.page.wait_for_selector(
                "table tbody tr",
                timeout=self.timeout_ms,
            )
        except Exception as e:
            logger.warning(
                "Date filter not available, proceeding without filter",
                extra={"error": str(e)},
            )

        # Click Export button
        await self.page.click(
            'button:has-text("Export")',
            timeout=self.timeout_ms,
        )

        # Handle download dialog
        async with self.page.expect_download() as download_info:
            await self.page.click('a:has-text("CSV")', timeout=self.timeout_ms)

        download = await download_info.value
        csv_path = await download.path()

        try:
            # Parse CSV
            transactions = await asyncio.to_thread(
                self.parse_csv_export, str(csv_path)
            )
            return transactions
        finally:
            # Cleanup temp file
            try:
                Path(csv_path).unlink()
            except Exception:
                pass  # Ignore cleanup errors

    async def _capture_error_screenshot(self) -> None:
        """Capture screenshot for debugging on error."""
        if not self.page:
            return

        screenshot_path = f"/tmp/indy_error_{date.today().isoformat()}.png"
        try:
            await self.page.screenshot(path=screenshot_path)
            logger.error(f"Error screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")

    async def _cleanup(self) -> None:
        """Close browser and cleanup."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser cleanup complete")

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """Parse date from various formats."""
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date: {date_str}")
```

---

## Intégration dans BankReconciliation

```python
# src/services/bank_reconciliation.py

from datetime import date
from typing import Optional

from src.adapters.indy_browser import IndyBrowserAdapter
from src.models import Transaction


class BankReconciliation:
    def __init__(self, indy_adapter: IndyBrowserAdapter, sheets_adapter, ...):
        self.indy = indy_adapter
        self.sheets = sheets_adapter
        # ...

    async def reconcile(
        self,
        date_from: date,
        date_to: date,
        csv_path: Optional[str] = None,
    ):
        """
        Reconcile invoices with bank transactions.

        Args:
            date_from: Start date
            date_to: End date
            csv_path: Optional path to manual CSV export (fallback)
        """
        # 1. Get transactions (Playwright or manual CSV)
        if csv_path:
            logger.info(f"Loading transactions from manual CSV: {csv_path}")
            transactions = await self.indy.parse_csv_export(csv_path)
        else:
            logger.info("Extracting transactions via Playwright")
            transactions = await self.indy.get_transactions(date_from, date_to)

        # 2. Import to Sheets
        await self.sheets.write_transactions(transactions)
        logger.info(f"Imported {len(transactions)} to Sheets")

        # 3. Get PAYE invoices
        invoices = await self.sheets.get_invoices_by_status(["PAYE"])

        # 4. Match & score (algorithm unchanged)
        results = self._score_and_match(invoices, transactions)

        # 5. Write results
        await self.sheets.write_lettrage(results)
        await self.sheets.update_balances()

        return {
            "total": len(invoices),
            "auto": sum(1 for r in results if r["status"] == "LETTRE_AUTO"),
            "verify": sum(1 for r in results if r["status"] == "A_VERIFIER"),
            "no_match": sum(1 for r in results if r["status"] == "PAS_DE_MATCH"),
        }
```

---

## CLI Integration

### Command : `sap reconcile`

```python
# src/cli.py

@click.command()
@click.option(
    "--date-from",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=lambda: (date.today() - timedelta(days=30)).isoformat(),
    help="Start date (default: 30 days ago)",
)
@click.option(
    "--date-to",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=lambda: date.today().isoformat(),
    help="End date (default: today)",
)
@click.option(
    "--csv",
    type=click.Path(exists=True),
    default=None,
    help="Path to manual CSV export (fallback)",
)
async def reconcile(date_from, date_to, csv):
    """Reconcile bank transactions with invoices."""
    try:
        service = BankReconciliation(...)
        result = await service.reconcile(
            date_from.date(),
            date_to.date(),
            csv_path=csv,
        )
        click.echo(f"✓ Reconciliation complete")
        click.echo(f"  Auto: {result['auto']}")
        click.echo(f"  To verify: {result['verify']}")
        click.echo(f"  No match: {result['no_match']}")
    except Exception as e:
        logger.error("Reconciliation failed", exc_info=True)
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Exit(1)
```

### Usage

```bash
# Normal : Playwright automation
sap reconcile --date-from 2026-02-15 --date-to 2026-03-15

# Fallback : Manual CSV
sap reconcile --csv ~/Downloads/indy_export.csv
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_indy_browser.py

import pytest
from datetime import date

from src.adapters.indy_browser import IndyBrowserAdapter, Transaction


@pytest.mark.asyncio
async def test_parse_csv_valid():
    """Test CSV parsing with valid data."""
    adapter = IndyBrowserAdapter("test@example.com", "pass")
    csv_content = """ID,Date,Montant,Libellé,Status
TXN001,2026-03-15,150.00,URSSAF Virement,COMPLETED
TXN002,2026-03-14,200.50,Client Paiement,COMPLETED
"""
    # Create temp CSV
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        csv_path = f.name

    try:
        transactions = await adapter.parse_csv_export(csv_path)
        assert len(transactions) == 2
        assert transactions[0].id == "TXN001"
        assert transactions[0].amount == 150.0
        assert transactions[0].date == date(2026, 3, 15)
    finally:
        import os
        os.unlink(csv_path)


@pytest.mark.asyncio
async def test_parse_csv_invalid_date():
    """Test CSV parsing with invalid date format."""
    adapter = IndyBrowserAdapter("test@example.com", "pass")
    csv_content = """ID,Date,Montant,Libellé,Status
TXN001,INVALID_DATE,150.00,Test,COMPLETED
"""
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(csv_content)
        csv_path = f.name

    try:
        with pytest.raises(ValueError, match="Cannot parse date"):
            await adapter.parse_csv_export(csv_path)
    finally:
        import os
        os.unlink(csv_path)


@pytest.mark.asyncio
async def test_parse_csv_missing_file():
    """Test CSV parsing with missing file."""
    adapter = IndyBrowserAdapter("test@example.com", "pass")

    with pytest.raises(FileNotFoundError):
        await adapter.parse_csv_export("/nonexistent/path.csv")
```

### Integration Tests

```python
# tests/integration/test_reconciliation_indy.py

@pytest.mark.asyncio
async def test_reconciliation_with_csv_fallback(sheets_adapter, indy_adapter):
    """Test reconciliation using CSV fallback."""
    csv_path = "tests/fixtures/indy_export_sample.csv"

    service = BankReconciliation(indy_adapter, sheets_adapter, ...)
    result = await service.reconcile(
        date_from=date(2026, 3, 1),
        date_to=date(2026, 3, 31),
        csv_path=csv_path,
    )

    assert result["total"] > 0
    assert result["auto"] + result["verify"] + result["no_match"] == result["total"]
```

---

## Error Handling & Retry

### Retry Logic with Exponential Backoff

```python
# src/adapters/indy_browser.py (addition to get_transactions)

async def get_transactions_with_retry(
    self,
    date_from: date,
    date_to: date,
    max_retries: int = 3,
) -> list[Transaction]:
    """Extract transactions with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            return await self.get_transactions(date_from, date_to)
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(
                    f"Indy extraction failed after {max_retries} attempts",
                    exc_info=True,
                )
                raise

            wait_time = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(
                f"Indy extraction failed, retrying in {wait_time}s",
                extra={"attempt": attempt + 1, "error": str(e)},
            )
            await asyncio.sleep(wait_time)
```

---

## Monitoring & Alerting

### Metrics to Track

```python
# src/monitoring/metrics.py

from datetime import datetime, timedelta

class IndyMetrics:
    def __init__(self, email_notifier):
        self.email = email_notifier
        self.consecutive_failures = 0
        self.last_success = None

    async def record_success(self, transaction_count: int):
        """Record successful extraction."""
        self.consecutive_failures = 0
        self.last_success = datetime.utcnow()
        logger.info(
            "Indy extraction success",
            extra={"transactions": transaction_count, "timestamp": self.last_success},
        )

    async def record_failure(self, error: str):
        """Record failed extraction."""
        self.consecutive_failures += 1
        logger.error(f"Indy extraction failure #{self.consecutive_failures}: {error}")

        # Alert after 3 consecutive failures
        if self.consecutive_failures >= 3:
            await self.email.send(
                to="jules@example.com",
                subject="SAP-Facture: Indy extraction failed 3 times",
                body=f"""
Indy extraction failed 3 consecutive times.

Last error: {error}

Manual fallback:
1. Export CSV from app.indy.fr/transactions
2. Run: sap reconcile --csv /path/to/export.csv

Automatic retry in 24h.
""",
            )
```

---

## Maintenance & Monitoring

### Monthly UI Test Checklist

```
[ ] Login form still accessible (email/password fields)
[ ] Transactions page URL hasn't changed
[ ] Export button exists and works
[ ] CSV format hasn't changed
[ ] Selectors in code still match actual UI
```

### Logging

All operations logged with structured JSON (production):

```json
{
  "timestamp": "2026-03-15T10:30:45.123Z",
  "level": "INFO",
  "message": "Indy transactions extracted",
  "service": "IndyBrowserAdapter",
  "count": 42,
  "date_from": "2026-02-15",
  "date_to": "2026-03-15",
  "duration_ms": 4523
}
```

---

## Troubleshooting

### Issue: "Session expired" on login

**Cause** : Credentials in .env are incorrect or Indy account locked
**Solution** :
1. Verify credentials in `.env`
2. Test login manually at app.indy.fr
3. Check if 2FA enabled (not supported by automation)

### Issue: "Selector not found" on export

**Cause** : Indy UI changed, selectors outdated
**Solution** :
1. Run with `INDY_HEADLESS=false` to see browser
2. Compare selectors in code with actual page elements
3. Update selectors in IndyBrowserAdapter
4. Test with sample CSV fallback: `sap reconcile --csv /path/to/export.csv`

### Issue: Timeout 30s exceeded

**Cause** : Network slow, page taking too long
**Solution** :
1. Increase `timeout_ms` in IndyBrowserAdapter init
2. Check Indy app status (may be down)
3. Use CSV fallback if automation unreliable

---

## Conclusion

`IndyBrowserAdapter` provides pragmatic, automated extraction with robust fallback. For implementation, follow this guide and reference the pseudo-code in `/docs/architecture/architecture.md` (Section 3.4.2).

Contact Winston (BMAD System Architect) for questions.

---

**Version** : 1.0
**Date** : Mars 2026
**Référence** : `docs/architecture/architecture.md` (ADR-006), `docs/DEVIATION_INDY_PLAYWRIGHT.md`
