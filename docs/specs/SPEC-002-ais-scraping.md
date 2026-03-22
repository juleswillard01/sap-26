# SPEC-002 — AIS Scraping

## Objectif

Synchroniser en **LECTURE SEULE** les statuts de factures et les informations clients depuis AIS (app.avance-immediate.fr) vers Google Sheets. SAP-Facture ne crée pas de factures, n'inscrit pas de clients, ne soumet rien à URSSAF. Il détecte les changements d'état et alerte Jules.

Source : CDC §3 — Sync AIS (Playwright / REST)

## Périmètre

### Ce que SAP-Facture fait

- Scrape page "Mes demandes" via REST API (httpx) ou Playwright headless
- Parse pour chaque demande : `_id`, `montant`, `statut`, `date_soumission`, `date_validation`, `date_paiement`, `customerId`
- Parse page Clients : `_id`, `nom`, `prenom`, `email`, `statut_urssaf`
- Dedup par `_id` (clé primaire AIS, correspond a `urssaf_demande_id` cote SAP)
- Maj onglet Factures (statut, dates) et onglet Clients (infos URSSAF)
- Detection demandes EN_ATTENTE > 36h et log alerte (relance Jules)
- Retry 3x backoff exponentiel sur erreurs reseau
- Screenshots erreur dans `io/cache/` (RGPD-safe, sans donnees sensibles)
- Cron `sap sync` toutes les 4h

### Ce que SAP-Facture NE fait PAS

- **PAS de creation de facture** — Jules cree la facture dans AIS manuellement
- **PAS d'inscription client** — Jules inscrit le client dans AIS manuellement
- **PAS de soumission URSSAF** — AIS soumet a URSSAF directement
- **PAS de modification de demande** — AIS et URSSAF gerent les modifications
- **PAS de generation PDF** — AIS genere les PDF signes pour URSSAF

Les methodes `register_client()` et `submit_invoice()` levent `NotImplementedError("INTERDIT")` pour garantir ce contrat.

## Criteres d'Acceptance

- [x] Login email + password via REST `/professional` endpoint -> token JWT
- [x] Retry 3x backoff exponentiel (2^attempt sec, cap 30s) sur erreurs HTTP
- [x] ValueError immediate si credentials invalides (pas de retry sur erreur client)
- [x] Lecture collection `customer` via `/mongo` -> liste clients dedupliquee par `_id`
- [x] Lecture collection `bill` via `/mongo` -> liste factures dedupliquee par `_id`
- [x] Mapping champs AIS -> format SAP-Facture (firstName->prenom, lastName->nom, status->statut_urssaf, etc.)
- [x] Filtre factures par statut (`get_invoices(status="EN_ATTENTE")`)
- [x] Lookup statut par `demande_id` (`get_invoice_status()`)
- [x] Detection EN_ATTENTE > 36h via `get_pending_reminders(hours_threshold=36)`
- [x] Context manager (`with AISAPIAdapter(settings) as adapter:`)
- [x] `close()` efface le token et ferme la session httpx
- [x] `register_client()` leve NotImplementedError — INTERDIT
- [x] `submit_invoice()` leve NotImplementedError — INTERDIT
- [x] Backward compat : alias `AISAdapter = AISAPIAdapter`
- [ ] Scrape Playwright headless comme fallback si REST API indisponible
- [ ] Screenshots erreur dans `io/cache/` (RGPD-safe)
- [ ] Cron `sap sync` toutes les 4h (integration CLI)
- [ ] Sync statuts AIS -> Sheets via `sync_statuses_from_ais()` (service PaymentTracker)
- [ ] Selectors AIS mappes et valides (login form, table demandes, table clients)

## Decisions Verrouillees

