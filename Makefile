.PHONY: help install lint format typecheck test cov check build clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install package with development dependencies
	python -m pip install -e '.[dev]'

lint: ## Run Ruff lint checks
	python -m ruff check .

format: ## Check Ruff formatting
	python -m ruff format --check .

typecheck: ## Run strict static typing
	python -m mypy

test: ## Run test suite with branch coverage
	python -m pytest --cov --cov-report=term-missing

cov: test ## Alias for coverage report

check: lint format typecheck test ## Run all quality gates

build: ## Build source and wheel distributions
	python -m build

clean: ## Remove generated artifacts
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache build dist htmlcov src/*.egg-info
