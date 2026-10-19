# LMA major project — Phase 0 scaffold.
# Everything runs through uv so all three laptops get the same Python 3.12 env.

UV ?= $(shell command -v uv 2>/dev/null || echo $(HOME)/Library/Python/3.9/bin/uv)
PY := $(UV) run

.DEFAULT_GOAL := help
.PHONY: help setup test lint fmt schemas fixtures hooks clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## Create .venv (Python 3.12) and install the project + dev tools
	@command -v $(UV) >/dev/null 2>&1 || { \
		echo "uv not found. Install it with:  curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		echo "or:  python3 -m pip install --user uv"; exit 1; }
	$(UV) python install 3.12
	$(UV) sync --extra dev
	@echo "env ready -> .venv (python 3.12). Run 'make hooks' once - it is required, not optional."

test: ## Run the test suite
	$(PY) pytest

lint: ## ruff + black --check
	$(PY) ruff check .
	$(PY) black --check .

fmt: ## Auto-fix with ruff and format with black
	$(PY) ruff check --fix .
	$(PY) black .

schemas: ## Regenerate docs/schemas/*.schema.json from the Pydantic models
	$(PY) python -m schema.export_schemas

fixtures: ## Regenerate tests/fixtures/ (offsets are computed, never hand-written)
	$(PY) python scripts/build_fixtures.py

hooks: ## Install the git hooks (pre-commit + the main-branch guard)
	$(PY) pre-commit install
	@mkdir -p .git/hooks
	@ln -sf ../../scripts/git-hooks/pre-push .git/hooks/pre-push
	@echo "pre-push guard installed: direct pushes to main are refused."

clean: ## Remove caches and the virtualenv
	rm -rf .venv .pytest_cache .ruff_cache **/__pycache__
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