| ID | Decision | Justification |
|----|----------|---------------|
| D1 | AIS gere la facturation — SAP lit via REST/Playwright (LECTURE SEULE) | Pas d'API publique directe, API interne decouverte via NetworkLogger |
| D2 | REST API (httpx) comme canal principal, Playwright en fallback | REST plus rapide, plus stable, moins fragile que le scraping DOM |
| D3 | Dedup par `_id` (cle MongoDB AIS) | Cle primaire naturelle, evite doublons lors imports multiples |
| D4 | Retry reseau uniquement, pas de retry sur erreur credentials | Echec auth = config incorrecte, pas un probleme transitoire |
| D5 | Token dans header Authorization en JSON (pas Bearer standard) | Protocole AIS specifique (AWS API Gateway custom) |
| D7 | register_client() et submit_invoice() levent NotImplementedError | Garde-fou code : empeche toute ecriture accidentelle dans AIS |

## Architecture

### Classes

```
AISAPIAdapter (src/adapters/ais_adapter.py)
├── connect()                    -> obtient token via POST /professional
├── get_profile()                -> GET profil utilisateur (SIRET, NOVA, abonnement)
├── get_clients()                -> READ collection 'customer' via POST /mongo
├── get_invoices(status?)        -> READ collection 'bill' via POST /mongo + filtre
├── get_invoice_statuses()       -> READ collection 'bill' (toutes)
├── get_invoice_status(id)       -> lookup statut par demande_id
├── get_pending_reminders(36h)   -> filtre EN_ATTENTE > seuil
├── register_client()            -> INTERDIT (NotImplementedError)
├── submit_invoice()             -> INTERDIT (NotImplementedError)
├── close()                      -> ferme session httpx + efface token
└── __enter__/__exit__           -> context manager
```

### API AIS (decouverte via NetworkLogger)

| Endpoint | Methode | Usage |
|----------|---------|-------|
| `/professional` | POST | Auth : envoie email+password en JSON dans header Authorization, recoit token |
| `/mongo` | POST | Read : envoie token+collection dans header Authorization, recoit items[] |

- Base URL : `https://3u7151jll8.execute-api.eu-west-3.amazonaws.com` (AWS API Gateway)
- Backend : Lambda + MongoDB
- Auth header : JSON stringifie (pas Bearer standard)

### Integration aval

```
AISAPIAdapter.get_invoice_statuses()
  -> sync_statuses_from_ais() (src/services/payment_tracker.py)
    -> compare ais_statuses vs sheets_invoices
      -> detecte changements de statut
        -> ecrit dans Google Sheets onglet Factures
```

### Configuration (pydantic-settings)

| Variable | Default | Description |
|----------|---------|-------------|
| `ais_email` | `""` | Email de connexion AIS |
| `ais_password` | `""` | Mot de passe AIS |
| `ais_api_base_url` | `https://3u7151jll8.execute-api.eu-west-3.amazonaws.com` | Base URL API |
| `ais_timeout_sec` | `30` | Timeout httpx en secondes |
| `ais_max_retries` | `3` | Nombre max de tentatives |

## Tests Requis

### test_ais_api.py — 20 tests (REST via respx mock)

| Classe | Tests | Couverture |
|--------|-------|------------|
| TestLogin | 4 | connect, login failure, retry on HTTP error, raise after 3 retries |
| TestGetClients | 3 | returns list, empty list, deduplicates by _id |
| TestGetInvoices | 4 | returns list, filter by status, single status lookup, not found raises |
| TestPendingReminders | 3 | finds old waiting, ignores recent, ignores non-waiting status |
| TestSessionManagement | 2 | close clears token, context manager pattern |
| TestBackwardCompat | 2 | AISAdapter alias exists, AISAdapter works |
| TestForbidden | 2 | register_client raises, submit_invoice raises |

### test_adapters_playwright.py — 19 tests AIS (via unittest.mock)

