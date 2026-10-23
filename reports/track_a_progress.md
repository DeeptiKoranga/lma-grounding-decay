# Track A delivery status — 23 October 2026

The local corpus, retrieval and series implementation is delivered and verified.
**Track A research acceptance is still incomplete.** Independent reviewers are
unassigned, required source balance is not met, and several series remain sparse.
This report replaces the older continuation status; it does not close research
issues or record team/TA approval.

## Delivered locally

| Work | Current evidence | Remaining acceptance requirement |
|---|---|---|
| News/official collection (A1–A2) | 1,177 retained documents: 1,116 news and 61 official, March–September. ET 889, BusinessLine 215, Mint 12; MoSPI 37, PPAC 14, OEA 10. Mint now covers all seven months. | Business Standard and RBI remain absent after access failures. ET dominates; Mint is sparse. OEA is a documented source-list deviation. |
| Parsing, deduplication, freeze and offsets (A3–A5) | Repaired invisible-format-character matching and omitted visible article leads. Reparsed 1,112 original news caches; restored 1,572 paragraphs in retained documents. Removed explicit related links and six additional same-day near duplicates. All 28,391 passage offsets match saved parent text; reverse-input archive is identical. | The 73-item extraction/source review is blank. Residual recommendations and PDF table/header quality need independent acceptance. |
| Lexical, dense, hybrid and date filtering (A6–A7, A11) | Plain/alias BM25, pinned BGE-M3, FAISS and RRF implemented. All 28,391 passages indexed. Saved index reloaded in a fresh process and searched at March and September cutoffs. Future documents are excluded before ranking. | Accepted corpus and retriever choice; broad aliases and source concentration remain limitations. |
| Retrieval/reranking pilot (A8–A9, #45) | Real four-way comparison and pinned top-50 cross-encoder on 20 machine-curated questions across all seven months, with 43 unchanged seed texts. A new 2,062-item blinded packet is ready. | Independent relevance judgments, corpus acceptance, D-02 and D-03. Smoke scores do not establish research performance. |
| Macro-series store (A10) | All six files populated: CPI 7, FX 141, Indian basket 2, Brent 4, benchmark GSEC yield 6, FPI 1; **161 observations**. Exact provenance, availability filtering and strict news import checks are recorded. | Complete histories and anchor-episode confirmation. Basket is monthly; Brent is intraday front-month futures; yields identify two benchmark securities; FPI has one completed-month news vintage. No interpolation or invented roll date. |
| Integration and reproduction (#33, #50) | All six development candidates rerun from fresh-clone source for B0/B1/B2/M: **24/24 canonical graphs match** the earlier v1 checkpoint. Prompt/model/tool/budget/corpus logs checked. Corpus binding now rejects v3 text for old v1 runs. | These are unreviewed candidates and reused local weights/runtime. Other team machines, Kaggle and accepted gold remain untested. |
| Figures/report (#46) | Source-by-month coverage PNG/SVG, retrieval comparison, provenance, computation and review handoff are saved. | Final UER, reference recall and strength figures require independent labels and corrected baseline graphs. |

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

Local checks: **586 tests passed**, Ruff and Black passed. The refreshed clean
clone at `57c0480` passes **584 tests with two optional PDF skips**, plus lint and
formatting. The real saved-index
reload passed; all 24 fresh graphs match. Fifteen quotation failures in the
original seven-condition baseline/ablation outputs remain visible for independent
correction; exact reproduction does not validate their support. No UER, human
agreement or reference recall is claimed.

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

The work remains local. The mid-submission draft records these limitations;
no issue closure, remote publication, teammate acceptance or research signoff
is implied by this delivery.
