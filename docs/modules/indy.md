# Module Indy Export — Cartographie

## Vue d'ensemble

Export automatique des transactions du Journal Book depuis Indy (app.indy.fr) via Playwright headless.
SAP-Facture opere en **LECTURE SEULE** sur Indy. CDC ref: SPEC-003, §3, §4.

Chaine d'authentification: Turnstile bypass (nodriver) -> login -> 2FA OTP (Gmail IMAP) -> session -> export CSV.

## Fichiers source

| Fichier | Lignes | Role |
|---------|--------|------|
| `src/adapters/indy_adapter.py` | 480 | Playwright sync: login, export CSV, parse journal, session persistence |
| `src/adapters/indy_auto_login.py` | 399 | nodriver async: login 2FA auto-inject, retry 3x backoff |
| `src/adapters/indy_2fa_adapter.py` | 584 | nodriver async: orchestration 2FA complete (fill, submit, detect, inject, verify) |
| `src/adapters/gmail_reader.py` | 479 | Gmail IMAP (`GmailReader`) + OAuth2 API (`GmailAPIReader`) pour extraction code 2FA |
| `src/adapters/network_logger.py` | 254 | Intercept Playwright network traffic pour reverse engineering API |

### Classes principales

- **`IndyBrowserAdapter`** (`indy_adapter.py`) -- Playwright sync. Methodes: `connect()`, `export_transactions()`, `export_journal_book()`, `get_balance()`, `close()`. Session persistence via `io/cache/indy_browser_state.json`. Retry 3x tenacity.
- **`IndyAutoLoginNodriver`** (`indy_auto_login.py`) -- nodriver async. Methode `login()` avec 3 retries. Depend de `GmailReader` pour 2FA. Async context manager (`__aenter__`/`__aexit__`).
- **`Indy2FAAdapter`** (`indy_2fa_adapter.py`) -- nodriver async, orchestration 2FA fine-grained. `auto_2fa_login()` avec 7 etapes. Masquage securite (`_mask_email`, `_mask_code`).
- **`GmailReader`** (`gmail_reader.py`) -- IMAP SSL (gmail.com:993). Polling INBOX 5s interval, 60s timeout. Filtre sender, support label custom.
- **`GmailAPIReader`** (`gmail_reader.py`) -- OAuth2 service account. `_search_and_extract_code()` via Gmail API. Alternative recommandee a IMAP.
- **`NetworkLogger`** (`network_logger.py`) -- Capture requests/responses Playwright. Export JSONL + Markdown. Masquage headers sensibles (RGPD).

## Fichiers tests

| Fichier | Lignes | Scope | Tests actifs |
|---------|--------|-------|-------------|
| `tests/test_indy_export.py` | 403 | `IndyBrowserAdapter`: journal book export, CSV parsing, close, integration | ~23 |
| `tests/test_indy_auto_login.py` | 818 | `IndyAutoLoginNodriver`: init, detect 2FA, inject, flow, security, cleanup, errors | ~35 |
| `tests/test_indy_2fa_adapter.py` | 528 | `Indy2FAAdapter`: fill form, submit, detect 2FA, code async, inject, dashboard, masking | ~30 |
| `tests/test_gmail_reader.py` | 1250 | `GmailReader` (IMAP) + `GmailAPIReader` (OAuth2): connect, poll, extract, body, label, close | ~55 |
| `tests/test_gmail_api_reader.py` | 518 | `GmailAPIReader` seulement (RED phase) | **~0 actifs** |
| `tests/test_network_logger.py` | 484 | `NetworkLogger`: init, attach, mask, filter, track, export, integration | ~30 |

### Overlap test_gmail_reader.py / test_gmail_api_reader.py

**Overlap confirme.** Les deux fichiers ciblent `GmailAPIReader`, mais avec des roles differents:

- **`test_gmail_reader.py`** contient les tests **actifs et fonctionnels** pour `GmailAPIReader` (classes `TestGmailAPIReaderInit`, `TestGmailAPIReaderConnect`, `TestGmailAPIReaderGetLatest2FACode`, `TestGmailAPIReaderSearchAndExtract`, `TestGmailAPIReaderGetEmailBody`, `TestGmailAPIReaderExtractCode`, `TestGmailAPIReaderClose` + tests edge cases supplementaires). Ces tests importent et instancient reellement `GmailAPIReader`.

- **`test_gmail_api_reader.py`** est un **squelette RED-phase mort**: quasi tous les tests sont `@pytest.mark.skip` ou ont le code d'assertion commente. Il teste une API fantome (`search()`, `_get_message()`) qui n'existe pas dans l'implementation reelle. Ne fournit aucune couverture effective.

