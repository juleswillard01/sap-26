---
name: ais-scraping
description: >
  Scraping AIS (avance-immediate.fr) via Playwright. TRIGGER : ais_adapter.py,
  scraping AIS, Playwright AIS, sync factures, statuts URSSAF, polling demandes.
---

# AIS Scraping

## Objectif
Lire les statuts factures et clients depuis AIS via Playwright headless. LECTURE SEULE.

## Perimetre
- Login email/password sur app.avance-immediate.fr
- Scrape page "Mes demandes" : id, montant, statut, dates
- Scrape page "Mes clients" : client_id, nom, statut_urssaf
- Dedup par `urssaf_demande_id`
- Maj onglets Factures + Clients dans Sheets
- Detection EN_ATTENTE > 36h → logger alerte

## Regles Metier
- SAP-Facture NE CREE PAS de factures — AIS le fait
- SAP-Facture NE SOUMET PAS a URSSAF — AIS le fait
- Transitions detectees, pas declenchees (CREE, EN_ATTENTE, VALIDE, PAYE)
- CREE → EN_ATTENTE est immediat (decision D3)
- Cron : `sap sync` toutes les 4h
- Retry 3x backoff exponentiel
- Screenshots erreur dans `io/cache/` (RGPD-safe)
- Voir `.claude/rules/state-machine.md` pour les transitions

## Code Map
| Fichier | Role |
|---------|------|
| `src/adapters/ais_adapter.py` | Playwright scraper AIS (login + parse demandes) |
| `src/services/payment_tracker.py` | Detection changements d'etat factures |
| `src/models/invoice.py` | Modele Invoice + InvoiceStatus enum |
| `src/config.py` | Credentials AIS (`.env`) |

## Tests
```bash
uv run pytest tests/ -k "ais or avance" -v
```

## Gotchas
- LECTURE SEULE absolue — jamais ecrire dans AIS
- JAMAIS logger passwords ou tokens
- Selecteurs CSS fragiles — AIS peut changer son UI sans prevenir
- Session timeout : re-login si cookie expire
- Respecter intervalle polling 4h (pas de spam)
- Screenshots `io/cache/` doivent etre RGPD-safe (pas de donnees nominatives)
