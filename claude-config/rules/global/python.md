# Python Rules

## Type Safety
- Type hints sur TOUTES les signatures (params + return)
- `from __future__ import annotations` dans chaque fichier
- Pydantic v2 BaseModel pour toutes structures
- pyright strict mode

## Code Quality
- ruff check + ruff format (remplace black, isort, flake8)
- Max 200-400 lignes/fichier, 50 lignes/fonction
- snake_case fn/vars, PascalCase classes, UPPER_SNAKE_CASE constants
- pathlib.Path obligatoire (jamais os.path)
- logging obligatoire (jamais print() dans src/)

## Imports
stdlib → third-party → local. Absolute only.

## Data
- Polars > pandas pour manipulation de données
- Patito pour validation Polars DataFrames via Pydantic
- List comprehensions pour transforms simples
- Generators pour grands datasets
- Async I/O pour réseau/fichiers

## Performance
- Profiler d'abord (cProfile, py-spy) avant d'optimiser
- Vectorized ops, jamais iterrows()
- asyncio.gather pour parallélisme I/O