**Recommandation**: supprimer `tests/test_gmail_api_reader.py` -- il est redondant avec les tests actifs dans `test_gmail_reader.py` et teste une interface qui n'a jamais ete implementee.

## Fichiers documentation

| Fichier | Lignes | Contenu |
|---------|--------|---------|
| `docs/specs/SPEC-003-indy-export.md` | 273 | Spec complete: criteres acceptance, architecture, gaps, status |
| `docs/NODRIVER_2FA_QUICK_REF.md` | 284 | Quick ref nodriver 2FA: code samples, selectors, timeouts, debug |
| `docs/TURNSTILE_DECISION_TREE.md` | 343 | Decision tree: OAuth vs Session Persistence, cost-benefit, roadmap |
| `.claude/skills/indy-export/SKILL.md` | 46 | Skill trigger: keywords, code map, regles metier |

## Fichiers tools

| Fichier | Lignes | Role | Adapter src correspondant |
|---------|--------|------|--------------------------|
| `tools/indy_2fa.py` | 150 | Script CLI: lance nodriver + 2FA flow complet | `indy_2fa_adapter.py` + `gmail_reader.py` |
| `tools/indy_intercept.py` | 388 | Intercept API Indy via CDP Network domain (nodriver) | **Partiel** -- `NetworkInterceptor` propre, pas dans src/ |
| `tools/indy_oauth.py` | 434 | Login Indy via Google OAuth (Playwright sync) | **Aucun** -- `IndyGoogleOAuthAutomation` pas dans src/ |
| `tools/indy_oauth_discovery.py` | 302 | Decouverte OAuth client_id Indy (nodriver) | **Aucun** -- script standalone |

### Tools sans adapter src

- **`tools/indy_intercept.py`** -- Contient `NetworkInterceptor` (CDP-based, nodriver). `src/adapters/network_logger.py` fait la meme chose mais via Playwright event listeners. Deux implementations paralleles du meme concept, approches differentes.
- **`tools/indy_oauth.py`** -- Contient `IndyGoogleOAuthAutomation` (Playwright sync, Google OAuth bypass Turnstile). Aucun `src/adapters/indy_oauth_adapter.py` n'existe. Mentionnee dans TURNSTILE_DECISION_TREE.md comme future integration.
- **`tools/indy_oauth_discovery.py`** -- Script de recherche one-shot (nodriver, headed). Pas vocation a etre dans src/.

## Architecture auth (3 strategies coexistantes)

```
Strategy 1: IndyBrowserAdapter (Playwright sync)
  connect("headed")  -> _login_interactive() -> attente 2FA manuelle -> save session
  connect("headless") -> _verify_session() -> reuse session ou RuntimeError

Strategy 2: IndyAutoLoginNodriver (nodriver async)
  login() -> navigate -> fill -> submit -> _detect_2fa_page()
    -> GmailReader.get_latest_2fa_code() -> _inject_2fa_code() -> _wait_for_dashboard()

Strategy 3: Indy2FAAdapter (nodriver async)
  auto_2fa_login() -> _fill_login_form() -> _submit_login_form()
    -> _detect_2fa_page() -> _get_2fa_code_async() -> _inject_and_verify()
    -> _wait_for_dashboard()
```

**Les strategies 2 et 3 sont redondantes.** `IndyAutoLoginNodriver` et `Indy2FAAdapter` font essentiellement la meme chose (nodriver + 2FA Gmail) avec des differences de granularite. `Indy2FAAdapter` est plus modulaire (7 methodes privees decomposees vs 1 grosse `login()`).

## Gaps identifies (repris de SPEC-003)

1. CSV parsing non-robuste: pas de gestion encoding (BOM, Latin-1), separateur `;`, montants format FR (`1.234,56`)
2. Pas de `indy_id` extrait du CSV: dedup par hash composite `(date_valeur, montant, libelle)` -- risque faux positifs
3. Trois implementations login coexistent (consolider)
4. `GmailAPIReader` faiblement testee (~30% coverage reelle, tests skip)
5. Mapping colonnes Indy CSV non verifie contre export reel
6. `tools/indy_oauth.py` et `tools/indy_intercept.py` n'ont pas de correspondant dans `src/adapters/`

## Metriques

| Metrique | Valeur |
|----------|--------|
| Fichiers src | 5 (2196 lignes) |
| Fichiers tests | 6 (4001 lignes) |
| Fichiers docs | 4 (946 lignes) |
| Fichiers tools | 4 (1274 lignes) |
| **Total module** | **19 fichiers, 8417 lignes** |
| Ratio tests/src | 1.82x |
| Tests morts (test_gmail_api_reader.py) | ~518 lignes, 0 tests actifs |
