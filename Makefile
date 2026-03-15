.PHONY: help install dev test lint format type-check clean cli docker-build docker-run docker-dev init-sheets seed-data health-check

help:
	@echo "SAP-Facture Development Commands"
	@echo "================================="
	@echo "make install        # Install dependencies (dev + prod)"
	@echo "make dev            # Run FastAPI dev server (hot reload)"
	@echo "make test           # Run pytest avec coverage"
	@echo "make test-watch     # Run pytest en watch mode"
	@echo "make lint           # Lint + format (ruff)"
	@echo "make type-check     # Type checking (mypy strict)"
	@echo "make format         # Auto-format code (ruff)"
	@echo "make clean          # Remove cache, build artifacts"
	@echo "make cli            # Run CLI (sap command)"
	@echo "make docker-build   # Build Docker image"
	@echo "make docker-run     # Run Docker container"
	@echo "make docker-dev     # Run docker-compose dev stack"
	@echo "make init-sheets    # Initialize Google Sheets"
	@echo "make seed-data      # Seed test data"
	@echo "make health-check   # Check external API connections"

install:
	python3.11 -m venv venv 2>/dev/null || true
	. venv/bin/activate && pip install -U pip setuptools wheel
	. venv/bin/activate && pip install -e ".[dev]"
	pre-commit install

dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest tests/ --cov=app --cov-fail-under=80 --cov-report=term-missing

test-watch:
	pytest-watch -- tests/ --cov=app

lint:
	ruff check --fix app/ tests/ scripts/
	ruff format app/ tests/ scripts/

format:
	ruff format app/ tests/ scripts/

type-check:
	mypy --strict app/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov dist build *.egg-info 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true

cli:
	python -m app.cli.commands

docker-build:
	docker build -t sap-facture:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env sap-facture:latest

docker-dev:
	docker-compose -f docker-compose.dev.yml up

docker-dev-down:
	docker-compose -f docker-compose.dev.yml down

init-sheets:
	python scripts/init_sheets.py

seed-data:
	python scripts/seed_dev_data.py

health-check:
	python scripts/health_check.py
