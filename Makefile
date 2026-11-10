# LMA major project — Phase 0 scaffold.
# Everything runs through uv so all three laptops get the same Python 3.12 env.

UV ?= $(shell command -v uv 2>/dev/null || echo $(HOME)/Library/Python/3.9/bin/uv)
PY := $(UV) run

.DEFAULT_GOAL := help
.PHONY: help setup test lint fmt schemas fixtures hooks clean

LMA_PYTHON ?= data/raw/llm_env/bin/python
DEV_OUTPUT ?= runs/local-v7-dev
REVIEW_OUTPUT ?= data/interim/support-review
RETRIEVAL_PYTHON ?= .venv/bin/python
RETRIEVER ?= bge_m3
DENSE_INDEX ?= data/interim/corpus_v7_index_20261026/bge_m3_vectors.json
MODEL_SELECTION ?= configs/model_selection.json
MODEL_ARGS ?= --model-selection $(MODEL_SELECTION)

.PHONY: run-dev run-all-dev review-dev audit-dev synthetic-faults agent-metrics

.PHONY: validate-track-c
validate-track-c: ## Verify every Phase 1 Track C deliverable against saved execution evidence
	PYTHONPATH=src $(PY) python scripts/validate_phase1_track_c.py

run-dev: ## Run B0/B1/B2/M on the six unreviewed development candidates (local model required)
	HF_HOME="$(CURDIR)/data/raw/model_cache" HF_HUB_OFFLINE=1 PYTHONPATH=src $(LMA_PYTHON) -m conditions --queries data/eval/development_candidates.jsonl --conditions B0 B1 B2 M $(MODEL_ARGS) --retriever $(RETRIEVER) --retrieval-python $(RETRIEVAL_PYTHON) --dense-index $(DENSE_INDEX) --output $(DEV_OUTPUT) --resume

run-all-dev: DEV_OUTPUT = runs/local-v7-all-dev
run-all-dev: ## Run all seven conditions with selected BGE-M3 and the cached cross-encoder
	HF_HOME="$(CURDIR)/data/raw/model_cache" HF_HUB_OFFLINE=1 PYTHONPATH=src $(LMA_PYTHON) -m conditions --queries data/eval/development_candidates.jsonl $(MODEL_ARGS) --retriever $(RETRIEVER) --retrieval-python $(RETRIEVAL_PYTHON) --dense-index $(DENSE_INDEX) --reranker-python .venv/bin/python --output $(DEV_OUTPUT) --resume

# ---------------------------------------------------------------------------
# The gold-backed sweep, and its two arms (D-28).
#
# run-dev and run-all-dev above sweep development_candidates.jsonl, whose six
# query_ids (dev-candidate-01..06) match NO gold graph. Scoring that output
# with --references raises "reference graph query/cutoff/anchor mismatch", so
# those targets cannot produce reference-edge recall and cannot answer H2d.
# The targets below sweep data/eval/queries_dev.jsonl, the four queries the
# adjudicated gold set is built for.
# ---------------------------------------------------------------------------

GOLD_QUERIES ?= data/eval/queries_dev.jsonl
ARM_PRIMARY_OUTPUT  ?= runs/dev-gold-qwen3-8b
ARM_SENSITIVITY_OUTPUT ?= runs/dev-gold-qwen35-9b
ALT_MODEL_SELECTION ?= configs/model_selection_qwen35_9b.json

.PHONY: sweep-dev-primary sweep-dev-sensitivity sweep-dev-both

define sweep_all_conditions
HF_HOME="$(CURDIR)/data/raw/model_cache" HF_HUB_OFFLINE=1 PYTHONPATH=src $(LMA_PYTHON) \
	-m conditions --queries $(GOLD_QUERIES) --model-selection $(1) \
	--retriever $(RETRIEVER) --retrieval-python $(RETRIEVAL_PYTHON) \
	--dense-index $(DENSE_INDEX) --reranker-python .venv/bin/python \
	--output $(2) --resume
endef

sweep-dev-primary: ## D-28 primary arm: all seven conditions on the gold-backed dev queries
	$(call sweep_all_conditions,$(MODEL_SELECTION),$(ARM_PRIMARY_OUTPUT))

