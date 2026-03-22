# Module Map — AIS Scraping

## Source

| Fichier | Lignes | Classe | Role |
|---------|--------|--------|------|
| `src/adapters/ais_adapter.py` | 426 | `AISAPIAdapter` | Client REST API AIS (httpx) — LECTURE SEULE |

### Methodes (18)

| Methode | Lignes | Visibilite | Description |
|---------|--------|------------|-------------|
| `__init__(settings)` | L38-41 | public | Stocke settings, cree client httpx avec timeout |
| `connect()` | L43-50 | public | Obtient token via `_get_token_with_retry()` |
| `_get_token_with_retry()` | L52-111 | private | POST `/professional` — retry 3x backoff exponentiel (reseau), ValueError immediate si credentials invalides |
| `get_profile()` | L113-128 | public | Lit profil utilisateur (SIRET, NOVA, abonnement) via `_read_collection_single("professional")` |
| `get_clients()` | L130-167 | public | Lit collection `customer` via `/mongo`, mappe champs AIS vers SAP, dedup par `_id` |
| `get_invoices(status?)` | L169-181 | public | Delegue a `get_invoice_statuses()` + filtre optionnel par statut |
| `get_invoice_statuses()` | L183-220 | public | Lit collection `bill` via `/mongo`, mappe champs, dedup par `_id` |
| `get_invoice_status(demande_id)` | L222-238 | public | Lookup statut par `demande_id`, leve `ValueError` si non trouve |
| `get_invoice_statuses_by_status(status)` | L240-242 | public | Alias pour `get_invoices(status)` |
| `get_pending_reminders(hours_threshold=36)` | L244-291 | public | Filtre EN_ATTENTE > seuil heures, ajoute `hours_waiting` |
| `register_client(client_data)` | L293-295 | public | INTERDIT — leve `NotImplementedError` |
| `submit_invoice(client_id, invoice_data)` | L297-299 | public | INTERDIT — leve `NotImplementedError` |
| `close()` | L301-305 | public | Ferme client httpx, efface token |
| `__enter__()` | L307-310 | public | Context manager — appelle `connect()` |
| `__exit__(...)` | L312-314 | public | Context manager — appelle `close()` |
| `_read_collection(collection)` | L316-362 | private | POST `/mongo` avec token+collection, retourne `items[]` |
| `_read_collection_single(collection, request_type)` | L364-407 | private | POST `/{collection}` avec token, retourne objet unique |
| `_make_auth_header(**extra)` | L409-422 | private | Construit header Authorization en JSON stringifie |

Alias backward compat : `AISAdapter = AISAPIAdapter` (L426)

## Tests

| Fichier | Lignes | Tests AIS | Strategie mock |
|---------|--------|-----------|----------------|
| `tests/test_ais_api.py` | 602 | 20 | `respx` (mock httpx transport) |
| `tests/test_adapters_playwright.py` | 798 | 15 | `unittest.mock.patch` (mock interne) |

**Total : 35 tests AIS**

### test_ais_api.py — 20 tests (respx, integration-style)

| Classe | Tests | Methodes couvertes |
|--------|-------|--------------------|
| `TestLogin` | 4 | `connect`, `_get_token_with_retry` (success, failure, retry, exhaust) |
| `TestGetClients` | 3 | `get_clients` (list, empty, dedup) |
| `TestGetInvoices` | 4 | `get_invoice_statuses`, `get_invoices(status=)`, `get_invoice_status`, not found |
| `TestPendingReminders` | 3 | `get_pending_reminders` (old, recent, non-waiting) |
| `TestSessionManagement` | 2 | `close`, `__enter__/__exit__` |
| `TestBackwardCompat` | 2 | alias `AISAdapter` |
| `TestForbidden` | 2 | `register_client`, `submit_invoice` |

### test_adapters_playwright.py — 15 tests AIS (unittest.mock, unit-style)

