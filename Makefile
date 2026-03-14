.PHONY: help dev test lint format mypy migrate clean deploy logs

# Variables
PYTHON := python
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
RUFF := $(PYTHON) -m ruff
MYPY := $(PYTHON) -m mypy
ALEMBIC := alembic

# Colors
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(GREEN)SAP-Facture Make Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

dev: ## Build and start development environment
	@echo "$(GREEN)Starting development environment...$(NC)"
	docker compose up --build

dev-down: ## Stop development environment
	@echo "$(GREEN)Stopping development environment...$(NC)"
	docker compose down

dev-logs: ## Follow development logs
	docker compose logs -f

install: ## Install dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(PIP) install -e ".[dev]"

test: ## Run tests with coverage
	@echo "$(GREEN)Running tests...$(NC)"
	$(PYTEST) tests/ \
		--cov=app \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-fail-under=80 \
		-v

test-quick: ## Run tests without coverage
	$(PYTEST) tests/ -v

test-watch: ## Run tests on file changes
	$(PYTEST) tests/ --watch

lint: ## Run ruff linter
	@echo "$(GREEN)Linting code...$(NC)"
	$(RUFF) check app/ tests/

format: ## Format code with ruff
	@echo "$(GREEN)Formatting code...$(NC)"
	$(RUFF) format app/ tests/
	$(RUFF) check --fix app/ tests/

mypy: ## Type check with mypy
	@echo "$(GREEN)Type checking...$(NC)"
	$(MYPY) app/

check: lint mypy ## Run all checks (lint + mypy)

migrate: ## Run database migrations
	@echo "$(GREEN)Running migrations...$(NC)"
	$(ALEMBIC) upgrade head

migrate-down: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	$(ALEMBIC) downgrade -1

migrate-status: ## Show migration status
	$(ALEMBIC) current

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)Error: MSG is required (usage: make migrate-create MSG=\"description\")$(NC)"; \
		exit 1; \
	fi
	$(ALEMBIC) revision --autogenerate -m "$(MSG)"

clean: ## Clean up cache and build files
	@echo "$(GREEN)Cleaning up...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name build -exec rm -rf {} + 2>/dev/null || true

deploy: ## Run deployment script (usage: make deploy ARGS="--build --migrate")
	@echo "$(GREEN)Running deployment...$(NC)"
	./deploy/deploy.sh $(ARGS)

deploy-build: ## Deploy with Docker build
	./deploy/deploy.sh --build

deploy-migrate: ## Deploy with migrations
	./deploy/deploy.sh --migrate

deploy-restart: ## Deploy and restart service
	./deploy/deploy.sh --restart

logs: ## Show application logs
	@echo "$(GREEN)Showing application logs...$(NC)"
	docker compose logs -f app

logs-nginx: ## Show nginx logs
	docker compose logs -f nginx

shell: ## Open shell in app container
	docker compose exec app /bin/bash

db-shell: ## Open SQLite shell in app container
	docker compose exec app sqlite3 data/sap.db

stats: ## Show project statistics
	@echo "$(GREEN)Project Statistics$(NC)"
	@echo "Python files: $$(find app -type f -name '*.py' | wc -l)"
	@echo "Test files: $$(find tests -type f -name '*.py' | wc -l)"
	@echo "Total lines of code:"
	@find app -type f -name '*.py' -exec wc -l {} + | tail -1
	@echo "Total test lines:"
	@find tests -type f -name '*.py' -exec wc -l {} + | tail -1
