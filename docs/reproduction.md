# Reproduce the integrated development pipeline

Updated 27 October 2026. Unit checks and development runs are distinct from a
reviewed research experiment. Track A review records are accepted on Varun's
attestations. Experiment annotations, model selection, complete series histories
and final episode acceptance remain open; see
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

New runs default to the selected BGE-M3 first stage with the pinned v7 FAISS
index. All retrieved conditions share this first stage; B1-R adds the pinned
cross-encoder over its top 50 eligible candidates. The original v1 BM25 runs
remain historical. D-02 is resolved by the receipt-bound retrieval pilot; the
end-to-end reranker comparison and D-01 model selection remain separate.

`make run-dev` and `make run-all-dev` use `.venv/bin/python` for a persistent
retrieval worker, keeping native retrieval dependencies outside the MLX runtime.
The cross-encoder worker also uses `.venv`. All workers are offline. Place the
corpus-matched vector file at
`data/interim/corpus_v7_index_20261026/bge_m3_vectors.json`, or set `DENSE_INDEX`.
Its embedding revision is `5617a9f61b028005a4858fdac845db406aefb181`; the reranker
revision is `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`. Both models must already
be present in `HF_HOME`. Select another first stage explicitly with `RETRIEVER`;
new settings require a new output directory.

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

The separate `data/series/retrospective_20261025/` snapshot contains 317
observations, including unchanged CPI/FX copies. Its four newly imported histories
have October capture-date availability. The default store ignores this nested
directory. Its README records public sources, measurement differences and replay
commands. Verify the actual stored files and absence of historical leakage with:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.validate_retrospective_series \
  --report reports/retrospective_read_layer_recheck.json
MPLCONFIGDIR=/private/tmp/lma-matplotlib PYTHONPATH=src .venv/bin/python \
  -m scripts.plot_series_coverage --output reports/series_coverage_recheck
```

Post-capture analysis must explicitly select that directory. It cannot supply
missing information to the frozen March–September runs or independently confirm
daily anchor episodes from monthly data.

## Run and resume

```sh
UV_NO_SYNC=1 UV_CACHE_DIR=/private/tmp/lma-uv-cache make run-dev DEV_OUTPUT=runs/my-dev
UV_NO_SYNC=1 UV_CACHE_DIR=/private/tmp/lma-uv-cache make run-all-dev DEV_OUTPUT=runs/my-all-dev
```

The first command runs B0/B1/B2/M; the second runs all seven conditions. The
default output directories are `runs/local-v7-dev` and `runs/local-v7-all-dev`,
respectively. Use the same command and output directory for resume.
Each query/condition gets a validated graph, provisional established-edge IDs,
raw candidates, optional prose answer, and a separate append-only event log.
Actual prompts, completions, token counts and call wall times are recorded.
Graph output is written only after a completed run. Failed attempts retain their
logs and are listed separately. Resume checks all ten runtime packages
(including retrieval, corpus and schema code/resources), exact local generator files, runtime package versions, selected
retriever/index, aliases, series, queries and model settings. Saved artifacts and
their successful execution logs have checksum receipts. Changed or legacy
unbound output is rejected; start a new directory rather than relabelling it.

`make run-dev` requires Metal access and downloaded weights; it is not a fixture
substitute for a research sweep. `--backend llama.cpp` and `--backend vllm` accept
an explicitly configured local `/v1` chat endpoint. Remote endpoints require
`--allow-remote`; no paid fallback occurs automatically. Native HTTP backends
are transport adapters and have not been validated on Kaggle in this session.

## Anchor checks

Every mapped anchor triggers a logged `get_series` lookup within the common
12-call budget, including B0. Supplied `confirmed_by_series` flags are discarded.
Confirmation requires a query's explicit `anchor_window` with exact `start` and
`end` observation dates; `end` must equal `anchor.event_date`. Both endpoints
must be published by `as_of`, match the declared direction and satisfy any
`minimum_absolute_change` or `minimum_percent_change` magnitude thresholds.
Recorded observations include availability dates, units and source URLs.

Without an explicit window the seven-day lookup is diagnostic and cannot confirm
an event. Empty, delayed or missing endpoints leave the anchor unconfirmed;
non-series policy announcements need separate episode evidence. No causal link
is established by a series move. `--require-confirmed-anchors` rejects
unconfirmed events before generation. Existing development candidates remain
unreviewed; they are not silently converted into confirmed study episodes.

## Audit, review and figures

The auditor checks the full condition/query matrix recorded in `inputs.json`,
artifact/log checksums, identities and call counts. Empty, incomplete, malformed
or unexpected runs fail with a nonzero exit status. `--allow-partial` explicitly
permits inspection of a partial/legacy run but never certifies completion.
Legacy runs need `--conditions ... --queries ...` for a declared matrix.
Compute for new runs uses only logs bound to completed artifacts; extra failed
or retry logs are listed separately and excluded from those totals.

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

### Source-audited development seeds — 25 October

A separate Codex audit read all 43 existing seed paragraphs against their fixed
questions. It retained 37 direct answers, rejected four outcome/background-only
seeds and left two unresolved-context seeds uncertain. All 20 questions retain
positive evidence. This is **not independent human annotation** and covers only
the pre-existing seeds, not the full pooled candidates. The human packet and
acceptance requirements remain unchanged. The local Qwen pool-classification
attempt was stopped after source-audited false positives; none of its labels
entered the new pair file. See `reports/relevance_screen_failure_audit_20261025.json`.

Replay the recorded source judgments into fresh files:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.audit_retrieval_seeds \
  --output reports/retriever_audited_seed_recheck.jsonl \
  --report reports/retriever_seed_audit_recheck.json
```

