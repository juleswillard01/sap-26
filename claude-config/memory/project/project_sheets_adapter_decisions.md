---
name: SheetsAdapter CRUD decisions
description: Decisions QCM pour l'implementation du SheetsAdapter CRUD [CDC §1.2] — Polars, cache, circuit breaker, queue worker
type: project
---

## Decisions SheetsAdapter CRUD — 2026-03-20

**Source de donnees** : avance-immediate.fr (clients+factures) et Indy (releves bancaires), scrapes via MCP Playwright headless. SheetsAdapter = couche data access pure vers Google Sheets.

**Auth** : Service Account JSON `./credentials/` (dev) + Docker secret (prod). Scopes: spreadsheets + drive.

**Connexion** : Connection pool avec auto-reconnect. Fail fast si spreadsheet_id vide (ValueError).

**Onglets** : 8 onglets tous accessibles. Nommage francais ("Clients", "Factures"...). Reference via pydantic Settings (configurable). Formules Google Sheets natives pour les 5 onglets calcules, injectees via `sap init`.

**Polars[all]>=1.0** : Partout — lecture, ecriture, cache. SheetsAdapter retourne des `pl.DataFrame`. CRUD brut dans l'adapter, filtrage Polars dans les Services.

**CRUD** :
- get_all_*() -> pl.DataFrame (8 onglets)
- get_by_id() : un par onglet (client_id, facture_id, transaction_id)
- add_client(), add_invoice() : append row
- add_transactions() : batch append + dedup indy_id
- update_invoice(facture_id, fields: dict) : methode generique
- update_transaction(txn_id, fields: dict) : tout sauf IDs
- Jamais de delete (soft delete via statut)

**Cache** : cachetools.TTLCache, cle = hash(method+params), invalidation totale sur write + TTL 30s.

**Rate limit** : best strategy (token bucket ou sliding window), 60 req/min.

**Concurrence** : threading.Queue + worker thread dedie pour serialiser les ecritures.

**Circuit breaker** : pybreaker (librairie). Retry 3x backoff (tenacity).

**Erreurs** : Hierarchie custom (SheetsError base) + exceptions standard Python. Raise ValidationError sur ligne corrompue. SheetsError generique si sheet introuvable. Timeout + circuit breaker.

**Types** : float standard pour montants. TRUE/FALSE natifs pour booleens. Dates configurables (ISO par defaut).

**Tests** : Fixture spreadsheet test reel + Mock gspread + Fake in-memory. JSON complets (3 clients, 5 factures, 10 txn) + factory_boy. DI constructeur + FastAPI Depends.

**Deps a ajouter** : polars[all]>=1.0, cachetools>=5.3, pybreaker>=1.2, tenacity>=8.3

**Volume** : ~20 clients, ~200 factures, ~400 transactions / an

**`sap init`** : commande CLI qui cree les 8 onglets + headers + injecte les formules Sheets.

**Why:** Google Sheets = backend data du projet. SheetsAdapter est la fondation sur laquelle tous les Services dependent.

**How to apply:** Implementer via golden workflow (CDC -> Plan -> TDD -> Review -> Verify -> Commit -> Refactor). Ne pas vibecoder — chaque etape doit etre validee.
