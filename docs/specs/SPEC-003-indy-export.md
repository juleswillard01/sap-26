# SPEC-003 — Indy Export

## Objectif

Exporter automatiquement les transactions du Journal Book depuis Indy (app.indy.fr) via Playwright headless pour alimenter l'onglet Transactions de Google Sheets et permettre le rapprochement bancaire avec les factures URSSAF (CDC §4).

SAP-Facture opère en **LECTURE SEULE** sur Indy. Aucune modification comptable, aucune ecriture dans Indy.

## Perimetre

### Ce que SAP-Facture fait

- Login Indy via nodriver (bypass Cloudflare Turnstile) + 2FA automatique via Gmail IMAP
- Navigation Documents > Comptabilite > Export CSV
- Export Journal Book CSV (revenus uniquement)
- Parse CSV → `date_valeur`, `montant`, `libelle`, `type`
- Dedup par cle composite `(date_valeur, montant, libelle)`
- Maj onglet Transactions (`date_import`, `source="indy"`)
- Retry 3x backoff exponentiel sur export et login
- Screenshots erreur RGPD-safe dans `io/cache/` (sans donnees sensibles)

### Ce que SAP-Facture NE fait PAS

- PAS de modification de la comptabilite Indy
- PAS d'ecriture dans Indy (lecture seule)
- PAS de generation de factures (AIS le fait — D1, D7)
- PAS d'API bancaire directe (D5 : Playwright impose par l'absence d'API)

## Criteres d'Acceptance

### Login & Authentification
- [x] `IndyBrowserAdapter.__init__()` valide que `indy_email` et `indy_password` sont presents
- [x] Mode headed : login interactif avec attente 2FA manuelle (timeout 2 min)
- [x] Mode headless : reutilisation session persistee (`io/cache/indy_browser_state.json`)
- [x] Verification session : navigation dashboard + check `[data-testid='account-balance']`
- [x] Session expiree → RuntimeError avec message explicite

### Authentification nodriver (2FA auto)
- [x] `IndyAutoLoginNodriver` : login avec retry 3x et backoff exponentiel
- [x] Detection page 2FA par URL patterns (`/verification`, `/verify`, `/two-fa`, `2fa`)
- [x] Detection page 2FA par selecteurs formulaire (`input[name='code']`, etc.)
- [x] Extraction code 2FA depuis Gmail IMAP via `GmailReader.get_latest_2fa_code()`
- [x] Injection code 2FA dans champ input + clic bouton verify
- [x] Attente dashboard apres 2FA (polling avec timeout)
- [x] Async context manager (`__aenter__`/`__aexit__`) pour cleanup

### Authentification nodriver (2FA adapter)
- [x] `Indy2FAAdapter` : orchestration complete du flow 2FA
- [x] Remplissage formulaire login (multi-selecteurs : `input[type='email']`, `input[name='email']`, etc.)
- [x] Soumission formulaire (texte bouton FR/EN, `button[type='submit']`, fallback Enter)
- [x] Detection page 2FA par URL, selecteurs, et contenu headings
- [x] Polling Gmail asynchrone via `run_in_executor` (non-bloquant)
- [x] Injection code + clic verify (multi-strategies pour bouton)
- [x] Masquage email dans logs (`j***@example.com`)
- [x] Masquage code dans logs (`123***`)

### Gmail IMAP (extraction code 2FA)
- [x] `GmailReader` : connexion IMAP SSL (gmail.com:993) avec app password
- [x] Polling INBOX avec timeout configurable (default 60s, poll 5s)
- [x] Filtrage par sender (`indy` dans From)
- [x] Support label Gmail custom (fallback INBOX)
- [x] Extraction code 4-8 digits avec preference 6 digits (pattern `\b(\d{4,8})\b`)
- [x] Parse body plaintext et HTML (multipart)
- [x] `GmailAPIReader` : alternative OAuth2 (credentials.json + token.json)

### Export Journal Book
- [x] `export_journal_book()` navigue vers `/dashboard/documents/comptabilite`
- [x] Attente bouton Export, declenchement telechargement CSV
- [x] `@retry` 3x backoff exponentiel (tenacity)
- [x] Screenshot erreur RGPD-safe sur echec