| Classe | Tests | Methodes couvertes |
|--------|-------|--------------------|
| `TestAISAPIAdapterInit` | 2 | `__init__` (settings, timeout) |
| `TestAISAPIAdapterConnect` | 2 | `connect` (token, logging) |
| `TestAISAPIAdapterGetClients` | 2 | `get_clients` (mapped list, dedup) |
| `TestAISAPIAdapterGetInvoices` | 2 | `get_invoices` (list, filter) |
| `TestAISAPIAdapterGetInvoiceStatus` | 2 | `get_invoice_status` (found, not found) |
| `TestAISAPIAdapterSubmitInvoice` | 1 | `submit_invoice` (forbidden) |
| `TestAISAPIAdapterRegisterClient` | 1 | `register_client` (forbidden) |
| `TestAISAPIAdapterClose` | 3 | `close` (httpx, token, idempotent) |

## Documentation

| Fichier | Role |
|---------|------|
| `docs/specs/SPEC-002-ais-scraping.md` | Spec complete (criteres d'acceptance, architecture, gaps) |
| `.claude/skills/ais-scraping/SKILL.md` | Skill Claude (trigger, regles metier, gotchas) |

## Couverture code vs tests

| Methode | test_ais_api | test_adapters_pw | Couvert |
|---------|:------------:|:----------------:|:-------:|
| `__init__` | - | 2 | oui |
| `connect` | 4 | 2 | oui |
| `_get_token_with_retry` | 4 (indirect) | - | oui |
| `get_profile` | - | - | **NON** |
| `get_clients` | 3 | 2 | oui |
| `get_invoices` | 1 | 2 | oui |
| `get_invoice_statuses` | 1 | - | oui |
| `get_invoice_status` | 2 | 2 | oui |
| `get_invoice_statuses_by_status` | - | - | **NON** |
| `get_pending_reminders` | 3 | - | oui |
| `register_client` | 1 | 1 | oui |
| `submit_invoice` | 1 | 1 | oui |
| `close` | 1 | 3 | oui |
| `__enter__/__exit__` | 1 | - | oui |
| `_read_collection` | 7 (indirect) | - | oui (indirect) |
| `_read_collection_single` | - | - | **NON** |
| `_make_auth_header` | - | - | **NON** |

## Gaps

### Tests manquants (P2)

| Methode | Gap |
|---------|-----|
| `get_profile()` | Aucun test — ni direct ni indirect |
| `get_invoice_statuses_by_status()` | Aucun test (alias trivial, risque faible) |
| `_read_collection_single()` | Teste indirectement via `get_profile` mais `get_profile` lui-meme n'est pas teste |
| `_make_auth_header()` | Aucun test direct (utilise nulle part dans le code actuel — dead code) |
| `_read_collection()` erreur path | Cas d'erreur `boolean: False` non teste directement |

### Fonctionnalites absentes (P1)

| Feature | Spec ref | Status |
|---------|----------|--------|
| Playwright fallback (scraping DOM si REST down) | SPEC-002 CA, CDC §3.3 | 0% — pas de code, pas de selectors |
| Cron `sap sync` toutes les 4h | SPEC-002 CA, SKILL.md | 0% — config `polling_interval_hours` existe, integration CLI absente |
| Screenshots erreur AIS RGPD-safe | SPEC-002 CA | 0% — present pour Indy, absent pour AIS |
| `sync_statuses_from_ais()` integration end-to-end | SPEC-002 architecture aval | Non teste |

### Dead code

| Element | Raison |
|---------|--------|
| `_make_auth_header(**extra)` | Defini L409-422 mais jamais appele — `_read_collection` et `_read_collection_single` construisent le header inline |

## Notes

- L'implementation est 100% REST (httpx) via l'API interne AIS (AWS API Gateway + Lambda + MongoDB). Aucun scraping DOM.
- Le protocole d'auth est non-standard : le header `Authorization` contient du JSON stringifie (pas Bearer).
- La dedup par `_id` (cle MongoDB) est coherente entre `get_clients()` et `get_invoice_statuses()`.
- `_get_token_with_retry` distingue erreur reseau (retry) vs erreur credentials (fail immediat) — conforme CDC.
- Les 2 fichiers de tests utilisent des strategies de mock differentes : `respx` (mock transport httpx, plus realiste) vs `unittest.mock.patch` (mock interne, plus isole). Pas de duplication inutile car les angles de test sont complementaires.