Run the four configurations/reranker with the preceding command, replacing
`--pairs` with the new file and selecting a new `--output`. Keep `--smoke`:
this audit cannot create a human review receipt or resolve research D-02/D-03.
The recorded result is `reports/pilot_retriever_v3_audited_seeds_20261025.md`.

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

## Historical v3 independent-review workspace

Build a new reviewer folder from the preserved v3 snapshot and existing blank
sample/relevance packets. This operation is local and copies no seeds, ranks,
scores or private condition mapping into reviewer materials:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.prepare_track_a_review \
  --snapshot data/interim/frozen_v3_20261026 \
  --output data/interim/track_a_review_recheck \
  --report reports/track_a_review_recheck.json
```

Open `START_HERE.md`, then `01_corpus/Review.html` in a browser. Cached HTML
originals render in a sandbox without scripts or external assets; PDFs remain
checksummed local files. The page saves `corpus_judgments.json` for progress and
resumption. After an independent human completes every check and their own
identity/date/independence/acceptance record, validate that file:

```sh
PYTHONPATH=src .venv/bin/python -m corpus.review export \
  --snapshot data/interim/frozen_v3_20261026 \
  --packet data/interim/track_a_review_delivery_20261023/01_corpus/packet.json \
  --judgments /path/to/completed_corpus_judgments.json \
  --output data/interim/corpus_sample_v3_accepted
```

This receipt covers only the fixed 73-item extraction sample. It does not grant
redistribution rights or certify source balance/full extraction coverage. Stale
corpus/parent/packet/text hashes, missing/rejected/duplicate rows, future review
dates and absent or non-independent attestations are rejected before output.
The actual blank packet was confirmed to fail.

After corpus acceptance, a reviewer blinded to retrieval results uses
`02_relevance/Review.html`, saves `relevance_judgments.json`, and returns it for
validation. The following requires their complete real judgments, including all
20 query suitability checks and exact spans for relevant passages:

```sh
PYTHONPATH=src .venv/bin/python -m retrieval.review export \
  --packet data/interim/track_a_review_delivery_20261023/02_relevance/packet.json \
  --judgments /path/to/completed_relevance_judgments.json \
  --corpus data/interim/frozen_v3_20261026/articles.jsonl \
  --output data/interim/retrieval_v3_accepted
```

Use that export's pairs/receipt for a reviewed pilot following
`reports/retrieval_review_workflow.md`. Do not replace the placeholders with
machine-produced judgments or prefill human attestations. Existing experiments
still use v1 and their separate correction/support packets.

## Completed development source review — 25 October

`reports/track_a_source_review_20261025.json` contains the actual Codex decisions
for all 73 corpus samples and 2,062 pooled items. Exact evidence offsets and
text hashes refer to the original v3 packet. Revalidate coverage, dates, raw
originals and unchanged independent-review files with the local source caches:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.validate_source_review \
  --snapshot data/interim/frozen_v3_20261026 \
  --output /private/tmp/track_a_source_review_recheck.json
```

