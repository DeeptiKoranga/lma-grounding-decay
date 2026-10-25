# Track A delivery status — 25 October 2026

The local corpus, retrieval and series implementation is delivered and verified.
**Track A research acceptance is still incomplete.** Independent reviewers are
unassigned, required source balance is not met, and original point-in-time series remain sparse.
This report replaces the older continuation status; it does not close research
issues or record team/TA approval.

## Delivered locally

| Work | Current evidence | Remaining acceptance requirement |
|---|---|---|
| News/official collection (A1–A2) | 1,177 retained documents: 1,116 news and 61 official, March–September. ET 889, BusinessLine 215, Mint 12; MoSPI 37, PPAC 14, OEA 10. Mint now covers all seven months. | Business Standard and RBI remain absent after access failures. ET dominates; Mint is sparse. OEA is a documented source-list deviation. |
| Parsing, deduplication, freeze and offsets (A3–A5) | Repaired invisible-format-character matching and omitted visible article leads. Reparsed 1,112 original news caches; restored 1,572 paragraphs in retained documents. Removed explicit related links and six additional same-day near duplicates. All 28,391 passage offsets match saved parent text; reverse-input archive is identical. | The 73-item extraction/source review is blank. Residual recommendations and PDF table/header quality need independent acceptance. |
| Lexical, dense, hybrid and date filtering (A6–A7, A11) | Plain/alias BM25, pinned BGE-M3, FAISS and RRF implemented. All 28,391 passages indexed. Saved index reloaded in a fresh process and searched at March and September cutoffs. Future documents are excluded before ranking. | Accepted corpus and retriever choice; broad aliases and source concentration remain limitations. |
| Retrieval/reranking pilot (A8–A9, #45) | Real four-way comparison and pinned top-50 cross-encoder on 20 machine-curated questions across all seven months, with 43 unchanged seed texts. A new 2,062-item blinded packet is ready. | Independent relevance judgments, corpus acceptance, D-02 and D-03. Smoke scores do not establish research performance. |
| Macro-series store (A10) | Original store: CPI 7, FX 141, basket 2, Brent 4, benchmark yield 6, FPI 1; **161 observations unchanged**. Separate retrospective snapshot: **317 observations**, with March–September Brent daily closes and monthly basket/yield/FPI. Actual read-layer checks reject October snapshots at September cutoffs. | Original-vintage histories and anchor confirmation remain incomplete. Retrospective financial-futures closes and monthly main yields have different definitions from the dated news points. Monthly values cannot confirm daily episode dates. |
| Integration and reproduction (#33, #50) | All six development candidates rerun from fresh-clone source for B0/B1/B2/M: **24/24 canonical graphs match** the earlier v1 checkpoint. Prompt/model/tool/budget/corpus logs checked. Corpus binding now rejects v3 text for old v1 runs. | These are unreviewed candidates and reused local weights/runtime. Other team machines, Kaggle and accepted gold remain untested. |
| Figures/report (#46) | Source-by-month and series-coverage PNG/SVG, retrieval comparisons, provenance, computation and review handoff are saved. | Final UER, reference recall and strength figures require independent labels and corrected baseline graphs. |

## Corpus and experiment versions

`data/processed/` is now **v3 development**, not a research-accepted freeze:
`1df503a6101471a8646f6521f7c44ffbd946661ea79e63057f1bedf06c2a9164`.
The full candidate snapshot also remains under `data/interim/corpus_v3_20261023/snapshot/`.

The earlier 42-graph seven-condition assembly and the fresh 24-graph reproduction
use **v1**, preserved at `data/interim/frozen_v1_20261023/`, corpus SHA
`7b843fe072573fe7b3d54f89af6b2128bf61abe4115b4059d57665e9638543d3`.
Their original three series are preserved separately at
`data/interim/fresh_reproduction_inputs_20261023/series/`.
Never pool these outputs with new v3 experiments or attach v3 passages to their
review packets. Run audit and both review preparers enforce recorded hashes.
The intermediate v2 corpus and its older review packet are historical checkpoints.

## Retrieval evidence and review

`reports/pilot_retriever.md` and `reports/pilot_retriever_v3_development.md`
now describe v3. First-stage Recall@10 on **incomplete machine seeds** is 0.4333
for BM25, 0.5167 for alias BM25, 0.6000 for BGE-M3 and 0.5833 for hybrid RRF;
dense plus reranking gives 0.7667. These are development diagnostics, not accepted
relevance scores. They do not justify resolving D-02/D-03 or switching the
shared development first stage from plain BM25. The old March comparison is
preserved as `reports/pilot_retriever_march_20261022.md`.

Current packet: `data/interim/retrieval_review_temporal_v4/`. Its 20 questions
have three cutoffs per month March–August and two in September. All 43 seed texts
and every four-way pooled candidate are retained. Scores, ranks, origins and
seed flags are hidden. All judgments and attestations are blank; an actual blank
export was rejected without producing output. Corpus review must precede final
relevance acceptance. See `reports/retrieval_v3_review_readiness.json`.

## Verification and handoff

Latest local checks: **620 tests passed**, Ruff and Black passed. The earlier clean clone at `57c0480` passed **584 tests with two optional PDF
skips**; current review-workflow validation is recorded in
`reports/track_a_review_validation.json` (598 passed and two optional PDF skips
at source `80a6d7a`). The real saved-index
reload passed; all 24 fresh graphs match. Fifteen quotation failures in the
original seven-condition baseline/ablation outputs remain visible for independent
correction; exact reproduction does not validate their support. No UER, human
agreement or reference recall is claimed.

The 25 October clean clone of source `a27e8e0` passed **618 tests with two optional
PDF skips**, with Ruff/Black clean and imports verified from the new checkout.
It validated all tracked snapshot files without raw caches. This reused the
core environment and does not certify a fresh heavy install or other machines.
Current evidence is in `reports/track_a_validation_20261025.json`.

Key records:

- `reports/corpus_v3_audit.json`, `reports/corpus_v3_extraction_qa.json`,
  `reports/corpus_versions.json`, `data/processed/MANIFEST.md`.
- `reports/retrieval_v3_saved_index_validation.json`,
  `reports/retrieval_v3_review_readiness.json`, `reports/retriever_temporal_v3_migration.json`.
- `data/series/README.md`, `reports/news_series_v3_acquisition.json`,
  `reports/series_store_validation.json`.
- `reports/fresh_full_development_reproduction.json`,
  `reports/fresh_full_development_logs.json`, `reports/corpus_binding_validation.json`.
- `reports/review_handoff.md`, `docs/reproduction.md`, `reports/compute_log.md`.

The earlier work through `c01d222` is on GitHub branch `varun`. The 25 October
data/source additions are committed locally at `a27e8e0` and documented below.
They have not been pushed. No pull request, issue closure, teammate
acceptance or research signoff is implied by the development delivery.

## Ready-to-use independent review workspace

Open `data/interim/track_a_review_delivery_20261023/START_HERE.md`.
`01_corpus/Review.html` contains the 73 sampled documents and all 73 checksummed
cached originals. `02_relevance/Review.html` contains the unchanged blinded
20-question, 2,062-passage packet. Both pages work locally, keep attestations
blank, and save/resume reviewer progress. The actual browser download and resume
were checked without adding any human judgments.

`corpus.review` now validates extraction sample acceptance against corpus,
parent, packet and judgment hashes. Missing, rejected, duplicate, stale or
non-independent review fails before a receipt is created. Acceptance covers the
specified sample; it does not certify source balance, all documents or sharing
rights. The relevance exporter retains its separate complete/blinded review gate.
Commands are in `docs/reproduction.md`.

The 23 October checks admitted no new data; their historical record remains
`reports/track_a_remaining_source_gaps.json`. On 25 October, public Yahoo,
FRED/OECD, PPAC and existing CDSL caches supplied the separate retrospective
histories. New Business Standard/RBI/FBIL checks remain unsuccessful, documented
in `reports/track_a_source_gaps_20261025.json`. No reviewer was assigned and no
human receipt was created.

## 25 October source audit and backfills

The 43 existing retrieval seeds were checked directly against their fixed
questions and isolated source paragraphs. The separate Codex audit retained
**37 relevant**, rejected **four irrelevant** and left **two uncertain** seeds.
Every question retains evidence; exact spans and reasons are in
`reports/retriever_seed_audit_20261025.json`. This is development curation, not
independent human review or full-pool relevance acceptance. The original pairs,
corpus, review packet and human judgments are unchanged. The follow-up pilot is
`reports/pilot_retriever_v3_audited_seeds_20261025.md`; D-02/D-03 remain open.
The recorded CPU/FAISS rerun took 145.04 seconds with the saved v3 index. Recall@10
was 0.4333 BM25, 0.4917 alias BM25, 0.6000 dense and 0.5583 hybrid; dense plus
top-50 reranking reached 0.7667. Dense remains the provisional simplest option
within 0.03 of the best. Seed curation is incomplete pool coverage and supplies
no human receipt; the existing shared development runs/settings are preserved.

The local Qwen classifier was stopped after 11 completed batches/313 items:
source inspection found it accepting generic background as direct answers.
All its outputs are excluded from pilot labels. Formatting and verbatim spans
alone cannot establish relevance. Actual usage, failed attempts and source-audit
examples are in `reports/relevance_screen_failure_audit_20261025.json`.

The new retrospective store and actual date-filter checks are documented in
`data/series/retrospective_20261025/README.md`,
`reports/retrospective_series_acquisition_20261025.json` and
`reports/retrospective_series_read_validation_20261025.json`.
An offline replay into a fresh directory reproduced all six CSV hashes. The
coverage figure `reports/series_coverage_20261025.png` was visually checked.
