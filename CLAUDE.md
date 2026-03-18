# SAP-Facture — Agent Teams Context

## Source de Vérité Absolue
Le fichier `docs/schemas/SCHEMAS.html` contient 8 diagrammes Mermaid qui définissent l'architecture complète :

1. Parcours Utilisateur Quotidien
2. Flux de Facturation End-to-End
3. Séquence API URSSAF
4. Architecture Système
5. Modèle de Données (8 onglets Google Sheets)
6. Rapprochement Bancaire & Lettrage
7. Machine à États Facture (10 états, 17 transitions)
8. Scope MVP vs Phases Futures

**INTOUCHABLE** — toute architecture, code, ou documentation doit s'aligner dessus.

## Décisions Verrouillées (2026-03-18)

| Décision | Détail |
|----------|--------|
| **D1: Polling URSSAF** | Toutes les 4 heures |
| **D2: Email SMTP** | SAP-Facture (via `aiosmtplib`) |
| **D3: États Facture** | CREE → EN_ATTENTE immédiat |
| **D4: CLI FIRST** | Click CLI est l'interface principale, pas le web en MVP |
| **D5: Indy + Playwright** | Scraping transactions bancaires **PAS Swan API** |
| **D6: Lettrage Manuel** | Lettrage manuel en MVP, pas d'auto-lettrage |
| **D7: PDF Prioritaire** | PDF factures prioritaires, stockage Google Drive |

## Stack Technique
- **Python 3.11+**, FastAPI, Click CLI
- **Pydantic v2** — validation stricte
- **Google Sheets API v4** (gspread) — backend database
- **WeasyPrint** — génération PDF
- **Playwright** — Indy banking scraping
- **aiosmtplib** — notifications email
- **pytest, ruff, mypy --strict** — qualité code

Dev: `pip install -e ".[dev]"` | Tests: `pytest --cov=app --cov-fail-under=80`

Google Sheets: service account JSON base64 in `.env` (GOOGLE_SERVICE_ACCOUNT_B64). Voir `.env.example` pour toutes les variables.

## Architecture (4 couches)

```
┌─────────────────────────────────────┐
│  Présentation: CLI (Click) + Web    │
├─────────────────────────────────────┤
│  Métier: Services (Facture, Email)  │
├─────────────────────────────────────┤
│  Accès: SheetsAdapter               │
├─────────────────────────────────────┤
│  Intégrations: URSSAF, Indy, PDF    │
└─────────────────────────────────────┘
```

## Structure Projet

```
app/
├── main.py           # FastAPI factory
├── config.py         # Pydantic Settings (.env)
├── adapters/         # SheetsAdapter, URSSAFClient, IndyBrowserAdapter
├── models/           # Pydantic v2 models
├── services/         # Business logic
└── routers/          # FastAPI endpoints

tests/
├── unit/             # No I/O
├── conftest.py       # Shared fixtures
```

## Règles de Code — STRICTES

### Type Safety
- Type hints sur **TOUTES** les signatures (params + return)
- `from __future__ import annotations` en haut de chaque fichier
- Pydantic v2 `BaseModel` pour toutes structures de données
- `mypy --strict` doit passer sans erreurs

### Qualité
- `ruff check --fix && ruff format` avant tout commit
- Max 200-400 lignes par fichier, 50 lignes par fonction
- Max 3 niveaux d'indentation
- `snake_case` fonctions/variables, `PascalCase` classes

### Patterns Obligatoires
- Repository pattern pour data access
- Services layer pour la logique métier
- Dependency injection dans constructeurs
- logging (jamais `print()`)
- pathlib (jamais `os.path`)

### Testing
- **80% minimum coverage** (`pytest --cov-fail-under=80`)
- Tests requirement-driven, pas implementation-driven
- Couvrir: happy path, edge cases, error handling, state transitions
- Mock ALL external APIs (URSSAF, Google Sheets, Indy)
- Nommer tests: `test_<what>_<condition>_<expected>`

## Livrables BMAD

Tous les livrables sont en **HTML dark-theme** (Mermaid inclus) dans `docs/bmad/deliverables/`.

Templates de base dans `bmad/templates/` :
- `architecture-template.html` — architecture diagrams
- `prd-template.html` — product requirements
- `review-report-template.html` — code review results
- `sprint-board-template.html` — sprint status
- `test-plan-template.html` — test coverage & results

**Injection helper** : `bmad/templates/inject.py` remplace `{{PLACEHOLDER}}` markers avec valeurs JSON.

## INTERDIT

- Toute référence à Swan ou Swan API
- Lettrage automatique en MVP
- Web dashboard en MVP (CLI first)
- `print()` au lieu de `logging`
- `os.path` au lieu de `pathlib`
- Secrets en dur dans le code
- Cross-package imports relatifs
- Fonctions > 50 lignes
- Fichiers > 400 lignes

## Contacts & Escalade

- **Product Owner** : Jules Willard (project lead)
- **Architecture Decision** : voir `bmad/ARCHITECTURE.md`
- **Agent Manifest** : `bmad/AGENT-MANIFEST.md`
- **Workflows** : `bmad/workflows/`