### CSV Parsing
- [x] `_parse_journal_csv()` valide colonnes requises : `date_valeur`, `montant`, `libelle`, `type`
- [x] Filtre revenus uniquement (`type == "revenus"`)
- [x] Conversion `montant` string → float
- [x] Skip montants zero
- [x] Validation format date `YYYY-MM-DD`
- [x] Strip whitespace sur `libelle`
- [x] Dedup par cle `(date_valeur, montant, libelle)`
- [x] ValueError sur CSV vide, colonnes manquantes, montant invalide, date invalide
- [ ] **GAP** : Gestion encoding CSV non-UTF-8 (BOM, Latin-1)
- [ ] **GAP** : Gestion separateur CSV variable (`;` vs `,`)
- [ ] **GAP** : Gestion montants format FR (`1.234,56` vs `1234.56`)
- [ ] **GAP** : Mapping colonnes Indy reelles → colonnes attendues (noms exacts non verifies)
- [ ] **GAP** : `transaction_id` / `indy_id` non extrait du CSV (dedup par hash composite)

### Securite
- [x] Credentials valides au `__init__` (pas de login avec champs vides)
- [x] Pas de credentials dans les logs (email masque, password jamais log)
- [x] Code 2FA efface de memoire apres usage (`del code`)
- [x] Screenshots RGPD-safe (pas de donnees sensibles)
- [x] Credentials dans `.env` (jamais hardcode)

## Decisions Verrouillees

| ID | Decision | Justification |
|----|----------|---------------|
| D5 | Playwright Indy export Journal CSV | Pas d'API bancaire Indy |
| D5a | nodriver pour bypass Cloudflare Turnstile | Playwright detecte par Turnstile, nodriver (undetected-chromedriver) passe |
| D5b | Gmail IMAP pour extraction code 2FA | Indy envoie code par email, pas SMS ; IMAP polling est le plus fiable |
| D5c | Session persistence comme fallback | Cookies valides 30-90 jours, login interactif periodique acceptable |
| D5d | Google OAuth envisage comme upgrade | Zero maintenance si OAuth client_id Indy decouverte (voir TURNSTILE_DECISION_TREE.md) |

## Architecture

### Chaine d'authentification complete

```
┌─────────────────────────────────────────────────────────┐
│                   IndyBrowserAdapter                     │
│  (Playwright sync — export CSV, navigation)              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  connect(session_mode)                                   │
│  ├─ "headless" → reutilise session persistee             │
│  │   └─ _verify_session() → dashboard check              │
│  │       └─ Si expire → RuntimeError                     │
│  │                                                       │
│  └─ "headed" → _login_interactive()                      │
│       └─ Remplit email/password                          │
│       └─ Attend 2FA manuelle (2 min timeout)             │
│       └─ Sauvegarde session state (JSON)                 │
│                                                          │
│  OU (automatise)                                         │
│                                                          │
│  IndyAutoLoginNodriver (nodriver async)                   │
│  ├─ login() — 3 tentatives avec backoff                  │
│  │   ├─ _launch_browser() → nodriver.start()             │
│  │   ├─ Navigate login page                              │
│  │   ├─ Fill email + password (multi-selecteurs)         │
│  │   ├─ Click submit                                     │
│  │   ├─ _detect_2fa_page()                               │
│  │   │   ├─ Check URL patterns (/verification, /verify)  │
│  │   │   └─ Check form selectors (input[name='code'])    │
│  │   ├─ Si 2FA detecte :                                 │
│  │   │   ├─ GmailReader.get_latest_2fa_code()            │
│  │   │   │   ├─ IMAP SSL → gmail.com:993                 │
│  │   │   │   ├─ Poll INBOX (5s interval, 60s timeout)    │
│  │   │   │   ├─ Filtre sender contient "indy"            │
│  │   │   │   └─ Extract code regex \b(\d{4,8})\b         │
│  │   │   ├─ _inject_2fa_code(tab, code)                  │
│  │   │   └─ del code (securite)                          │
│  │   └─ _wait_for_dashboard() → polling selector         │
│  └─ close() → cleanup browser                           │
│                                                          │
│  Indy2FAAdapter (nodriver async — alternative)            │
│  ├─ auto_2fa_login(page, gmail, email, pwd)              │
│  │   ├─ _fill_login_form() (multi-selecteurs)            │
│  │   ├─ _submit_login_form() (texte FR/EN, fallback)     │
│  │   ├─ _detect_2fa_page() (URL + selecteurs + headings) │
│  │   ├─ _get_2fa_code_async() (run_in_executor)          │
│  │   ├─ _inject_and_verify() (code + bouton)             │
│  │   └─ _wait_for_dashboard() (URL + elements)           │
│  └─ Masquage securite (_mask_email, _mask_code)          │
│                                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                     GmailReader                          │
│  (IMAP SSL — extraction code 2FA)                        │
├─────────────────────────────────────────────────────────┤
│  connect() → IMAP4_SSL(imap.gmail.com, 993)              │
│  get_latest_2fa_code(timeout, poll, sender, label)       │
│  _check_inbox(sender_filter, label_name)                 │
│  _get_email_body(msg) → plaintext/HTML                   │
│  _extract_code(text) → regex 4-8 digits (prefer 6)      │
│  close() → IMAP logout                                   │
├─────────────────────────────────────────────────────────┤
│                    GmailAPIReader                         │
│  (OAuth2 API — alternative recommandee)                  │
│  connect() → service account credentials                 │
│  get_latest_2fa_code() → API search + extract            │
│  _search_and_extract_code() → Gmail API query            │
│  _get_email_body(msg_id) → base64 decode payload         │
│  close() → service = None                                │
└─────────────────────────────────────────────────────────┘
```

