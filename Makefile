# Cyphergy — Developer Makefile
# Usage: make <target>
# Run `make help` for available targets

.PHONY: help install test lint format typecheck security ci clean

SHELL := /bin/bash
PYTHON ?= python3
SRC_DIR := src
TEST_DIR := tests

# ──────────────────────────────────────────────
# Help
# ──────────────────────────────────────────────
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ──────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────
install: ## Install package in editable mode with dev dependencies
	$(PYTHON) -m pip install -e ".[dev]"
	$(PYTHON) -m pip install pytest-cov pip-audit bandit

# ──────────────────────────────────────────────
# Quality
# ──────────────────────────────────────────────
lint: ## Run ruff linter and format checker
	ruff check .
	ruff format --check .

format: ## Auto-format code with ruff
	ruff format .
	ruff check --fix .

typecheck: ## Run mypy type checking on src/
	mypy $(SRC_DIR)/

# ──────────────────────────────────────────────
# Testing
# ──────────────────────────────────────────────
test: ## Run pytest with verbose output
	pytest -v $(TEST_DIR)/

test-cov: ## Run pytest with coverage report
	pytest \
		--cov=$(SRC_DIR) \
		--cov-report=term-missing \
		--cov-report=html:htmlcov \
		-v \
		$(TEST_DIR)/

test-integration: ## Run integration tests (requires ANTHROPIC_API_KEY)
	pytest -v -m "integration" $(TEST_DIR)/

# ──────────────────────────────────────────────
# Security
# ──────────────────────────────────────────────
security: ## Run pip-audit and bandit security scans
	pip-audit
	bandit -r $(SRC_DIR)/

# ──────────────────────────────────────────────
# CI (mirrors GitHub Actions pipeline)
# ──────────────────────────────────────────────
ci: lint typecheck test security ## Run full CI pipeline locally (lint + typecheck + test + security)

# ──────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────
clean: ## Remove build artifacts, caches, and temp files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	find . -type f -name "bandit-report.json" -delete 2>/dev/null || true
	rm -rf build/ dist/ .eggs/
