# Whole-project and Track A audit — 27 October 2026

**The full project is not complete or fully connected.** Track A's standalone
components work within the declared data scope, but five integration or
reproduction gaps remain. Two additional Track A code defects were reproduced
and fixed during this audit. The earlier scoped handoff did not establish
completion of Track A's shared Phase 2–4 obligations.

This audit starts from `d07ad4dd484012c3187fdac84b7d6bb9be50f5ea`. It inventories
all 143 previously tracked Python files, checks all 99 source/script modules,
traces the collection-to-evaluation paths, and checks the plan's required
artifacts. A new regression file brings the working tree to 144 Python files.
It combines source review, imports, command startup, the full test suite,
targeted failure probes, actual cached retrieval and an isolated package install.
These checks are not a proof of every possible runtime path or scientific claim.

## Open implementation findings

### F1 — P1: the chosen retriever is disconnected from the conditions command

`src/conditions/__main__.py:96` still records “plain BM25 … D-02 unresolved”,
and lines 115–117 construct `PlainBM25` directly. The command has no
`--retriever`/dense-index selection options. Thus `make run-dev` and
`make run-all-dev` do not run the BGE-M3 configuration selected by Track A.
B1-R also reranks that hard-coded first stage rather than the selected dense one.

The underlying interface works: a new probe injected real pinned BGE-M3/FAISS
and the pinned reranker into the shared pipeline for all seven conditions. That
test used a synthetic empty-edge generator and is not a model experiment.
**Required fix (A+C, C entry point):** consume the selected configuration and
pinned index/model settings consistently in the runner, record their hashes,
and run a new smoke sweep. Preserve historical v1 outputs and settings.

### F2 — P1: anchor confirmation never reaches the series tool

`src/conditions/pipeline.py:69` copies the supplied anchor into the graph. There
is no `get_series` call in the pipeline or controller. A probe supplied
`confirmed_by_series: true` with an empty series store: all seven conditions
preserved that flag, and the store received **zero requests**. The six current
development candidates correctly remain marked unconfirmed, so this audit does
not claim they already contain false confirmations.