The original reviewer-delivery hashes must match. This validator checks record
integrity, not the correctness or independence of judgments; it creates no
human receipt. Uncertain labels are unresolved, not negatives. Findings and
inspection limits are in `reports/track_a_source_review_20261025.md`.

The HTML repairs can be replayed offline into a fresh candidate directory:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.apply_source_review \
  --snapshot data/interim/frozen_v3_20261026 \
  --output data/interim/corpus_source_review_recheck \
  --report /private/tmp/corpus_source_review_recheck.json
```

This needs all original news caches and the optional extraction dependencies.
It checks raw checksums, publication identity, every passage offset and a
reverse-order freeze. It preserves archived v3 and cannot promote the candidate or migrate index/review
identities. The historical 25 October v4 candidate had 1,159 documents and 29,595
passages. Replaying with the current parser creates a new candidate; it does not
reproduce historical parser bytes. Use the finalizer below for the current
narrative PDF scope and final v7 payload.

## Current v7 Track A delivery — 26 October

Active corpus: `data/processed/articles.jsonl`, SHA
`25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496`.
Its manifest declares narrative-only PDF scope. Originals and table/fragment
layout audits stay local. The old v3 snapshot is preserved at
`data/interim/frozen_v3_20261026/`; v1 experiments still require their own corpus.
Source policies and series limitations are in
`reports/track_a_source_scope_20261026.md` and
`reports/track_a_series_scope_20261026.json`.

Rebuild a new candidate from preserved v3 inputs and checksummed raw caches:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.finalize_track_a_corpus \
  --snapshot data/interim/frozen_v3_20261026 \
  --output data/interim/v7_rebuild \
  --report /private/tmp/v7_rebuild.json \
  --version v7-narrative-development
```

The corpus/archive payload hashes are reproducible. The active manifest also
contains the delivery scope note. This does not grant redistribution rights or
certify research acceptance. PDF/extraction versions used were PyMuPDF 2.0 and
trafilatura 2.3.1. The final parser removes marked related links by character
ranges before extraction and preserves all other HTML unchanged.

The saved index is
`data/interim/corpus_v7_index_20261026/bge_m3_vectors.json`.
Use a fresh output path for an offline rebuild. Only exact title+text hashes
with the same model/preprocessing identity may reuse vectors:

```sh
HF_HOME="$PWD/data/raw/model_cache" HF_HUB_OFFLINE=1 PYTHONPATH=src \
.venv/bin/python -m scripts.build_track_a_index \
  --corpus data/processed/articles.jsonl \
  --output data/interim/v7_index_rebuild \
  --seed data/interim/corpus_v7_index_20261026/bge_m3_checkpoint.json \
  --report /private/tmp/v7_index_rebuild.json
```

The completed pool review is `reports/retriever_v7_full_review_20261026.json`.
Exact spans refer to `data/interim/retrieval_v7_review_20261026/packet.json`.
The 195 positive query/passage judgments are grouped into 20 queries in
`reports/retriever_v7_pairs_20261026.jsonl`. Replay the real comparison:

```sh
HF_HOME="$PWD/data/raw/model_cache" HF_HUB_OFFLINE=1 PYTHONPATH=src \
.venv/bin/python -m retrieval.pilot_runner \
  --pairs reports/retriever_v7_pairs_20261026.jsonl \
  --corpus data/processed/articles.jsonl --smoke \
  --dense-index data/interim/corpus_v7_index_20261026/bge_m3_vectors.json \
  --dense-backend faiss --device cpu --embedding-batch-size 8 \
  --max-length 1024 --local-files-only \
  --embedding-revision 5617a9f61b028005a4858fdac845db406aefb181 \
  --rerank --reranker-revision 953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e \
  --output /private/tmp/v7_pilot_replay.md
```

`--smoke` is intentional: complete development-pool labels do not carry
independent human acceptance. The development selection is recorded in
`reports/track_a_retrieval_selection_20261026.json`. It does not change archived
v1 runs or establish end-to-end research benefit.

