# SAP-Facture — Orchestrateur

## Source de Vérité
- `docs/SCHEMAS.html` — Schémas fonctionnels (INTOUCHABLE)
- `docs/CDC.md` — Cahier des charges

## Qu'est-ce que SAP-Facture ?
SAP-Facture est un **orchestrateur** qui synchronise :
- **AIS** (app.avance-immediate.fr) → facturation URSSAF + avance immédiate
- **Indy** (app.indy.fr) → comptabilité + banque
- **Google Sheets** → backend data + calculs

Et qui **comble les gaps** : rapprochement bancaire, alertes, reporting NOVA.

**SAP-Facture ne crée PAS les factures. AIS le fait.**
**SAP-Facture ne soumet PAS à URSSAF. AIS le fait.**
**SAP-Facture SYNCHRONISE, RAPPROCHE et ALERTE.**

## Décisions Verrouillées
| ID | Décision | Justification |
|----|----------|---------------|
| D1 | AIS gère la facturation URSSAF — SAP-Facture lit AIS en Playwright (LECTURE seule) | Offre tout-en-un fiable, Playwright = pas d'API directe nécessaire |
| D2 | Google Sheets 8 onglets (gspread + Polars + Patito) | Backend flexible, éditabilité directe, pas DB à maintenir |
| D3 | CREE → EN_ATTENTE immédiat | Pas de T+0 requis, simplification |
| D4 | FastAPI SSR + Jinja2 + Tailwind | Stack léger, rendu serveur, pas SPA |
| D5 | Playwright sur Indy pour exporter le Journal Book CSV | Pas d'accès API bancaire disponible, Playwright = scraping fiable |
| D6 | Lettrage semi-automatique (système propose, Jules confirme) | MVP pragmatique |
| D7 | Pas de génération PDF — AIS génère les factures PDF | URSSAF demande PDF signé, AIS le fait |
| D8 | Python 3.12 + uv (pas pip/poetry) | Vitesse, déterminisme |
| D9 | ruff strict + pyright strict + pytest ≥80% | Qualité non-négociable |

## Stack Technique
- **Python 3.12**, uv, ruff, pyright strict
- **FastAPI** + Jinja2 + Tailwind (dashboard SSR)
- **Click** + Rich (CLI)
- **Google Sheets** : gspread v6 + Polars + Patito
- **AIS** : Playwright headless (LECTURE — scrape statuts)
- **Indy** : Playwright headless (LECTURE — export Journal CSV)
- **Email** : SMTP Gmail (notifications/alertes)
- **Tests** : pytest + pytest-cov (≥80%)
- **Docker** : python:3.12-slim + Playwright chromium

## Architecture
```
src/
├── adapters/           # Intégrations
│   ├── sheets_adapter.py   # gspread + Polars → Google Sheets
│   ├── ais_adapter.py      # Playwright LECTURE → AIS
│   ├── indy_adapter.py     # Playwright LECTURE → Indy
│   └── email_notifier.py   # SMTP Gmail
├── services/           # Logique métier
│   ├── payment_tracker.py      # Sync AIS → Sheets
│   ├── bank_reconciliation.py  # Sync Indy → lettrage
│   ├── notification_service.py # Alertes email
│   ├── nova_reporting.py       # NOVA trimestriel
│   └── cotisations_service.py  # Charges sociales + fiscal
├── models/             # Pydantic v2 + Patito
├── config.py           # pydantic-settings
├── app.py              # FastAPI
└── cli.py              # Click CLI
```

## CLI
| Commande | Action |
|----------|--------|
| `sap init` | Créer spreadsheet 8 onglets |
| `sap sync` | Scrape AIS → maj Factures/Clients |
| `sap reconcile` | Export Indy → import transactions → lettrage |
| `sap status` | Résumé rapide |
| `sap nova` | Données NOVA trimestriel |
| `sap export` | CSV comptable |

## Cycle TDD
1. **RED** : Tests d'abord (testeur)
2. **GREEN** : Code minimal (implementeur)
3. **REFACTOR** : Nettoyer (revieweur)
4. **VERIFY** : Quality gate (gardien-qualite)

