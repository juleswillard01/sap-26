# Module Map — Indy Banking

## Vue d'ensemble

Adapter REST API pour Indy Banking (app.indy.fr) via httpx + Firebase Auth JWT.
SAP-Facture opere en **LECTURE SEULE** sur Indy. CDC ref: SPEC-003, §3, §4.

Chaine d'authentification: nodriver login (Turnstile bypass) -> 2FA Gmail IMAP -> Firebase custom token -> ID token (JWT Bearer) -> refresh automatique httpx.

## Fichiers source

| Fichier | Lignes | Role |
|---------|--------|------|
| `src/adapters/indy_api_adapter.py` | 580 | **REST httpx**: Firebase Auth, 14 endpoints, transactions, balance, CSV export |
| `src/adapters/indy_auto_login.py` | 399 | nodriver async: login 2FA auto-inject, retry 3x backoff |
| `src/adapters/indy_2fa_adapter.py` | 584 | nodriver async: orchestration 2FA complete (fill, submit, detect, inject, verify) |
| `src/adapters/gmail_reader.py` | 479 | Gmail IMAP (`GmailReader`) + OAuth2 API (`GmailAPIReader`) pour extraction code 2FA |
| `src/adapters/indy_adapter.py` | 480 | Playwright sync (legacy): login, export CSV, parse journal, session persistence |
| `src/adapters/network_logger.py` | 254 | Intercept Playwright network traffic pour reverse engineering API |

### Architecture

```
IndyAPIAdapter (REST httpx, primary)
  |
  +-- Firebase Auth JWT
  |     custom token -> ID token -> refresh auto
  |     _exchange_custom_token() / _refresh_bearer_token()
  |
  +-- nodriver login (1x Turnstile bypass)
  |     _login_with_nodriver() -> IndyAutoLoginNodriver
  |     -> 2FA Gmail IMAP -> custom token capture
  |
  +-- httpx endpoints (14 REST)
        get_transactions(), get_balance(), get_account_statements()
        get_accounting_summary(), export_journal_csv(), export_to_csv()
        get_pending_transactions()
```

### Classes principales

- **`IndyAPIAdapter`** (`indy_api_adapter.py`) -- REST httpx. Auth Firebase JWT (custom token -> ID token -> refresh). Methodes: `connect()`, `get_transactions()`, `get_balance()`, `get_account_statements()`, `get_accounting_summary()`, `export_journal_csv()`, `export_to_csv()`, `get_pending_transactions()`, `close()`. Context manager sync. Retry 3x tenacity sur 5xx/timeout.
- **`IndyAutoLoginNodriver`** (`indy_auto_login.py`) -- nodriver async. Methode `login()` avec 3 retries. Depend de `GmailReader` pour 2FA. Async context manager (`__aenter__`/`__aexit__`).
- **`Indy2FAAdapter`** (`indy_2fa_adapter.py`) -- nodriver async, orchestration 2FA fine-grained. `auto_2fa_login()` avec 7 etapes. Masquage securite (`_mask_email`, `_mask_code`).
- **`GmailReader`** (`gmail_reader.py`) -- IMAP SSL (gmail.com:993). Polling INBOX 5s interval, 60s timeout. Filtre sender, support label custom.
- **`GmailAPIReader`** (`gmail_reader.py`) -- OAuth2 service account. `_search_and_extract_code()` via Gmail API. Alternative recommandee a IMAP.
- **`IndyBrowserAdapter`** (`indy_adapter.py`) -- Playwright sync (legacy). Session persistence via `io/cache/indy_browser_state.json`. Retry 3x tenacity.
- **`NetworkLogger`** (`network_logger.py`) -- Capture requests/responses Playwright. Export JSONL + Markdown. Masquage headers sensibles (RGPD).

### indy_api_adapter.py — Methodes cles