| Classe | Tests | Couverture |
|--------|-------|------------|
| TestAISAPIAdapterInit | 2 | stores settings, sets timeout |
| TestAISAPIAdapterConnect | 2 | calls _get_token_with_retry, logs success |
| TestAISAPIAdapterGetClients | 2 | returns mapped list, deduplicates by id |
| TestAISAPIAdapterGetInvoices | 2 | returns list, filters by status |
| TestAISAPIAdapterGetInvoiceStatus | 2 | returns status string, raises if not found |
| TestAISAPIAdapterSubmitInvoice | 1 | raises NotImplementedError |
| TestAISAPIAdapterRegisterClient | 1 | raises NotImplementedError |
| TestAISAPIAdapterClose | 3 | closes httpx, nullifies token, idempotent |

**Total : 39 tests AIS** (20 respx + 19 mock)

### Tests manquants (gaps)

- [ ] Test Playwright fallback (scrape DOM quand REST down)
- [ ] Test `get_profile()` (lecture profil utilisateur)
- [ ] Test `_read_collection()` directement (erreur collection read)
- [ ] Test `_read_collection_single()` erreur
- [ ] Test `_make_auth_header()` extra kwargs
- [ ] Test integration `sync_statuses_from_ais()` end-to-end avec mock AIS
- [ ] Test screenshot erreur RGPD-safe

## Implementation Status

| Fichier | Lignes | Tests | Status | CDC ref |
|---------|--------|-------|--------|---------|
| `src/adapters/ais_adapter.py` | 427 | 39 | REST complet, Playwright absent | CDC §3.1, §3.3 |
| `src/services/payment_tracker.py` | ~270 | - | `sync_statuses_from_ais()` present | CDC §3.3 |
| `src/config.py` | 75 | - | Settings AIS presentes | CDC §3 |
| `src/adapters/network_logger.py` | - | - | Outil de dev (decouverte API) | - |
| `tests/test_ais_api.py` | 603 | 20 | Complet (respx) | - |
| `tests/test_adapters_playwright.py` | 799 | 19 AIS | Complet (mock) | - |

## Golden Workflow

| Phase | Status | Evidence |
|-------|--------|----------|
| 0. PLAN | Done | CDC §3 documente le flux complet |
| 1. TDD RED | Done | 39 tests ecrits et passes |
| 2. TDD GREEN | Done | AISAPIAdapter REST implementee (427 lignes) |
| 3. REVIEW | Done | ruff + pyright strict passe |
| 4. VERIFY | Partial | 39 tests passent, coverage a verifier |
| 5. COMMIT | Done | Code committe |
| 6. REFACTOR | Pending | Playwright fallback a ajouter |

## Gaps identifies

### P1 — Playwright fallback absent
L'implementation actuelle est 100% REST (httpx). Le CDC §3.3 mentionne Playwright headless comme methode d'acces. Si AIS change son API interne, le fallback Playwright n'existe pas. Les selectors AIS (formulaire login, table demandes, table clients) ne sont pas mappes.

### P2 — Selectors AIS non mappes
Aucun selector CSS/XPath n'est defini pour le scraping DOM AIS. Le repertoire `docs/io/research/ais/` n'existe pas. Les selectors devraient etre documentes via NetworkLogger pour le fallback Playwright.

### P3 — Cron non integre
Le CDC specifie `sap sync` toutes les 4h. La config `polling_interval_hours=4` existe dans Settings mais l'integration CLI cron n'est pas implementee.

### P4 — Screenshots erreur
Le CDC specifie screenshots RGPD-safe dans `io/cache/`. Implemente pour Indy (`_screenshot_on_error`), mais pas pour AIS REST (pas de navigateur). A implementer si Playwright fallback est ajoute.

## Statut

**Implemented (60%)**

- REST API : 100% (login, clients, factures, relances, dedup, retry, forbidden ops)
- Playwright fallback : 0% (pas de selectors, pas de code scraping)
- Integration CLI/cron : 0%
- Screenshots erreur AIS : 0% (present pour Indy uniquement)