**Required fix (B+C, with A's series interface):** add explicit confirmation or
require reviewed, evidence-bound anchor records before accepting confirmation
flags. Define observation windows and exact measures; do not infer a daily
threshold from monthly data, or a policy announcement from a price series.
Confirm, drop or redate unsupported episodes. `data/eval/episodes.md` is absent.

### F3 — P2: resume can reuse outputs after Track A code changes

`src/conditions/__main__.py:84` hashes agent/conditions/extract/LLM/tools/verifier
code but omits `src/retrieval`, `src/corpus` and `src/schema`. A temporary-source
probe replaced the retrieval implementation with an empty-result backend. The
recorded pipeline hash stayed unchanged and `--resume` reused the old graph.
No workspace source or historical run was changed by that probe.

**Required fix (C):** bind resume to all participating code, ontology and runtime
settings, and verify cached artifact identity. Evidence:
`whole_project_resume_probe_20261027.json`.

### F4 — P2: the run audit does not establish sweep completeness

`src/eval/run_audit.py:17` accepts an empty run directory and returns zero
graphs, an empty condition map and `failures: []`; its command completes
successfully. It also has no expected query-by-condition coverage requirement.
A structurally valid partial sweep can therefore have no listed failures.

**Required fix (C):** distinguish partial inspection from a completeness gate;
reject empty runs and report missing/duplicate expected query-condition pairs
when validating a sweep. Evidence: `whole_project_probes_20261027.json`.

### F5 — P2: installed verifier cannot locate its default alias data

The wheel builds and all 65 core modules import in an isolated environment.
However, `verify.aliases.ALIASES_PATH` resolves outside the installed package
to `lib/python3.12/data/aliases.yaml`, which is absent. Calling the default
loader raises `FileNotFoundError`. Passing the tracked YAML explicitly works.
`Verifier.verify` in `src/verify/llm_verifier.py:41` always uses the default rule
loader, so the runner's `--aliases` selection is not passed through either.

**Required fix (B+C/shared packaging):** package the alias resource with a stable
resource path, or pass one explicit alias configuration through retrieval and
verification. Repository/editable execution works; a built wheel alone is not
a complete verifier installation. Evidence: `whole_project_install_probe_20261027.json`.

## Track A repairs completed in this audit

- **A1 batch restart:** `scripts/fetch/news_batch.py` applied its monthly limit
  before removing cached articles. Once that first cohort was cached, repeated
  runs attempted nothing. It also skipped orphaned metadata without a payload.
  The limit now applies after complete-cache filtering. Two real command-path
  regression cases failed before the fix and pass afterwards. No new articles
  were acquired and no frozen corpus changed.
- **A8 review chronology:** retrieval exports and loaded receipts accepted
  future review dates, unlike the existing corpus-review gate. `ReviewReceipt`
  now rejects them. Export-before-write and receipt-load regression cases both
  failed before the fix and pass afterwards. Varun's 27 October receipts remain
  valid; judgments, spans and attestations were not changed by this audit.
- **A8 report entry point:** the plan's `reports/pilot_retriever.md` now links
  the current receipt-bound comparison and selection before its preserved
  historical development report. Old smoke provenance is not relabelled.

## Every Track A task in PLAN_MIDSUB.md

| Task | Implementation and verification | Current disposition |
|---|---|---|
| A1 collectors | Four publisher definitions; bounded robots/redirect/pacing client; sitemap/RSS/Atom discovery; raw checksums; corrected resumable batching | Implemented. Acquired news: ET 870, BusinessLine 213, Mint 12; Business Standard absent. Source balance remains a declared deviation. |
| A2 official fetcher | Audited release metadata, HTML/PDF handling, version checks and original caches | 61 retained official documents: MoSPI 37, PPAC 14, OEA 10. RBI/PIB corpus coverage absent; OEA differs from original source list. Delivered with deviations, not full original coverage. |
| A3 parser/normaliser | HTML extraction, publication eligibility, scope screen and narrative PDF finalizer; Passage validation | Working for the final scoped v7 snapshot. Generic ingestion is not a substitute for the documented narrative finalization steps. |
| A4 dedup/freeze/manifest | Deterministic title/lede MinHash with exact Jaccard confirmation, exact-text dedup, stable archive and source/month/licence notes | 1,156 documents: 1,095 news and 61 official. Count targets met; source/extraction/redistribution limits retained. |
| A5 exact offsets | Parent documents retained; paragraph slicing and full integrity validation | All 16,472 passage offsets match exact parent text. |
| A6 BM25/aliases | Plain and expanded BM25; date-visible scoring population; tracked alias table | Component works. Default installed verifier alias path is F5. |
| A7 BGE/FAISS/RRF | Pinned BGE-M3, identity-bound vectors/checkpoints, eligible-only FAISS scoring and hybrid fusion | Component and actual cached-model searches pass. Runner selection remains disconnected: F1. |
| A8 20-query pilot | Four-way comparison, fixed selection rule, complete 2,035-item pool, 195 positive spans; user-attested records validate | BGE-M3 selected; Recall@10 0.4259. Future-date guard fixed. Actual experiment runner still needs F1. Review conduct is attested, not independently observed. |
| A9 reranker | Pinned top-50 cross-encoder, same queries/metrics | Recall@10 0.5296, gain 0.1037. Retrieval component works; full end-to-end B1-R benefit remains deferred as planned. |
| A10 six series/read layer | CSV units, finite values, vintages, publication availability and tool adapter validated | All six populated with 161 observations; four histories sparse. Separate 317-observation October snapshot is excluded at historical cutoffs. Anchor use remains F2/B2. |
| A11 date enforcement | Cutoffs before scoring/reranking, trusted-passage rechecks and tool cutoff pinning | Unit tests and actual BGE/reranker connector checks pass. No future passage returned in the probe. |

The supplied source/PDF and sparse-series scope was adopted for the scoped
mid-submission handoff. That disposition does not fill missing sources or
histories, grant publisher permission, or establish the original full-scope goal.

## Track A's later and shared obligations

| Plan item | What remains |
|---|---|
| 2.1 A+C retrieval wiring | Fix F1 and run the selected retriever through the actual conditions command. |
| 2.4 pilot decisions | Retriever choice recorded; reranker retrieval component complete. C2/D-01 model selection is still open. |
| 2.5 shared double annotation | No completed independent paired annotations or `reports/agreement.md`; Cohen's kappa cannot be invented. Track A corpus/retrieval review does not replace this. |
| 2.6 annotate ten test queries | The planned 30-query file and reviewed reference graphs are absent; the six candidate queries are not that deliverable. |
| 3.2 shared dev support review | Separate baseline correction and condition-blinded support judgments remain incomplete. |
| 3.5 retrieval table, A | Complete; the current canonical entry point links the receipt-bound v7 report. |
| 3.6 figures, A | Corpus/series figures and an explicitly unreviewed historical example exist. The headline UER-by-hop figure awaits corrected baselines, support judgments and reference graphs. |
| 3.7 shared failure analysis | Historical structural failure analysis exists; final reviewed/current-configuration case analysis still depends on the above. |
| 4.1 shared mid report | Working draft exists, but headline results and the incomplete items must still be completed or reported as deviations. |
| 4.3 fresh-clone reproduction, A | Current local suite and isolated wheel/component checks pass within the limits below. A full selected-configuration model run from a fresh checkout, and all-three-laptop verification, are not established. Fix F1/F3/F5 first. |

## Broader project against the plan

| Plan tasks | Current evidence / remaining work |
|---|---|
| Phase 0 contracts/fixtures | Schemas, ontology and generated fixtures exist; drift/contract tests pass. The gate on all three laptops is unverified. |
| B1 guide | Annotation guide exists. Agreement/results still need the separate annotation work. |
| B2–B4 episodes, 30 queries, dev gold | `episodes.md`, `queries.jsonl` and all dev reference graphs are absent. Only six unreviewed development candidates exist. |
| B5–B8 extractor/verifier/paths | Implemented and exercised by tests and historical development runs; F2/F5 affect readiness. Semantic performance still needs the planned pilot/review data. |
| B9–B10 challenge/public checks | Challenge builder exists, but the 125-item reviewed set is absent. No completed 200-item FinCausal/Yu strength/direction pilot or `pilot_strength.md`. |
| C1–C2 generation/model pilot | Local MLX and compatible HTTP adapters exist. No completed two-model/five-task pilot or `pilot_model.md`; remote backends have no accepted execution evidence. |
| C3–C6 tools/controller/conditions/logs | Implemented; all seven share one pipeline. F1–F3 remain. Historical real-model outputs use archived v1, not the current selected v7 configuration. |
| C7–C8 metrics/statistics | Implemented, with null-denominator and review guards. No accepted UER/strength/reference-recall results to compute yet. |
| C9–C10 capability/safety | Frozen synthetic fixtures and diagnostic runs exist. Twenty fault cases pass; earlier model action choice was only 5/40. Text safety screening is heuristic, with independent adjudication pending. |
| C11 notebook/compute | Compute log exists. Kaggle notebook is an unexecuted handoff template; no Kaggle GPU execution is established. |
| Phase 2 smoke/annotation | Historical development runs exist. A new selected-configuration smoke and the missing annotation/reference artifacts remain. |
| Phase 3 results | UER, strength inflation, paired contrasts, recall guard and final result figures remain blocked by model/annotation/anchor/integration work. |
| Phase 4 freeze/write | README/report drafts exist. Final results, reproduction and team/TA decisions remain. The 30 October tag is not due yet; no tag or PR is created by this audit. |

## Checks executed and their limits

- **641 tests pass**, Ruff and Black pass. Four new regression cases verify the
  two repaired defects. The baseline was 637 passing tests.
- **All 65 core modules import** in the workspace and from the built wheel in a
  separate environment using Python isolated mode. All **43 argparse entry
  points** start successfully with `--help`; no missing internal imports or
  Python syntax errors were found. Startup is not a full run of every command.
- A real BGE-M3/FAISS/reranker connector probe completed all seven conditions in
  **23.70 seconds**, with date-eligible retrieval. Its generator deliberately
  returned empty graphs; it tests connections, not answer quality or final UER.
- The earlier receipt-bound 20-query comparison remains unchanged at 153.84
  seconds and the documented scores. It is not an end-to-end explanation run.
- A fresh wheel was built and installed with only the core dependencies.
  Fixture retrieval, all six series, ontology loading and Varun's accepted
  receipt validate; default verifier alias loading fails as described in F5.
  Initial dependency-cache failures were resolved using a fresh temporary cache.
- The final corpus/index/archive, all offsets, 82 current blank-review workspace
  files, 83 historical workspace files, accepted review records and both series
  stores are checked separately. They are not modified by this audit.
- Remote model services, Kaggle, other team laptops, publisher availability,
  exhaustive semantic correctness and a new real-model v7 sweep were not tested.

Evidence files: `whole_project_inventory_20261027.json`,
`whole_project_probes_20261027.json`, `whole_project_resume_probe_20261027.json`,
`whole_project_real_retrieval_probe_20261027.json`,
`whole_project_install_probe_20261027.json` and
`whole_project_validation_20261027.json`.

## Next work in dependency order

1. Resolve F1–F5 in the responsible integration/shared modules. The Track A code
   fixes above are already complete. `CONTRIBUTING.md` assigns the remaining
   affected modules to B/C/shared ownership; this audit does not silently edit
   those modules or send external messages.
2. Complete model selection and reviewed episodes/queries/reference graphs.
3. Run the selected configuration, correct prose baselines, and obtain the
   separate support/double-annotation judgments.
4. Produce UER/strength-by-hop, recall guard, agreement and final figures; then
   complete fresh-checkout/team reproduction and the mid report.

No remaining reviewer identity/date/independence field is being requested for
Track A: Varun's declarations are recorded and the current review receipts pass.
