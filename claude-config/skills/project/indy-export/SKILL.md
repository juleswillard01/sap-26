---
name: indy-export
description: >
  Export Indy banking via Playwright. TRIGGER : indy_adapter.py,
  indy_auto_login.py, gmail_reader.py, indy_2fa_adapter.py, Turnstile, 2FA OTP.
---

# Indy Export

## Objectif
Exporter le Journal Book CSV depuis Indy (app.indy.fr) via Playwright headless.

## Perimetre
- Chaine auth : Turnstile challenge → nodriver bypass → 2FA OTP → Gmail reader
- Navigation : Documents > Comptabilite > Export CSV
- Parser CSV : transaction_id, date_valeur, montant, libelle, type
- Dedup par `indy_id` + `montant` + `date_valeur`
- Maj onglet Transactions dans Sheets (source="indy")

## Regles Metier
- Indy = LECTURE SEULE — export Journal CSV uniquement
- Cron : `sap reconcile` quotidien
- Retry 3x backoff exponentiel
- Transactions immutables apres import (sauf `facture_id`, `statut_lettrage`)
- Ordre auth strict : Turnstile → login → 2FA → session

## Code Map
| Fichier | Role |
|---------|------|
| `src/adapters/indy_adapter.py` | Playwright scraper Indy (nav + CSV export) |
| `src/adapters/indy_auto_login.py` | Login auto avec bypass Turnstile (nodriver) |
| `src/adapters/indy_2fa_adapter.py` | Gestion 2FA OTP Indy |
| `src/adapters/gmail_reader.py` | Lecture OTP 2FA depuis Gmail IMAP |
| `src/models/transaction.py` | Modele Transaction Pydantic v2 |

## Tests
```bash
uv run pytest tests/ -k indy -v
```

## Gotchas
- Turnstile = anti-bot Cloudflare — nodriver le bypass, fragile
- 2FA OTP arrive par email — gmail_reader lit via IMAP avec delai
- CSV encoding peut varier (UTF-8 BOM possible)
- JAMAIS stocker credentials en dur — `.env` obligatoire
- Screenshots erreur dans `io/cache/` (RGPD-safe)