### Fichiers source

| Fichier | Role | Lignes |
|---------|------|--------|
| `src/adapters/indy_adapter.py` | Playwright sync : login, export CSV, parse | ~481 |
| `src/adapters/indy_auto_login.py` | nodriver async : login 2FA auto-inject | ~400 |
| `src/adapters/indy_2fa_adapter.py` | nodriver async : orchestration 2FA complete | ~585 |
| `src/adapters/gmail_reader.py` | Gmail IMAP + OAuth2 API : extraction code 2FA | ~480 |

## Tests Requis

### Tests existants

| Fichier test | Classe / Scope | Tests |
|---|---|---|
| `tests/test_indy_export.py` | `TestIndyExportJournalBook` — methode existe, retry, retour list | 4 |
| `tests/test_indy_export.py` | `TestIndyParseJournalCSV` — parsing, filtrage, dedup, validation | 12 |
| `tests/test_indy_export.py` | `TestIndyCSVParsing` — special chars, gros montants, negatifs | 3 |
| `tests/test_indy_export.py` | `TestIndyLoginAndSession` — close, idempotent | 2 |
| `tests/test_indy_export.py` | `TestIndyIntegration` — filtrage end-to-end | 2 |
| `tests/test_indy_auto_login.py` | `TestIndyAutoLoginInit` — validation credentials | 3 |
| `tests/test_indy_auto_login.py` | `TestIndyAutoLoginDetect2FA` — detection URL + selecteur | 3 |
| `tests/test_indy_auto_login.py` | `TestIndyAutoLoginInject2FA` — injection code + bouton | 3 |
| `tests/test_indy_auto_login.py` | `TestIndyAutoLoginFlow` — login sans/avec 2FA, retries | 6 |
| `tests/test_indy_auto_login.py` | `TestIndyAutoLoginGmailIntegration` — filtre sender, timeout | 2 |
| `tests/test_indy_auto_login.py` | `TestIndyAutoLoginSecurity` — pas de credentials dans logs | 3 |
| `tests/test_indy_auto_login.py` | `TestIndyAutoLoginCleanup` — close, context manager | 3 |
| `tests/test_indy_auto_login.py` | `TestIndyAutoLoginErrorHandling` — exceptions tous chemins | 7 |
| `tests/test_indy_auto_login.py` | `TestIndyAutoLoginLaunchBrowser` — launch, import error | 3 |
| `tests/test_indy_auto_login.py` | `TestIndyAutoLoginTabManagement` — tab recovery | 2 |
| `tests/test_indy_2fa_adapter.py` | `TestIndy2FAAdapterFillLoginForm` — email/password multi-selecteurs | 4 |
| `tests/test_indy_2fa_adapter.py` | `TestIndy2FAAdapterSubmitLoginForm` — texte FR, selecteur, Enter | 3 |
| `tests/test_indy_2fa_adapter.py` | `TestIndy2FAAdapterDetect2FAPage` — URL, selecteur, heading, timeout | 4 |
| `tests/test_indy_2fa_adapter.py` | `TestIndy2FAAdapterGet2FACodeAsync` — success, timeout, exception | 3 |
| `tests/test_indy_2fa_adapter.py` | `TestIndy2FAAdapterInjectAndVerify` — injection, bouton, echecs | 4 |
| `tests/test_indy_2fa_adapter.py` | `TestIndy2FAAdapterWaitForDashboard` — URL, balance, timeout | 3 |
| `tests/test_indy_2fa_adapter.py` | `TestIndy2FAAdapterAuto2FALogin` — flow complet, skip 2FA, gmail timeout | 3 |
| `tests/test_indy_2fa_adapter.py` | `TestIndy2FAAdapterMasking` — masquage email, code | 6 |
| `tests/test_gmail_reader.py` | IMAP : connect, poll, extract, parse body, close | ~20+ |
| `tests/test_gmail_api_reader.py` | OAuth2 : connect, search, extract, poll, close | ~20+ (majoritairement skip) |

