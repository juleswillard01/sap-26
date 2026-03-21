---
description: Suite de tests — unit, integration, couverture, filtre
---

# /test — Tests

Action : $ARGUMENTS

## Commandes

### tout
`uv run pytest tests/ -v --tb=short`

### unit
`uv run pytest tests/ -v --tb=short -m "not integration"`

### integration
`uv run pytest tests/ -v --tb=short -m integration`

### couverture
`uv run pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80`

### [pattern]
`uv run pytest tests/ -k "$ARGUMENTS" -v --tb=short`

### derniers
`uv run pytest tests/ --lf -v --tb=short`

## Seuils
- Coverage minimum : 80%
- Timeout par test : 30s
- Mode : unit tests seulement en auto (hook PostToolUse)