| Methode | Visibilite | Description |
|---------|------------|-------------|
| `__init__(settings)` | public | Valide credentials, cree client httpx avec timeout |
| `connect(custom_token?)` | public | Firebase token exchange, ou nodriver login si pas de token |
| `_login_with_nodriver()` | private | Lance nodriver async, capture custom token via CDP |
| `_exchange_custom_token(token)` | private | POST Firebase `signInWithCustomToken` -> ID token + refresh token |
| `_refresh_bearer_token()` | private | POST Firebase `token` endpoint avec refresh token |
| `_ensure_token()` | private | Refresh auto si token expire (buffer 300s) |
| `_ensure_connected()` | private | Guard — leve si `connect()` non appele |
| `_api_get(path, params?)` | private | GET httpx avec Bearer JWT, retry tenacity |
| `_api_post(path, json?)` | private | POST httpx avec Bearer JWT, retry tenacity |
| `get_transactions(start?, end?)` | public | Liste transactions avec dedup par ID, retourne `list[Transaction]` |
| `get_balance()` | public | Solde en EUR (conversion centimes -> euros) |
| `get_account_statements()` | public | Releves de compte |
| `get_accounting_summary()` | public | Resume comptable avec filtre date optionnel |
| `get_pending_transactions()` | public | Transactions en attente |
| `export_journal_csv(start?, end?)` | public | Export journal au format Polars DataFrame |
| `export_to_csv(path, start?, end?)` | public | Ecrit CSV sur disque via pathlib |
| `close()` | public | Ferme client httpx, efface tokens |
| `__enter__/__exit__` | public | Context manager sync |
| `_to_transaction(raw)` | private | Mapping dict -> Pydantic `Transaction`, defensive |

## Fichiers tests

| Fichier | Lignes | Tests | Scope |
|---------|--------|-------|-------|
| `tests/test_indy_api_adapter.py` | 1139 | 65 | `IndyAPIAdapter`: init, connect, token exchange, refresh, transactions, balance, statements, accounting, CSV, retry, errors |
| `tests/test_indy_2fa_adapter.py` | 528 | 30 | `Indy2FAAdapter`: fill form, submit, detect 2FA, code async, inject, dashboard, masking |
| `tests/test_indy_auto_login.py` | 818 | 37 | `IndyAutoLoginNodriver`: init, detect 2FA, inject, flow, security, cleanup, errors, browser launch |
| `tests/test_indy_export.py` | 403 | 24 | `IndyBrowserAdapter` (legacy): journal book export, CSV parsing, close |
| `tests/test_gmail_reader.py` | 1250 | ~55 | `GmailReader` (IMAP) + `GmailAPIReader` (OAuth2) |
| `tests/test_gmail_api_reader.py` | 518 | **~0 actifs** | Squelette RED-phase mort — tous `@pytest.mark.skip` |
| `tests/test_network_logger.py` | 484 | ~30 | `NetworkLogger` |

**Total tests REST (P1 nouveau) : 132** (65 API + 30 2FA + 37 auto login)

**4 pre-existing test failures** dans le module (hors scope P1).

### test_indy_api_adapter.py — 65 tests

| Classe | Tests | Scope |
|--------|-------|-------|
| `TestIndyExceptions` | 8 | Exception hierarchy (IndyAPIError, IndyAuthError, IndyLoginError, IndyConnectionError) |
| `TestIndyAPISettings` | 3 | Settings defaults (base_url, timeout, firebase_key) |
| `TestIndyAPIAdapterInit` | 3 | Init validation (valid, missing email, missing password) |
| `TestConnect` | 4 | Token exchange, nodriver fallback, error propagation |
| `TestIndyAPIAdapterConnectionError` | 4 | Not-connected guards (transactions, balance, statements, summary) |
| `TestIndyAPIAdapterTokenExchange` | 2 | Firebase custom -> ID token, failure |
| `TestIndyAPIAdapterRefreshToken` | 2 | Refresh success, failure |
| `TestIndyAPIAdapterEnsureToken` | 2 | Valid token skip, expired token refresh |
| `TestGetTransactions` | 6 | Happy path, negative amounts, empty, dedup, API error, date params |
| `TestGetBalance` | 3 | Cents-to-EUR conversion, zero, API error |
| `TestGetAccountStatements` | 2 | Happy path, empty |
| `TestGetAccountingSummary` | 2 | Happy path, date filter |
| `TestContextManager` | 2 | Enter/exit, close idempotent |
| `TestRetryBehavior` | 2 | Retry 5xx, no retry 4xx |
| `TestNetworkErrors` | 4 | Timeout, connect error, timeout retry, connect retry |
| `TestFirebaseKeyError` | 2 | Missing idToken in exchange/refresh responses |
| `TestRefreshTokenGuard` | 1 | Refresh with None token raises |
| `TestToTransactionDefensive` | 1 | Malformed transaction skipped |
| `TestGetPendingTransactions` | 2 | Happy path, returns list |
| `TestExportJournalCsv` | 2 | Returns DataFrame, empty DataFrame |
| `TestExportToCsv` | 3 | Writes file, empty file, accounting summary error |
| `TestApiPostError` | 1 | POST API error propagation |
| `TestLoginWithNodriver` | 1 | Async nodriver login integration |
| `TestApiPostNetworkErrors` | 2 | POST timeout, POST connect error |
| `TestCloseIdempotency` | 2 | Close clears state, double close |

