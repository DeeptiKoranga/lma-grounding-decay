# Reproduce the integrated development pipeline

Updated 23 October 2026. Unit checks and development runs are distinct from a
reviewed research experiment. Corpus acceptance, independent annotations, model
selection and missing series remain open; see the acceptance report.

## Core checks

```sh
make setup
make lint test
```

Core checks require no model, corpus download, API key or GPU. Optional-backend
tests use fixtures or skip unavailable native libraries. Tests never certify the
independence of a reviewer or manufacture missing support judgments.

## Local model and optional retrieval runtime

The default development model is `mlx-community/Qwen3-8B-4bit`, revision
`545dc4251c05440727734bcd94334791f6ab0192`. This is an integration choice; D-01
is still open. Keep it the same across all conditions. Its download and optional
dependencies stay under ignored `data/raw/`.

```sh
UV_CACHE_DIR=/private/tmp/lma-uv-cache uv venv data/raw/llm_env --python .venv/bin/python
UV_CACHE_DIR=/private/tmp/lma-uv-cache uv pip install --python data/raw/llm_env/bin/python -r configs/requirements-local-llm.txt
UV_CACHE_DIR=/private/tmp/lma-uv-cache uv pip install --python .venv/bin/python -r configs/requirements-retrieval.txt
```

Download the public model with Hugging Face `snapshot_download`, passing that
exact revision and `local_dir='data/raw/generator/qwen3-8b-4bit'`. Model Python
code is not downloaded or executed. The isolated runtime avoids changing the
core environment when local inference requires different packages.

The first stage is plain BM25 for these development runs; D-02/D-03 are not
resolved. B1-R uses the same BM25 candidates plus the pinned existing BGE
cross-encoder, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`, from the
local Hugging Face cache. The worker runs in `.venv` and releases its memory when
it exits. No reranker download occurs during a development sweep.

## Corpus transfer

The corpus payload and model caches are intentionally excluded from git.
Obtain the locally frozen archive separately, review reproduction terms and
verify its checksum against `data/processed/MANIFEST.md`. It contains the saved
passages and their parent document text. Do not substitute a new scrape without
rebuilding indexes and repeating the input/review audits.

The pipeline uses `data/processed/articles.jsonl`, `data/aliases.yaml` and the
accepted CSVs under `data/series/`. Candidate FPI values remain outside that
store. The development provenance file binds the corpus, aliases, query file,
series CSVs, model revision, conditions and relevant source code hash.

## Run and resume

```sh
UV_NO_SYNC=1 UV_CACHE_DIR=/private/tmp/lma-uv-cache make run-dev DEV_OUTPUT=runs/my-dev
UV_NO_SYNC=1 UV_CACHE_DIR=/private/tmp/lma-uv-cache make run-all-dev DEV_OUTPUT=runs/my-all-dev
```

The first command runs B0/B1/B2/M; the second runs all seven conditions.
Each query/condition gets a validated graph, provisional established-edge IDs,
raw candidates, optional prose answer, and a separate append-only event log.
Actual prompts, completions, token counts and call wall times are recorded.
Graph output is written only after a completed run. Failed attempts retain their
logs and are listed separately. Resume refuses changed settings/input hashes.

`make run-dev` requires Metal access and downloaded weights; it is not a fixture
substitute for a research sweep. `--backend llama.cpp` and `--backend vllm` accept
an explicitly configured local `/v1` chat endpoint. Remote endpoints require
`--allow-remote`; no paid fallback occurs automatically. Native HTTP backends
are transport adapters and have not been validated on Kaggle in this session.

## Audit, review and figures

Correct the mechanically extracted prose baselines before their final support
review. The correction packet includes the actual answer and editable graph;
the reviewer must preserve the answer's errors rather than improve its content.

```sh
PYTHONPATH=src .venv/bin/python -m eval.prose_review prepare --runs runs/my-all-dev --output data/interim/prose_corrections.json
# After a human completes every correction and their own attestation:
PYTHONPATH=src .venv/bin/python -m eval.prose_review export --runs runs/my-all-dev --corrections data/interim/prose_corrections.json --output runs/my-corrected-dev
```

Use the corrected run folder for final support packets. The scorer refuses
uncorrected prose baselines, even if support judgments have been completed.

```sh
PYTHONPATH=src .venv/bin/python -m eval.run_audit --runs runs/my-all-dev --output reports/integration_recheck.json
PYTHONPATH=src .venv/bin/python -m eval.review prepare --runs runs/my-all-dev --output data/interim/my-support-review
```

For final scoring, replace the example run path with `runs/my-corrected-dev`.
Give a reviewer `packet.json` and blank `judgments.json`, keeping
`private_mapping.json` with the curator. The local page
`notebooks/review_edges.html` loads these files without uploading them. The
reviewer judges all items and fills their own identity, date and attestations.
Incomplete, changed or unattested packets fail scoring.

```sh
PYTHONPATH=src .venv/bin/python -m eval.review score --review data/interim/my-support-review --references data/eval/gold/dev --output reports/reviewed_dev.json
PYTHONPATH=src data/raw/llm_env/bin/python -m eval.figures --reviewed-scores reports/reviewed_dev.json --output reports/uer_by_hop.png
PYTHONPATH=src .venv/bin/python -m eval.figures --graph runs/my-all-dev/M/dev-candidate-01.json --output reports/development_example.svg
```

Reference graphs must exist and match the reviewed query/cutoff; the placeholder
gold directory is insufficient. Omit `--references` to measure attached support
without reference recall. Missing recall cannot pass the recall guard. The UER
plot refuses unreviewed scores and missing hop denominators. Graph exports need
Graphviz; plots use the isolated runtime's pinned Matplotlib.

The independent retrieval review is separate: follow
`reports/retrieval_review_workflow.md`. A support-review packet does not resolve
retriever relevance, and a retrieval relevance judgment does not establish an
edge's causal direction or strength.

## Capability fixtures and limits

`scripts/build_capability_fixtures.py` regenerates 40 synthetic action states,
20 fault specifications and 25 adversarial prompts under `data/eval/synthetic`.
`python -m eval.faults` executes the frozen faults against the real tool boundary.
`eval.capabilities.evaluate_actions` probes model tool selection on the synthetic
states. Neither is a substitute for the planned real-run state benchmark or
human adjudication of advice/forecast leakage.

`eval.challenge` generates 100 corruption candidates and 25 controls only after
enough eligible reviewed gold exists. It requires genuinely hedged seeds for
strength inflation and leaves all challenge outcome labels unfilled for review.
`eval.agreement` calculates Cohen's kappa and the predeclared strength-collapse
trigger. It never invents an agreement score when the paired labels are absent.