sweep-dev-sensitivity: ## D-28 sensitivity arm: the same sweep, generator weights only changed
	$(call sweep_all_conditions,$(ALT_MODEL_SELECTION),$(ARM_SENSITIVITY_OUTPUT))

sweep-dev-both: ## Both D-28 arms, in order. Read neither until both finish.
	@echo "Both arms are pre-registered in docs/preregistration_model_sensitivity.md."
	@echo "The primary arm supplies every headline number whatever the numbers say."
	$(MAKE) sweep-dev-primary
	$(MAKE) sweep-dev-sensitivity

review-dev: ## Prepare a fresh local blinded support-review packet
	PYTHONPATH=src $(PY) python -m eval.review prepare --runs $(DEV_OUTPUT) --output $(REVIEW_OUTPUT)

agent-metrics: ## Agentic capability metrics (Table 4) from a sweep's run logs
	PYTHONPATH=src $(PY) python scripts/report_agent_metrics.py --runs $(ARM_PRIMARY_OUTPUT)

audit-dev: ## Validate generated graphs, safety boundaries, logs and measured compute
	PYTHONPATH=src $(PY) python -m eval.run_audit --runs $(DEV_OUTPUT) --output reports/integration_validation.json

synthetic-faults: ## Exercise the frozen synthetic tool-fault diagnostic
	PYTHONPATH=src $(PY) python -m eval.faults --output reports/tool_faults_recheck.json

.PHONY: gold adjudicate kappa rq challenge

gold: ## Re-draft the dev gold graphs and check every span against the corpus
	PYTHONPATH=src $(PY) python scripts/draft_gold_graphs.py
	PYTHONPATH=src $(PY) python scripts/check_gold_graphs.py --require

adjudicate: ## Write the two blind adjudication worksheets (keeps started ones)
	PYTHONPATH=src $(PY) python scripts/prepare_adjudication.py --annotators Deepti Varun

kappa: ## Score two completed worksheets -> reports/adjudication_kappa.md
	PYTHONPATH=src $(PY) python scripts/score_adjudication.py

# The test half (#38). Two of its four queries carry no graph: test-cpi-why by
# D-27, and test-cpi-effects because this corpus treats Indian headline CPI as
# the destination of the oil shock rather than its source. The drafts are NOT
# adjudicated and must not be scored with --references until two annotators
# have read every span and signed a receipt.
.PHONY: test-gold test-gold-feasibility adjudicate-test kappa-test

test-gold-feasibility: ## Which test queries could carry gold at all, before anyone drafts
	PYTHONPATH=src $(PY) python scripts/audit_test_gold_feasibility.py

test-gold: ## Draft the test gold graphs and check every span against the corpus
	PYTHONPATH=src $(PY) python scripts/draft_test_gold_graphs.py
	PYTHONPATH=src $(PY) python scripts/draft_test_gold_graphs.py --check

adjudicate-test: ## Write the two blind test worksheets (keeps started ones)
	PYTHONPATH=src $(PY) python scripts/prepare_adjudication.py --set test --annotators Deepti Harshal

kappa-test: ## Score two completed test worksheets
	PYTHONPATH=src $(PY) python scripts/score_adjudication.py --set test

rq: ## Write the RQ1/RQ2 findings from a reviewed run (needs #41, #42, #37 first)
	PYTHONPATH=src $(PY) python scripts/report_rq.py --review-dir data/interim/support-review

challenge: ## Build the challenge set and run the rules-only arm (no model needed)
	# Needs a signed data/eval/gold/dev/review_receipt.json. Add --allow-unreviewed
	# to build from unsigned gold; the manifest then records gold_adjudicated false
	# and the false-alarm denominator is not quotable.
	@rm -f data/eval/challenge.jsonl data/eval/challenge_manifest.json
	PYTHONPATH=src $(PY) python -m eval.challenge --gold data/eval/gold/dev \
		--corpus data/processed/articles.jsonl --output data/eval/challenge.jsonl
	PYTHONPATH=src $(PY) python scripts/run_challenge.py

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