### test_indy_2fa_adapter.py — 30 tests

| Scope | Tests |
|-------|-------|
| Fill login form (email by type, by name, missing fields) | 4 |
| Submit form (button text, selector fallback, enter key) | 3 |
| Detect 2FA page (URL, selector, heading, timeout) | 4 |
| Get 2FA code (success, timeout, exception) | 3 |
| Inject and verify (success, no input, no button, by text) | 4 |
| Wait for dashboard (URL, balance element, timeout) | 3 |
| Full flow (success, no 2FA, gmail timeout) | 3 |
| Security masking (email, code) | 6 |

### test_indy_auto_login.py — 37 tests

| Scope | Tests |
|-------|-------|
| Init validation (settings, email, password) | 3 |
| Detect 2FA page (URL, selector, not found) | 3 |
| Inject 2FA code (success, no input, no button) | 3 |
| Wait for dashboard (success, timeout) | 2 |
| Login flow (no 2FA, with 2FA, timeout, injection fail, dashboard fail) | 5 |
| Retry on failure | 1 |
| Gmail reader integration (filter, timeout) | 2 |
| Security (no credentials in logs, no email in logs, screenshot on error) | 3 |
| Cleanup (close, idempotent, context manager) | 3 |
| Error handling (detect exception, inject exception, dashboard exception, login exception, close exception) | 5 |
| Browser launch (success, import error, exception) | 3 |
| Browser relaunch (missing tab, both missing) | 2 |
| Screenshot error handling (missing tab, exception) | 2 |

## Documentation

| Fichier | Lignes | Contenu |
|---------|--------|---------|
| `docs/specs/SPEC-003-indy-export.md` | 273 | Spec complete: criteres acceptance, architecture, gaps, status |
| `docs/specs/INDY_API_CONTRACTS.md` | — | 14 endpoints REST documentes (routes, params, responses) |
| `docs/NODRIVER_2FA_QUICK_REF.md` | 284 | Quick ref nodriver 2FA: code samples, selectors, timeouts, debug |
| `docs/TURNSTILE_DECISION_TREE.md` | 343 | Decision tree: OAuth vs Session Persistence, cost-benefit, roadmap |
| `.claude/skills/indy-export/SKILL.md` | 46 | Skill trigger: keywords, code map, regles metier |

## Fichiers tools

| Fichier | Lignes | Role | Adapter src correspondant |
|---------|--------|------|--------------------------|
| `tools/indy_2fa.py` | 150 | Script CLI: lance nodriver + 2FA flow complet | `indy_2fa_adapter.py` + `gmail_reader.py` |
| `tools/indy_intercept.py` | 388 | Intercept API Indy via CDP Network domain (nodriver) | **Partiel** — `NetworkInterceptor` propre, pas dans src/ |
| `tools/indy_oauth.py` | 434 | Login Indy via Google OAuth (Playwright sync) | **Aucun** — `IndyGoogleOAuthAutomation` pas dans src/ |
| `tools/indy_oauth_discovery.py` | 302 | Decouverte OAuth client_id Indy (nodriver) | **Aucun** — script standalone |

## Architecture auth (3 strategies coexistantes)

```
Strategy 1 (PRIMARY): IndyAPIAdapter (REST httpx + nodriver login)
  _login_with_nodriver() -> IndyAutoLoginNodriver.login()
    -> Turnstile bypass -> fill form -> submit
    -> GmailReader.get_latest_2fa_code() -> inject
    -> capture custom token via CDP response interception
  _exchange_custom_token() -> Firebase ID token (JWT Bearer)
  _refresh_bearer_token() -> auto-refresh avant expiration
  -> Toutes les ops bancaires via httpx REST (pas de browser)

Strategy 2 (LEGACY): IndyBrowserAdapter (Playwright sync)
  connect("headed")  -> _login_interactive() -> attente 2FA manuelle -> save session
  connect("headless") -> _verify_session() -> reuse session ou RuntimeError

Strategy 3 (REDUNDANT): Indy2FAAdapter (nodriver async)
  auto_2fa_login() -> _fill_login_form() -> _submit_login_form()
    -> _detect_2fa_page() -> _get_2fa_code_async() -> _inject_and_verify()
    -> _wait_for_dashboard()
```