## INTERDIT Absolument
- ❌ Créer des factures (AIS le fait)
- ❌ Soumettre à URSSAF (AIS le fait)
- ❌ Générer des PDF factures (AIS le fait)
- ❌ Inscrire des clients URSSAF (AIS le fait)
- ❌ Modifier SCHEMAS.html
- ❌ Utiliser print() dans src/ (logging obligatoire)
- ❌ Stocker des secrets dans le code (.env obligatoire)
- ❌ Écrire du code sans tests
- ❌ Sauter une phase du cycle TDD
- ❌ Utiliser pip/poetry (uv obligatoire)

## Python Rules

### Type Safety
- Type hints sur **TOUTES** les signatures (params + return)
- `from __future__ import annotations` en tête de CHAQUE fichier
- `typing` pour types complexes : `Optional[T]`, `Union[A, B]`, `list[T]`, `dict[K, V]`
- Pydantic v2 `BaseModel` pour toutes structures

### Code Quality
- `ruff check --fix` + `ruff format` (remplace black, isort, flake8)
- `pyright --strict` pour type checking
- Max 200-400 lignes/fichier, 50 lignes/fonction, 3 niveaux indent
- `snake_case` fonctions/vars, `PascalCase` classes, `UPPER_SNAKE_CASE` constantes

### Imports
stdlib puis third-party puis local. Absolute only, pas de relative.
`pathlib.Path` obligatoire (jamais `os.path`). `logging` obligatoire (jamais `print()`).

### Patterns

#### Pydantic v2
```python
from pydantic import BaseModel, Field, field_validator

class Invoice(BaseModel):
    facture_id: str = Field(min_length=1, pattern=r"^FAC-")
    montant: Annotated[float, Field(gt=0)]
```

#### Repository + DI
```python
class InvoiceService:
    def __init__(self, sheets: SheetsAdapter, ais: AISAdapter) -> None:
        self._sheets = sheets
        self._ais = ais
```

#### Async
```python
results = await asyncio.gather(*tasks, return_exceptions=True)
errors = [r for r in results if isinstance(r, Exception)]
```

#### Logging
```python
logger = logging.getLogger(__name__)
logger.info("Invoice synced", extra={"facture_id": "FAC-001"})
logger.error("AIS scrape failed", exc_info=True)
```

## Security
- `pydantic-settings` BaseSettings pour secrets (`.env`, validation startup)
- ALL external inputs via Pydantic, jamais raw `dict` access
- SQL : parameterized queries only
- File paths : `Path.resolve()` + `is_relative_to()` check
- Never `eval()`/`exec()` avec user input
- `subprocess.run` avec list args uniquement
- Never expose stack traces to clients

## Performance
- Profile first (`cProfile`, `py-spy`) ; benchmark avec `timeit`
- List comprehensions pour transforms simples ; generators pour gros datasets
- NumPy vectorized ops over loops ; Pandas `.loc`/vectorized (jamais `iterrows`)
- Async I/O pour network/file
- `__slots__` sur dataclasses high-volume

## Testing

### TDD Requirement-Driven
- pytest + pytest-asyncio + pytest-cov (min 80%)
- factory_boy pour test data ; freezegun pour time mocking
- Naming : `test_<what>_<condition>_<expected>`
- Pas shared mutable state ; fixed timestamps ; deterministic random seeds
- Mock ALL external APIs ; no live network calls in unit tests
- Coverage gate : `--cov-fail-under=80`

### Coverage Requirements
- **Happy path** : tous les use cases normaux
- **Edge cases** : boundary values, empty inputs, max limits
- **Error handling** : invalid inputs, failure scenarios
- **State transitions** : si stateful, couvrir tous state changes valides

## Commands Essentielles
```bash
# Installation
uv sync

# Development
uvicorn src.app:app --reload --port 8000

# Tests
pytest tests/unit -x --tb=short              # Rapide
pytest --cov=src --cov-report=term-missing   # Coverage
pytest tests/integration -v                  # Intégration

# Quality
ruff check --fix src/ tests/
ruff format src/ tests/
pyright --strict src/

# Docker
docker-compose up --build
docker-compose logs -f

# CLI
python -m src.cli sync
python -m src.cli reconcile
python -m src.cli status
```

## Checklist Pré-Commit
- [ ] Tous tests passent (`pytest --cov=src --cov-fail-under=80`)
- [ ] Ruff OK (`ruff check src/ tests/`)
- [ ] Pyright OK (`pyright --strict src/`)
- [ ] Pas de `print()` dans `src/`
- [ ] Pas de secrets hardcodés
- [ ] Docstrings sur fonctions publiques
- [ ] Commits atomiques : `type(scope): description`
- [ ] SCHEMAS.html intouché
