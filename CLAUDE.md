# SAP-Facture — Orchestrateur

## Source de Vérité
- `docs/schemas/SCHEMAS.html` — Schémas fonctionnels (INTOUCHABLE)
- `docs/CDC.md` — Cahier des charges

## Qu'est-ce que SAP-Facture ?
Orchestrateur qui synchronise AIS (facturation URSSAF), Indy (banque), Google Sheets (backend).
**NE CRÉE PAS de factures. NE SOUMET PAS à URSSAF. SYNCHRONISE, RAPPROCHE et ALERTE.**

## Décisions Verrouillées
| ID | Décision | Justification |
|----|----------|---------------|
| D1 | AIS gère la facturation — SAP lit via Playwright (LECTURE) | Offre tout-en-un, pas d'API directe |
| D2 | Google Sheets 8 onglets (gspread + Polars) | Backend flexible, éditabilité directe |
| D3 | CREE → EN_ATTENTE immédiat | Simplification |
| D4 | FastAPI SSR + Jinja2 + Tailwind | Stack léger, pas SPA |
| D5 | Playwright Indy export Journal CSV | Pas d'API bancaire |
| D6 | Lettrage semi-auto (système propose, Jules confirme) | MVP pragmatique |
| D7 | Pas de génération PDF — AIS le fait | URSSAF demande PDF signé |
| D8 | Python 3.12 + uv | Vitesse, déterminisme |
| D9 | ruff strict + pyright strict + pytest ≥80% | Qualité non-négociable |

## Stack
Python 3.12, uv, FastAPI+Jinja2+Tailwind, Click+Rich CLI, gspread v6+Polars, Playwright headless, SMTP Gmail, pytest

## Architecture
```
src/
├── adapters/    # AIS, Indy, Sheets, Email (Playwright LECTURE)
├── services/    # PaymentTracker, BankReconciliation, Notifications, NOVA, Cotisations
├── models/      # Pydantic v2 (Client, Invoice, Transaction, Sheets)
├── templates/   # Jinja2 emails
├── config.py    # pydantic-settings
├── app.py       # FastAPI
└── cli.py       # Click CLI
```

## Setup
```bash
uv sync
uv run pytest --cov=src --cov-fail-under=80
uv run ruff check --fix src/ tests/ && uv run ruff format src/ tests/
uv run pyright --strict src/
```

## INTERDIT
- Créer des factures (AIS le fait)
- Soumettre à URSSAF (AIS le fait)
- Générer des PDF factures (AIS le fait)
- Inscrire des clients URSSAF (AIS le fait)
- Modifier SCHEMAS.html
- print() dans src/ (logging obligatoire)
- Stocker des secrets dans le code (.env obligatoire)
- Écrire du code sans tests
- Utiliser pip/poetry (uv obligatoire)
- os.path (pathlib obligatoire)
