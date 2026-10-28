# LMA major project — Phase 0 scaffold.
# Everything runs through uv so all three laptops get the same Python 3.12 env.

UV ?= $(shell command -v uv 2>/dev/null || echo $(HOME)/Library/Python/3.9/bin/uv)
PY := $(UV) run

.DEFAULT_GOAL := help
.PHONY: help setup test lint fmt schemas fixtures hooks clean

LMA_PYTHON ?= data/raw/llm_env/bin/python
DEV_OUTPUT ?= runs/local-v7-dev
RETRIEVAL_PYTHON ?= .venv/bin/python
RETRIEVER ?= bge_m3
DENSE_INDEX ?= data/interim/corpus_v7_index_20261026/bge_m3_vectors.json
MODEL_REVISION ?= 545dc4251c05440727734bcd94334791f6ab0192

.PHONY: run-dev run-all-dev review-dev audit-dev synthetic-faults

run-dev: ## Run B0/B1/B2/M on the six unreviewed development candidates (local model required)
	HF_HOME="$(CURDIR)/data/raw/model_cache" HF_HUB_OFFLINE=1 PYTHONPATH=src $(LMA_PYTHON) -m conditions --queries data/eval/development_candidates.jsonl --conditions B0 B1 B2 M --revision $(MODEL_REVISION) --retriever $(RETRIEVER) --retrieval-python $(RETRIEVAL_PYTHON) --dense-index $(DENSE_INDEX) --output $(DEV_OUTPUT) --resume

run-all-dev: DEV_OUTPUT = runs/local-v7-all-dev
run-all-dev: ## Run all seven conditions with selected BGE-M3 and the cached cross-encoder
	HF_HOME="$(CURDIR)/data/raw/model_cache" HF_HUB_OFFLINE=1 PYTHONPATH=src $(LMA_PYTHON) -m conditions --queries data/eval/development_candidates.jsonl --revision $(MODEL_REVISION) --retriever $(RETRIEVER) --retrieval-python $(RETRIEVAL_PYTHON) --dense-index $(DENSE_INDEX) --reranker-python .venv/bin/python --output $(DEV_OUTPUT) --resume

review-dev: ## Prepare a fresh local blinded support-review packet
	PYTHONPATH=src $(PY) python -m eval.review prepare --runs $(DEV_OUTPUT) --output data/interim/support-review

audit-dev: ## Validate generated graphs, safety boundaries, logs and measured compute
	PYTHONPATH=src $(PY) python -m eval.run_audit --runs $(DEV_OUTPUT) --output reports/integration_validation.json

synthetic-faults: ## Exercise the frozen synthetic tool-fault diagnostic
	PYTHONPATH=src $(PY) python -m eval.faults --output reports/tool_faults_recheck.json

.PHONY: gold adjudicate kappa rq

gold: ## Re-draft the dev gold graphs and check every span against the corpus
	PYTHONPATH=src $(PY) python scripts/draft_gold_graphs.py
	PYTHONPATH=src $(PY) python scripts/check_gold_graphs.py --require

adjudicate: ## Write the two blind adjudication worksheets (keeps started ones)
	PYTHONPATH=src $(PY) python scripts/prepare_adjudication.py --annotators Deepti Varun

kappa: ## Score two completed worksheets -> reports/adjudication_kappa.md
	PYTHONPATH=src $(PY) python scripts/score_adjudication.py

rq: ## Write the RQ1/RQ2 findings from a reviewed run (needs #41, #42, #37 first)
	PYTHONPATH=src $(PY) python scripts/report_rq.py --review-dir data/interim/support-review

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## Create .venv (Python 3.12) and install the project + dev tools
	@command -v $(UV) >/dev/null 2>&1 || { \
		echo "uv not found. Install it with:  curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		echo "or:  python3 -m pip install --user uv"; exit 1; }
	$(UV) python install 3.12
	$(UV) sync --python 3.12 --extra dev
	@echo "env ready -> .venv (python 3.12). Run 'make hooks' once to enable pre-commit."

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

hooks: ## Install the git pre-commit hooks
	$(PY) pre-commit install

clean: ## Remove caches and the virtualenv
	rm -rf .venv .pytest_cache .ruff_cache **/__pycache__
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
