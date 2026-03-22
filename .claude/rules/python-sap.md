# Python SAP-Facture — Patterns Métier

## Fondamentaux

- `from __future__ import annotations` en haut de CHAQUE fichier
- Type hints TOUTES signatures (params + return)
- `pathlib.Path` uniquement (jamais `os.path`)
- `logging` obligatoire (jamais `print()` dans src/)
- Pydantic v2 pour ALL external inputs

## Patterns SAP-Spécifiques

### 1. Modèles Pydantic v2

```python
from pydantic import BaseModel, Field, field_validator

class Invoice(BaseModel):
    facture_id: str = Field(pattern=r"^F\d{3}$")
    montant: float = Field(gt=0)
    statut: Literal["BROUILLON", "SOUMIS", "CREE", "EN_ATTENTE", "VALIDE", "PAYE", "RAPPROCHE"]
    client_id: str

    @field_validator("montant")
    @classmethod
    def validate_montant(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Montant doit être > 0")
        return round(v, 2)
```

### 2. Google Sheets via gspread + Polars

```python
import gspread
import polars as pl
from pathlib import Path

class SheetsAdapter:
    def __init__(self, credentials_path: Path, spreadsheet_id: str) -> None:
        self.gc = gspread.service_account(filename=str(credentials_path.resolve()))
        self.spreadsheet_id = spreadsheet_id
        self._cache: dict[str, pl.DataFrame] = {}

    def get_all_records(self, sheet: str) -> pl.DataFrame:
        # Cache 30s
        if sheet in self._cache:
            return self._cache[sheet]

        ws = self.gc.open_by_key(self.spreadsheet_id).worksheet(sheet)
        data = ws.get_all_records()
        df = pl.DataFrame(data)
        self._cache[sheet] = df
        return df
```

### 3. Playwright Headless (AIS/Indy)

```python
from playwright.async_api import async_playwright
import logging

logger = logging.getLogger(__name__)

async def scrape_ais_invoices() -> list[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto("https://app.avance-immediate.fr", timeout=30000)
        await page.fill("input[name='email']", EMAIL)
        await page.fill("input[name='password']", PASSWORD)
        await page.click("button[type='submit']")
        await page.wait_for_selector("table", timeout=10000)

        # Scrape avec timeout obligatoire
        rows = await page.query_selector_all("table tbody tr")
        logger.info("Scraped rows", extra={"count": len(rows)})

        await browser.close()
        return [...]
```

### 4. Click + Rich CLI

```python
import click
from rich.table import Table
from rich.console import Console

console = Console()

@click.group()
def cli() -> None:
    """SAP-Facture CLI"""
    pass

@cli.command()
@click.option("--client", help="Client ID to filter")
def sync(client: str | None) -> None:
    """Synchroniser AIS → Sheets"""
    console.print("🔄 Sync en cours...", style="blue")
    # ...logic...
    console.print("✅ Sync OK", style="green")
```

### 5. Async I/O Patterns

```python
import asyncio

async def batch_scrape(clients: list[str]) -> list[dict]:
    tasks = [scrape_client(c) for c in clients]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        logger.error("Batch scrape errors", extra={"count": len(errors)})
    return [r for r in results if not isinstance(r, Exception)]
```

### 6. Config via pydantic-settings

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ais_email: str
    ais_password: str
    google_credentials_path: Path = Path(".creds.json")
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False
```

### 7. Repository Pattern

```python
class InvoiceRepository:
    def __init__(self, sheets: SheetsAdapter) -> None:
        self._sheets = sheets

    async def get_by_id(self, facture_id: str) -> Invoice | None:
        df = self._sheets.get_all_records("Factures")
        row = df.filter(pl.col("facture_id") == facture_id)
        return Invoice(**row.to_dicts()[0]) if len(row) > 0 else None

    async def save(self, inv: Invoice) -> None:
        await self._sheets.append_rows("Factures", [inv.model_dump()])
```

## Qualité

- `ruff check --fix && ruff format` (black + isort + flake8)
- `pyright --strict` (zero tolerance type errors)
- `pytest --cov=src --cov-fail-under=80` (80% minimum)
- Max 400 lignes/file, 50 lignes/fonction, 3 indent levels
- Secrets jamais en dur → `.env` obligatoire
