.PHONY: install test test-cov lint typecheck format dev docker-build docker-run sync reconcile export clean

install:
	uv sync --all-extras
	uv run playwright install --with-deps chromium

test:
	uv run pytest -x --tb=short

test-cov:
	uv run pytest --cov=src --cov-report=term-missing

lint:
	uv run ruff check src tests
	uv run ruff format --check src tests

typecheck:
	uv run pyright src

format:
	uv run ruff format src tests
	uv run ruff check --fix src tests

dev:
	uv run uvicorn src.app:app --reload --port 8000

docker-build:
	docker build -t sap-facture .

docker-run:
	docker-compose up

sync:
	uv run python -m src.cli sync

reconcile:
	uv run python -m src.cli reconcile

export:
	uv run python -m src.cli export

status:
	uv run python -m src.cli status

clean:
	rm -rf io/exports/* io/cache/* .pytest_cache .ruff_cache __pycache__ .pyright
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