Independent review uses
`data/interim/track_a_review_delivery_v7_20261026/START_HERE.md`.
Read `SCOPE.md`; review the 73 source samples and 2,035 pooled candidates.
Supply actual independent judgments/attestations. The old v3 packet and all
83 files remain unchanged; neither its receipt nor Codex judgments can be used
as independent acceptance for new text. The new 82-file delivery has blank forms.
To rebuild it into a new directory:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.prepare_track_a_review \
  --snapshot data/processed \
  --sample data/interim/corpus_v7_20261026/extraction_judgments.json \
  --retrieval data/interim/retrieval_v7_review_20261026 \
  --output data/interim/track_a_review_v7_recheck \
  --report /private/tmp/track_a_review_v7_recheck.json
```

Use the corpus/relevance export commands above with the v7 delivery paths and
`data/processed` as the snapshot. Export only genuine completed human forms.
The actual blank exports were rejected before creating any output.

With the local payloads, vectors, review workspaces and series present, check
all final development bindings:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.validate_track_a_delivery \
  --output /private/tmp/track_a_delivery_recheck.json
```

This checks bytes, offsets, label coverage/spans, dates, index identity, series
hashes and blank human forms. It certifies integrity, not semantic correctness,
independence, source permissions or research acceptance. Fresh setup, source
replay and runtime details are in `reports/track_a_clean_reproduction_20261026.json`;
the final integrity result is `reports/track_a_validation_20261026.json`.

## Follow-up official source audit — 26 October

With the separately cached public SEBI listing and seven annexures, audit
source hashes, dynamic FPI table identity, native USD labels, arithmetic and
publication/file-version dates:

```sh
python3 scripts/audit_sebi_fpi.py \
  --raw data/raw/track_a_followup_20261026 \
  --output /private/tmp/sebi_fpi_vintage_recheck.json
```

The actual source read used the bundled Python runtime. The importer itself
uses only Python standard-library ZIP/XML support; it does not need a workbook
application or execute macros/formulas. Table ordinals change between issues,
so the title and native USD column are validated. Known later versions and
invalid downloaded copies are excluded. Missing or formula-error values never
become zero. These are broader total-FPI candidates (including mutual funds),
kept outside the existing canonical series. No corpus, index, pair, human
judgment or previous experiment payload is changed by this command.

The primary ATF/August MPC web checks, collector failures and all-61-official-PDF
metadata audit are recorded in `reports/track_a_followup_20261026.json`. Web
readability does not imply acquisition of a checksummed original for the corpus.
Current 637-test local/fresh checks are separate from the earlier 630-test
rebuild receipt; see `reports/track_a_followup_validation_20261026.json`.


## 27 October user-attested Track A review

The user identifies the reviewer as Varun, supplies 27 October 2026 as the date,
and explicitly declares independent review and blinding to results. Completed
records are in `data/interim/track_a_attested_review_20261027/assessment/`, with
corpus and retrieval receipts in `corpus_accepted/` and `relevance_accepted/`.
Original blank workspaces and earlier rejected submissions remain unchanged.

The completed records preserve every original development decision and evidence
span. The software checks packet/corpus hashes, coverage, dates, exact spans and
recorded declarations. It does not authenticate identity or independently verify
review conduct or timing of results exposure. See
`reports/track_a_reviewer_identity_20261027.json` for exact declarations, file
hashes, acceptance scope and limits.

For a receipt-bound comparison, use the v7 replay command above with:

- `--pairs data/interim/track_a_attested_review_20261027/relevance_accepted/pairs.jsonl`
- `--review-receipt data/interim/track_a_attested_review_20261027/relevance_accepted/receipt.json`
- omit `--smoke` and choose a fresh report output.

The resulting report is `reports/pilot_retriever_v7_attested_20261027.md`.
Earlier smoke reports retain their original provenance and are not overwritten.
This review does not accept baseline corrections, support labels or final UER.

## 27 October integration fixes

All five original code findings are repaired. The current suite passes 663 tests,
Ruff and Black. A new wheel loads its default alias table and passes an actual
rule check from outside the repository in Python isolated mode. The packaged
alias bytes match the tracked table. The run command now selects BGE-M3 and
uses the provenance, completeness and anchor checks documented above.

See `reports/integration_fixes_20261027.md` and its JSON evidence. The original
641-test audit and earlier reproduction reports retain their historical scope;
they are not current implementation instructions or reviewed research results.
