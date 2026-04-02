---
name: sheets-adapter
description: >
  Google Sheets backend adapter. TRIGGER : sheets_adapter.py, sheets_schema.py,
  write_queue.py, Patito, 8 onglets, rate limiting, cache TTL, batch ops.
---

# Sheets Adapter

## Objectif
Adapter gspread + Polars + Patito pour lire/ecrire les 8 onglets Google Sheets.

## Perimetre
- Batch reads (`get_all_records()`), batch writes (`append_rows()`, `update()`)
- Rate limiting 60 req/min (TokenBucketRateLimiter)
- Cache memoire TTL 30s (cachetools.TTLCache)
- Circuit breaker (pybreaker, open apres 5 echecs consecutifs)
- Write queue serialisee (threading.Queue)
- Validation schemas Patito sur DataFrames Polars

## Regles Metier
- 3 onglets data brute (Clients, Factures, Transactions) : R/W
- 5 onglets calcules (Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal IR) : READ ONLY
- Jamais `update_cell()` en boucle — batch obligatoire
- Dedup transactions par `indy_id` a l'import
- `montant_total` = formule Sheets (`quantite * montant_unitaire`)
- Voir `.claude/rules/sheets-schema.md` pour colonnes et contraintes

## Code Map
| Fichier | Role |
|---------|------|
| `src/adapters/sheets_adapter.py` | Adapter principal gspread + cache + rate limit |
| `src/adapters/sheets_schema.py` | Schemas Patito par onglet |
| `src/adapters/write_queue.py` | Queue serialisee pour ecritures thread-safe |
| `src/adapters/rate_limiter.py` | TokenBucketRateLimiter (60 req/min) |
| `src/models/sheets.py` | Modeles Pydantic v2 pour config Sheets |

## Tests
```bash
uv run pytest tests/ -k sheets -v
```

## Gotchas
- JAMAIS `update_cell()` en boucle — batch uniquement
- JAMAIS ecrire dans les onglets calcules (4-8)
- Rate limit Google = 60 req/min/user — depasser = 429
- Cache invalidation manuelle si write puis read immediat
- Write queue doit etre drainee avant shutdown
- `SCHEMAS.html` est INTOUCHABLE
