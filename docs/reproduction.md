# Reproduce the integrated development pipeline

Updated 23 October 2026. Unit checks and development runs are distinct from a
reviewed research experiment. Corpus acceptance, independent annotations, model
selection, complete series histories and anchor confirmation remain open; see
`reports/track_a_progress.md`.

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
CSV observations under `data/series/`. All six files have data, but four
have sparse coverage; read `data/series/README.md` for exact measurement types.
Unverified dynamic CDSL/FBIL candidates remain outside that store. The development provenance file binds the corpus, aliases, query file,
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
It also attaches trusted cited paragraphs from `--corpus`. An extractor quote
can be corrected from that same cited paragraph when the prose gives only its
ID; the answer's claims and cited passage identity must be preserved.

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
The correction packet exposes condition names, so its corrector cannot also
claim blinded support review of those same items. Keep that support review with
someone who has not consulted the corrections or run outputs.

```sh
# After building source-backed reference graphs, prepare their blank review receipt:
PYTHONPATH=src .venv/bin/python -m eval.references --references data/eval/gold/dev
# An independent human reviews every relation/strength and fills their own receipt.
PYTHONPATH=src .venv/bin/python -m eval.review score --review data/interim/my-support-review --references data/eval/gold/dev --output reports/reviewed_dev.json
PYTHONPATH=src data/raw/llm_env/bin/python -m eval.figures --reviewed-scores reports/reviewed_dev.json --output reports/uer_by_hop.png
PYTHONPATH=src .venv/bin/python -m eval.figures --graph runs/my-all-dev/M/dev-candidate-01.json --output reports/development_example.svg
```

Reference graphs must contain exact eligible source citations, match the reviewed
query/cutoff/anchor and carry a complete independent `review_receipt.json` bound
to their bytes and the support corpus. The placeholder gold directory is
insufficient. Omit `--references` to measure attached support
without reference recall. Missing recall cannot pass the recall guard. The UER
plot refuses unreviewed scores and missing hop denominators. Graph exports need
Graphviz; plots use the isolated runtime's pinned Matplotlib.

The recall guard reports the query-macro M-minus-B1 reference-recall difference
against the predeclared −0.10 threshold only when both conditions cover the same
queries with complete reference denominators. Otherwise its descriptive outcome
remains null. This development guard is not confirmation of H2.

The independent retrieval review is separate: follow
`reports/retrieval_review_workflow.md`. A support-review packet does not resolve
retriever relevance, and a retrieval relevance judgment does not establish an
edge's causal direction or strength.

## Recorded 23 October development phases

The actual local run used a baseline phase and a corrected agent phase. A
controller stop-state bug was fixed after the baseline phase; baseline
generation itself was unchanged. Preserve both source fingerprints rather than
presenting the assembly as a single-version frozen experiment:

```sh
PYTHONPATH=src .venv/bin/python scripts/assemble_development_phases.py \
  --baseline runs/development_prose_20261023 \
  --agent runs/development_agents_20261023 \
  --queries data/eval/development_candidates.jsonl \
  --output runs/development_complete_20261023
```

The assembler refuses incomplete cases or different shared inputs, validates
graphs and logs, retains failed attempts and records per-file hashes. Earlier
direct-graph runs and the interrupted old agent attempt are excluded. Human
correction/review must use newly prepared packets bound to the assembled files;
moving a packet between run folders invalidates its mapping.

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

## Current Track A development corpus and retrieval

The active root corpus is **v3 development**, not a research-accepted freeze.
It has 1,177 documents and 28,391 passages. `reports/corpus_versions.json` binds
the current root, archived v1 experiments and superseded v2 candidate.

To rebuild v3 from its checksummed local raw inputs in a new output directory,
start explicitly from the archived original v1 corpus:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.prepare_corpus_revision \
  --frozen data/interim/frozen_v1_20261023 --reparse-raw data/raw \
  --version v3-candidate --output data/interim/corpus_v3_recheck \
  --report reports/corpus_v3_recheck.json
```

This reparses original news, adds the ten eligible Mint pages, checks all exact
offsets, freezes in both input orders and creates blank extraction judgments.
Raw publisher/official files and cached rejection sidecars must be present;
these commands imply no permission to redistribute them.

The current pairs preserve 43 seed texts and unchanged query wording/cutoffs.
They are machine curated, not independently judged. To rerun the real comparison
using the saved v3 index:

```sh
HF_HOME="$PWD/data/raw/model_cache" HF_HUB_OFFLINE=1 OMP_NUM_THREADS=1 \
  VECLIB_MAXIMUM_THREADS=1 PYTHONPATH=src .venv/bin/python -m retrieval.pilot_runner \
  --pairs reports/retriever_temporal_v3_pairs.jsonl --corpus data/processed/articles.jsonl \
  --smoke --device cpu --max-length 1024 \
  --dense-index data/interim/corpus_v3_20261023/bge_m3_vectors.json \
  --dense-backend faiss --embedding-batch-size 8 --reranker-batch-size 1 \
  --embedding-revision 5617a9f61b028005a4858fdac845db406aefb181 \
  --rerank --reranker-revision 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e \
  --local-files-only --output reports/pilot_v3_recheck.md \
  --candidate-output data/interim/retrieval_candidates_v3_recheck.jsonl
```

Without that index, supply a fresh `--dense-index` path and
`--embedding-checkpoint data/interim/corpus_v3_20261023/bge_m3_checkpoint.json`.
Text/model/preprocessing hashes validate reuse. Keep original caches unchanged.
The pilot report records actual packages, pinning, cache state and phase time.

Current blinded packet: `data/interim/retrieval_review_temporal_v4/`, 2,062 items.
To prepare another packet, use a fresh output directory:

```sh
PYTHONPATH=src .venv/bin/python -m retrieval.review prepare \
  --pairs reports/retriever_temporal_v3_pairs.jsonl --corpus data/processed/articles.jsonl \
  --curator 'Codex (machine curation for Varun Patil)' \
  --candidate-pool data/interim/retrieval_review_candidates_temporal_v4.jsonl \
  --output data/interim/retrieval_review_v3_recheck
```

`reports/retrieval_v3_review_readiness.json` records the current packet hashes,
all-seed/four-way-pool coverage, cutoff checks and actual blank-export refusal.
Give only its packet, review text and blank judgments to an independent reviewer;
keep seeds, ranks and reports hidden. Resolve extraction/source acceptance before
final relevance selection. D-02/D-03 remain open. Old v2 commands and counts are
preserved in the historical continuation, not the current pipeline recipe.

## Reproducing or reviewing the earlier experiments

The 42-graph assembly and full fresh 24-graph reproduction used archived v1.
Their review preparation and audits **must** supply:

```sh
--corpus data/interim/frozen_v1_20261023/articles.jsonl
```

A recorded corpus mismatch now fails before review output is created. Corrected
prose exports preserve the corpus hash for downstream support review.
`reports/fresh_full_development_reproduction.json` records the exact original
model, corpus, aliases, queries and three series hashes. The original series
snapshot is `data/interim/fresh_reproduction_inputs_20261023/series/`.
Reproducing those exact results requires those inputs, not the newly extended
canonical series. The completed sweep used source `bbc9288`, all six development
candidates and B0/B1/B2/M; all 24 canonical graphs match after dropping only
`run_id`. It reused weights/runtime and does not certify other machines or
Kaggle. A new v3 experiment needs new logs and review packets.
