# Règles Python — SAP-Facture

## Imports

- `from __future__ import annotations` en haut de CHAQUE fichier
- stdlib → third-party → local (ruff enforce)
- `pathlib.Path` uniquement (jamais `os.path`)
- `logging` uniquement (jamais `print()`)
- Imports absolus uniquement, pas de relatifs cross-package

## Types

- Type hints sur TOUTES les signatures (params + return)
- Pydantic v2 `BaseModel` pour les structures de données
- Polars pour les DataFrames (manipulation de données tabulaires)
- `Optional[T]` ou `T | None` pour les champs nullable
- `Literal["value"]` pour les enums à domaine fermé

## Style

- `snake_case` fonctions/variables, `PascalCase` classes, `UPPER_SNAKE_CASE` constantes
- Max 400 lignes/fichier, 50 lignes/fonction, 3 niveaux d'indentation
- Commentaires uniquement quand l'intent n'est pas évident
- Espacements cohérents (multiples de 4)

## Patterns Obligatoires

### Repository + DI
```python
class InvoiceService:
    def __init__(self, repo: InvoiceRepository, adapter: SheetsAdapter) -> None:
        self._repo = repo
        self._adapter = adapter
```

### Async I/O
```python
results = await asyncio.gather(*tasks, return_exceptions=True)
errors = [r for r in results if isinstance(r, Exception)]
```

### Logging
```python
logger = logging.getLogger(__name__)
logger.info("Invoice created", extra={"invoice_id": inv.id})
logger.error("Sheets error", exc_info=True)
```

### Config & Secrets
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    google_credentials: str
    urssaf_client_id: str

    class Config:
        env_file = ".env"
```

## Sécurité

- Pydantic pour TOUTES les entrées externes (query params, body, headers)
- SQL : requêtes paramétrées uniquement, jamais de f-strings
- Paths : `Path.resolve()` + `is_relative_to()` pour valider les répertoires
- Jamais `eval()`/`exec()` avec input utilisateur
- `subprocess.run()` avec list args (jamais string shell)
- Secrets jamais en dur ; `.env` jamais committé

## Tests

- pytest + pytest-asyncio + pytest-cov (min 80%)
- Nommage : `test_<quoi>_<condition>_<attendu>`
- Mock TOUTES les APIs externes (gspread, URSSAF, Playwright)
- factory_boy pour les données de test
- Pas d'état mutable partagé entre tests
- Timestamps fixés (freezegun), seeds déterministes
- Couverture minimum 80% : `--cov-fail-under=80` en pyproject.toml

## Stack SAP-Facture

### Google Sheets
- **gspread v6** : client, authentification OAuth2
- **Polars** : manipulation de DataFrames (filtrage, agrégation, joins)
- Patito pour modèles typés sur Sheets (deprecated → migrer vers Polars)

### URSSAF API
- **httpx** : client async HTTP
- OAuth2 client_credentials (pydantic-settings pour secrets)
- Retry logic : exponential backoff

### Banking
- **Playwright** headless : scraping Indy pour transactions
- Parsing CSV bancaire : Polars

### PDF & Documents
- **WeasyPrint** : génération PDF à partir de HTML
- **Jinja2** : templates HTML/XML
- Localisation : babel pour dates/nombres

### Email
- **aiosmtplib** : envoi async (Gmail SMTP)
- **email-validator** : validation adresses

### CLI & Web
- **Click** : CLI avec commands + options
- **Rich** : output formaté (tables, progress bars)
- **FastAPI** : SSR avec Jinja2, Pydantic validation
- **Tailwind CSS** : styling

## Conventions Métier

### Modèles Métier
```python
from pydantic import BaseModel, Field

class Invoice(BaseModel):
    id: str = Field(min_length=1)
    client_id: str
    amount: float = Field(gt=0)
    status: Literal["draft", "sent", "paid", "cancelled"]
    issued_at: datetime
```

### Services
- Une responsabilité par service
- DI via constructeur (pas de singletons globaux)
- Async-first (si I/O)

### Repositories
- CRUD opérations uniquement
- Return None au lieu de lever pour "not found"
- Parameterized queries pour DB

## Performance

- Profiler avant d'optimiser (`cProfile`, `py-spy`)
- Polars vectorisé au lieu de boucles
- Async/await pour I/O réseau/fichier
- Connection pooling pour DB/API
- Timeouts sur TOUS les appels externes

## Checklist Avant Commit

- [ ] `ruff check --fix` + `ruff format` réussissent
- [ ] `mypy --strict` sans erreurs (type coverage 100%)
- [ ] Tests: `pytest --cov=app --cov-fail-under=80` passent
- [ ] Logs vérifiés (pas de `print()`, secrets masqués)
- [ ] Secrets dans `.env`, jamais committé
- [ ] Docstrings sur fonctions publiques (une ligne pour APIs simples)