### Tests manquants (gaps)

- [ ] CSV encoding non-UTF-8 (BOM, Latin-1)
- [ ] CSV separateur `;` (format FR)
- [ ] Montants format FR (`1.234,56`)
- [ ] Integration Playwright reelle (export end-to-end avec mock page)
- [ ] Timeout export CSV (download jamais complete)
- [ ] CSV avec colonnes supplementaires inattendues
- [ ] Dedup avec `indy_id` reel (pas hash composite)

## Implementation Status

| Fichier | Existe | Tests | Coverage estimee | CDC §ref |
|---------|--------|-------|------------------|----------|
| `src/adapters/indy_adapter.py` | Oui | `test_indy_export.py` | ~75% | §4.2 |
| `src/adapters/indy_auto_login.py` | Oui | `test_indy_auto_login.py` | ~85% | §4 (2FA) |
| `src/adapters/indy_2fa_adapter.py` | Oui | `test_indy_2fa_adapter.py` | ~80% | §4 (2FA) |
| `src/adapters/gmail_reader.py` | Oui | `test_gmail_reader.py` | ~70% | §4 (2FA) |
| `src/adapters/gmail_reader.py` (API) | Oui | `test_gmail_api_reader.py` | ~30% (skips) | §4 (2FA) |

## Golden Workflow

| Phase | Status | Evidence |
|-------|--------|----------|
| 0. PLAN | Done | CDC §4, TURNSTILE_DECISION_TREE.md, NODRIVER_2FA_QUICK_REF.md |
| 1. TDD RED | Done | Tests existent dans 5 fichiers, couvrent happy path + errors |
| 2. TDD GREEN | Done (partiel) | Adapters implementes, CSV parsing fonctionnel, login OK |
| 3. REVIEW | En cours | ruff + pyright a verifier sur les 4 fichiers adapter |
| 4. VERIFY | En cours | Coverage globale a mesurer, gaps CSV parsing identifies |
| 5. COMMIT | En cours | Code committe, pas de release formelle |
| 6. REFACTOR | A faire | Trois adapters login (IndyBrowserAdapter._login, IndyAutoLoginNodriver, Indy2FAAdapter) → consolider |

## Gaps identifies

1. **CSV parsing robuste manquant** : pas de gestion encoding (BOM, Latin-1), separateur variable (`;`), montants format FR (`1.234,56`). Le parser actuel suppose UTF-8, separateur `,`, montants format anglais.

2. **Pas de `transaction_id` / `indy_id` extrait du CSV** : la dedup utilise un hash composite `(date_valeur, montant, libelle)` au lieu d'un identifiant unique Indy. Risque de faux positifs si deux transactions legitimes ont les memes valeurs.

3. **Trois implementations login coexistent** : `IndyBrowserAdapter._login()` (Playwright sync), `IndyAutoLoginNodriver` (nodriver async), `Indy2FAAdapter` (nodriver async). A consolider en une seule chaine d'authentification.

4. **GmailAPIReader majoritairement non testee** : les tests `test_gmail_api_reader.py` sont presque tous en skip (credentials non disponibles en CI). Coverage reelle ~30%.

5. **Mapping colonnes Indy non verifie** : les noms de colonnes CSV (`date_valeur`, `montant`, `libelle`, `type`) sont supposes. Les noms reels du Journal Book Indy n'ont pas ete valides contre un export reel.

## Statut

**Implemented (70%)**

- Login Indy : OK (3 strategies implementees)
- 2FA auto-inject : OK (nodriver + Gmail IMAP)
- Export Journal Book CSV : OK (navigation + download)
- CSV parsing basique : OK (filtrage revenus, dedup, validation)
- CSV parsing robuste : **MANQUANT** (encoding, separateur, format FR)
- Integration onglet Transactions : a verifier