**Strategy 1 est le chemin principal.** `IndyAPIAdapter` utilise nodriver uniquement pour le login initial (Turnstile + 2FA), puis toutes les operations passent par REST httpx avec JWT Bearer. Les strategies 2 et 3 sont conservees mais secondaires.

## Gaps identifies

### Tests manquants (P2)

| Element | Gap |
|---------|-----|
| `GmailAPIReader` | Tests actifs uniquement dans `test_gmail_reader.py`, `test_gmail_api_reader.py` est un squelette mort |
| `IndyBrowserAdapter` CSV parsing | Pas de gestion encoding (BOM, Latin-1), separateur `;`, montants format FR |
| Mapping colonnes Indy CSV | Non verifie contre export reel pour `IndyBrowserAdapter` legacy |

### Code a consolider (P3)

| Element | Recommandation |
|---------|----------------|
| `test_gmail_api_reader.py` | Supprimer — squelette RED-phase mort, redondant avec `test_gmail_reader.py` |
| `Indy2FAAdapter` vs `IndyAutoLoginNodriver` | Convergent — `Indy2FAAdapter` est plus modulaire (7 methodes privees) |
| `tools/indy_intercept.py` vs `network_logger.py` | Deux implementations paralleles (CDP vs Playwright events) |
| `tools/indy_oauth.py` | Pas de correspondant dans `src/adapters/` |

### Fonctionnalites absentes (P2)

| Feature | Status |
|---------|--------|
| Dedup par `indy_id` natif | `IndyAPIAdapter.get_transactions()` deduplique par ID |
| Cron `sap reconcile` integration | CLI non connecte a `IndyAPIAdapter` |

## Notes

- L'implementation principale est 100% REST (httpx) via l'API interne Indy. Le browser (nodriver) n'est utilise que pour le login initial (Turnstile bypass + 2FA).
- Firebase Auth JWT: custom token (capture CDP) -> ID token (signInWithCustomToken) -> refresh automatique (buffer 300s avant expiration).
- 14 endpoints REST documentes dans `INDY_API_CONTRACTS.md`.
- `_to_transaction()` est defensive : les transactions malformees sont skippees avec un warning log (pas d'exception).
- Retry tenacity 3x avec backoff exponentiel sur 5xx et erreurs reseau. Les 4xx ne sont PAS retries.
- Read-only : aucune operation d'ecriture sur Indy.

## Metriques

| Metrique | Valeur |
|----------|--------|
| Fichiers src | 6 (2776 lignes) |
| Fichiers tests | 7 (5140 lignes) |
| Fichiers docs | 5 (946+ lignes) |
| Fichiers tools | 4 (1274 lignes) |
| **Total module** | **22 fichiers, 10136+ lignes** |
| Tests REST (P1 nouveau) | 132 (65 + 30 + 37) |
| Tests legacy + support | ~109 (24 export + 55 gmail + 30 network) |
| Tests morts (test_gmail_api_reader.py) | ~518 lignes, 0 tests actifs |
| Pre-existing failures | 4 |
| Ratio tests/src | 1.85x |

## Traceability — Linear × GitHub

| Story | Description | PR | Status |
|-------|------------|-----|--------|
| [MPP-64](https://linear.app/pmm-001/issue/MPP-64) | Reverse API exploration | manual | Done |
| [MPP-65](https://linear.app/pmm-001/issue/MPP-65) | IndyAPIAdapter REST httpx | [#39](https://github.com/juleswillard01/sap-26/pull/39) | Done |
| [MPP-51](https://linear.app/pmm-001/issue/MPP-51) | Export CSV Journal Book | [#52](https://github.com/juleswillard01/sap-26/pull/52) | Done |
| [MPP-67](https://linear.app/pmm-001/issue/MPP-67) | Mock Indy API FastAPI | [#51](https://github.com/juleswillard01/sap-26/pull/51) | Done |
| [MPP-53](https://linear.app/pmm-001/issue/MPP-53) | Gmail auth SA→OAuth fix | [#49](https://github.com/juleswillard01/sap-26/pull/49) | Done |
| [MPP-25](https://linear.app/pmm-001/issue/MPP-25) | Mock Gmail 2FA IMAP | [#53](https://github.com/juleswillard01/sap-26/pull/53) | Done |
| [MPP-24](https://linear.app/pmm-001/issue/MPP-24) | CSV fixture Q1 2026 | [#44](https://github.com/juleswillard01/sap-26/pull/44) | Done |

### Test Summary
- Unit tests: 132 (65 API + 30 2FA + 37 auto login), 4 pre-existing failures
- Mock server: 9 tests
- CSV fixture: 22 tests
