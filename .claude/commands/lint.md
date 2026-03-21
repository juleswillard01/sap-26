---
description: Lint + format + types — ruff, pyright
---

# /lint — Qualité Code

Action : $ARGUMENTS

## Commandes

### tout
1. `uv run ruff check src/ tests/`
2. `uv run ruff format --check src/ tests/`
3. `uv run pyright src/`

### fix
1. `uv run ruff check --fix src/ tests/`
2. `uv run ruff format src/ tests/`

### types
`uv run pyright src/`

### [fichier]
1. `uv run ruff check $ARGUMENTS`
2. `uv run pyright $ARGUMENTS`
