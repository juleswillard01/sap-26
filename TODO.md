# TODO — SAP-Facture

## Bilan TDD GREEN Pass 1

**540 GREEN / 47 RED / 1 skip** (588 total)

### Tests RED restants (47)

| Fichier | RED | Cause | Action |
|---|---|---|---|
| `test_ais_scrape.py` | 18 | Stubs `NotImplementedError` — AIS Playwright adapter | GREEN Pass 2 (MCP Playwright + credentials AIS) |
| `test_indy_export.py` | 18 | `_parse_journal_csv()` pas implementee | Implementer la logique CSV (pure Python, pas besoin MCP) |
| `test_cli_status.py` | 9 | `sap status` = `raise NotImplementedError` | Implementer la commande status dans `src/cli.py` |
| `test_nova_reporting.py` | 1 | CLI nova command manquante | Ajouter `sap nova` dans `src/cli.py` |
| `test_sap_init.py` | 1 | Mock/import mismatch CLI init | Fixer le mock path dans le test |

### Prochaines etapes

1. **Fixer les 29 RED mockables** (pas besoin de credentials)
   - `_parse_journal_csv()` dans `indy_adapter.py` (18 tests)
   - `sap status` dans `cli.py` (9 tests)
   - `sap nova` dans `cli.py` (1 test)
   - Fix mock `sap init` (1 test)

2. **GREEN Pass 2 — Adapters reels** (besoin credentials + MCP)
   - AIS Playwright : `get_invoice_statuses()`, `get_clients()`, login, session (18 tests)
   - Necessite : MCP Playwright + `.env` avec `AIS_EMAIL`, `AIS_PASSWORD`

3. **REFACTOR** — Nettoyer le code GREEN
   - DRY, KISS, fonctions < 50 lignes
   - Verifier lint + typecheck

4. **Code Review** — gardien-qualite quality gate
   - `ruff check src/ tests/`
   - `pyright --strict src/`
   - Coverage >= 80%

5. **Integration tests** — Google Sheets reel
   - Necessite : `credentials/service_account.json` + spreadsheet ID dans `.env`
