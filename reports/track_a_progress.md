# Track A delivery status — updated 27 October 2026

The remaining local engineering, corpus repair, development review, indexing,
retrieval comparison and reproduction work is complete. The final v7 delivery
has **1,156 documents and 16,472 passages**, **2,035 completed development
judgments**, a matching dense index and a new independent-review workspace.
The **scoped mid-submission development handoff is closed** under the
[27 October scope disposition](track_a_mid_submission_scope_20261027.md): the
available source mix, narrative-only PDFs and sparse historical series are
delivered with explicit deviations. **Research acceptance remains pending**:
no independent human review, source permission or original-vintage episode
confirmation is invented. This report
replaces the 25 October status, preserved as `track_a_progress_20261025.md`.

## Human expert review update — 27 October

The user reports completing Track A review only, with the expected outcome.
The earlier interpretation that the review included experiment results was
incorrect; no main hypothesis or Track B/C conclusion is claimed here.

The user supplied `corpus_judgments.json`, `relevance_judgments.json`,
`provenance.json` and `review_notes.md`, and confirmed these are the intended
files. Exact copies are preserved at
`data/interim/track_a_received_review_20261027/`. The files match the final v7
packets, have valid schemas and cover 73 corpus items, 20 questions and 2,035
candidates. All 2,035 decisions and 195 positive evidence spans exactly match
the saved development review. The three supplied output hashes and all five
referenced project-input hashes agree with the provenance record.

The provenance explicitly identifies generated draft files, illustrative
favorable corpus checks and transferred development labels. Reviewer/date fields
are empty, independence/blinding are false and final corpus acceptance is false.
The notes likewise describe possible disposition subject to actual review.
Both actual acceptance exports reject the files without creating output.
This preserves the user's report of completed review, but the supplied records
do not establish independent human acceptance. No draft decisions are relabelled
as human judgments, and no source/PDF scope approval or publisher permission is
inferred from the review files. The later development-scope disposition is
recorded separately; the original 82-file v7 delivery remains unchanged.

See `reports/track_a_human_review_status_20261027.json` and
`reports/track_a_submitted_review_validation_20261027.json`. The originally supplied versions are preserved. A later user-requested wording
revision removes product branding and draft/submission-status phrasing from the
four Desktop files. All decisions, spans, automated-label provenance and review
status fields remain unchanged; output hashes were updated and checked. See
`reports/track_a_submission_wording_revision_20261027.json`. The corpus, series,
indexes and existing scores remain unchanged.

## Delivered

| Track A task | Final evidence | Scope and acceptance limit |
|---|---|---|
| A1–A2 collection | 1,095 news: ET 870, BusinessLine 213, Mint 12. Official: MoSPI 37, PPAC 14, OEA 10. All seven months represented. | The documented mid-submission fallback retains the acquired source mix. Business Standard/RBI remain unavailable; ET concentration, sparse Mint and OEA deviation remain explicit. |
| A3–A5 extraction, scope, deduplication and freeze | Missing ET bodies recovered, Mint biographies/promotions removed, 21 unsuitable news documents excluded. All 870 ET originals checked: 105 marked custom links removed, no long related-link titles retained; untouched HTML preserved. Exact parent offsets and reverse-input archive checked. | Official PDFs are narrative-only: 949 paragraphs from 61 documents. Tables, charts, image-only material and 53,967 rejected native line groups remain outside the index. Source originals and layout audits stay local. No exhaustive table transcription or independent extraction certification is claimed. |
| A6–A7/A11 retrieval and dates | Plain/alias BM25, pinned BGE-M3, FAISS, RRF and pre-ranking date eligibility implemented. Final 16,472-passage index matches the corpus; fresh-process reload and two actual query embeddings/searches pass March/September cutoffs. | Model/preprocessing identity and exact title+text hashes govern vector reuse. Old v1 outputs and v3 review packets retain their original bindings. |
| A8–A9 development comparison | All six old uncertain items adjudicated as insufficient standalone evidence. Complete final pool: 195 relevant, 1,840 irrelevant, zero uncertain across 20 queries. All prior positives accounted for; final pool adds no candidates beyond the fully read v5 pool. Dense selected by the declared 0.03 rule; Recall@10 0.4259, rising to 0.5296 with reranking. | Single Codex review with prior results exposure. This settles the development configuration only. D-02/D-03 research acceptance requires independent review; reranker end-to-end benefit is unproven and full-scale B1-R remains deferred. |
| A10 series and episode support | All six canonical files retain 161 original-vintage observations. Separate 317-observation retrospective snapshot, exact hashes and date exclusions revalidated. Source/measure/episode feasibility audit complete; stricter source checks admitted no additional original-date values. | October captures cannot become March–September evidence. Daily benchmark yield, Brent/basket/FPI histories remain sparse. ATF and RBI policy episodes require the corresponding dated measures/statements; Track B owns anchor acceptance. |
| Reproduction/integration | 630 tests pass with Ruff/Black clean in the working checkout and a fresh environment with optional PDF/extraction packages. Committed source rebuilds the final corpus/archive from checksummed local originals. Saved-index reload uses two real query embeddings. | Core/PDF dependencies were installed into a new environment from local package cache. Heavy retrieval models/runtime and original data caches were reused; other machines and Kaggle are untested. The earlier 24/24 graph reproduction remains v1. |
| Reports, figures and handoff | Current corpus/series figures, selection, provenance, source scope, compute record, reproduction guide and mid-submission draft updated. New 82-file human-review workspace contains 73 sources/originals and all 2,035 candidates; all forms and attestations blank. | All 83 files in the original v3 delivery are unchanged. Actual blank corpus/relevance exports fail without output. No final UER, reference recall, agreement or human acceptance score is produced. |

## Additional source and acceptance work — 26 October follow-up

The user requested that the remaining work be handled without arranging another
reviewer. The existing development review remains complete. An assistant cannot
supply the independent human identity/blinding required by the study protocol;
the human forms and research acceptance therefore remain blank.

Further primary-source work is now complete:

- All 61 retained official PDFs were checked for file creation/modification dates
  later than their declared publication. All have comparable metadata; no known
  later-version conflict was found. This detects known conflicts, not unknown
  historical edits or full extraction correctness.
- The dated [PIB announcement](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2247895&lang=2&reg=3)
  supports the April 1 domestic ATF announcement and its limited 25 percent
  increase. It does not provide a city-specific daily price series.
- The [August 5 RBI statement](https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=63288)
  confirms the August 3–5 meeting and unchanged 5.25 percent repo rate. Primary
  content was read through the web tool; the collector remains blocked and no
  new RBI original was added to the corpus. Track B anchor acceptance is open.
- Seven public SEBI annexures were acquired. Four pass the file/version/table
  checks, yielding five distinct April–August total-FPI candidates with native
  USD values and conservative publication dates. The August annexure postdates
  its listed release and is excluded; two other downloaded copies are invalid
  ZIP files. The total includes mutual-fund investment and cannot be mixed with
  the current equity-plus-debt series. All five candidates and their source
  cells are recorded separately; canonical series remain at 161 observations.

The follow-up implementation adds seven meaningful publication, table identity,
unit, arithmetic, future-date and corrupt-download checks. Current local and
fresh-checkout suites pass **637 tests**. The earlier 630-test delivery and
source-rebuild receipts remain unchanged historical evidence.

See `reports/track_a_followup_20261026.json`,
`reports/sebi_fpi_vintage_audit_20261026.json`,
`reports/official_pdf_version_audit_20261026.json` and
`reports/track_a_followup_validation_20261026.json`. Source gaps, permissions,
independent human acceptance and complete original-date histories remain
requirements where the evidence above does not satisfy them.

## Final corpus and experiment boundaries

Active: `data/processed/`, **v7-narrative-development**, corpus SHA-256
`25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496`;
archive SHA-256
`88ae396dc390ff562684e5ab642d09523315e4de01a208ad0608ecc0b3194037`.
The active manifest records the narrative extraction scope. The final dense index
is `data/interim/corpus_v7_index_20261026/bge_m3_vectors.json`.

The reviewed v3 snapshot is archived at `data/interim/frozen_v3_20261026/`,
SHA `1df503a6101471a8646f6521f7c44ffbd946661ea79e63057f1bedf06c2a9164`.
Its 25 October review, index and original reviewer packet remain historical.
Intermediate v4/v5/v6 candidates are preserved and identified in
`reports/corpus_versions.json`. They are not mixed into final comparisons.

The earlier 42-graph assembly and 24-graph fresh-source reproduction use v1,
SHA `7b843fe072573fe7b3d54f89af6b2128bf61abe4115b4059d57665e9638543d3`,
at `data/interim/frozen_v1_20261023/`, with the preserved original three-series
inputs. They are unreviewed development runs, not v7 experiments or accepted
gold. Corrected baseline graphs, independent support/reference labels and
final UER belong to the remaining study work across tracks.

## Independent review handoff

Open `data/interim/track_a_review_delivery_v7_20261026/START_HERE.md` and read
`SCOPE.md` first. The corpus page includes 73 deterministic source/month samples
and all 73 checksummed originals. The relevance page includes 20 questions and
2,035 candidates without scores, ranks or seed flags. Forms and human identity,
date, independence, blinding and acceptance attestations remain wholly blank.
Do not copy the separate Codex review into those forms.

The final integrity validator checks corpus/archive bytes, every passage offset,
index identity, complete judgment coverage/text hashes/evidence spans, dates,
all new and original workspace hashes, series hashes and blank human forms.
It checks integrity; it does not certify semantic correctness or independence.

## Mid-submission closure and remaining research acceptance

The [27 October closeout](track_a_mid_submission_scope_20261027.md) adopts the
reduced source/PDF scope and sparse six-series coverage for this development
handoff. These two disposition tasks are closed with explicit deviations;
complete acquisition or historical coverage is not claimed. No further
autonomous Track A engineering task remains within that scope.

Formal independent review remains incomplete. Actual reviewer records and
truthful date/independence/blinding declarations are required before Track A
research receipts or final D-02/D-03 acceptance. The user's reported review is
preserved, but the submitted declarations do not meet that gate.

Publisher permission remains necessary before any sharing that requires it.
Full text, indexes, source originals and archives remain local. Later research
requiring complete series or confirmed anchors needs the missing dated evidence;
Track B must confirm, drop or redate unsupported anchors. Retrospective proxies
remain separate. The broader study still has Track B/C annotation, model/TA
decisions and final-result work. No pull request or research issue closure is
part of this delivery.

## Key records

- `reports/track_a_validation_20261026.json`,
  `reports/track_a_clean_reproduction_20261026.json`.
- `reports/corpus_v7_build_20261026.json`,
  `reports/corpus_v7_navigation_qa_20261026.json`,
  `reports/corpus_v7_index_20261026.json`,
  `reports/retrieval_v7_saved_index_validation_20261026.json`.
- `reports/relevance_adjudication_20261026.json`,
  `reports/retriever_v5_full_review_20261026.json`,
  `reports/retriever_v7_full_review_20261026.json`,
  `reports/track_a_retrieval_selection_20261026.json`,
  `reports/pilot_retriever_v7_20261026.md`.
- `reports/track_a_source_scope_20261026.md`,
  `reports/track_a_series_scope_20261026.json`,
  `reports/retrospective_series_read_validation_20261026.json`.
- `reports/track_a_reviewer_delivery_v7_20261026.json`,
  `reports/corpus_versions.json`, `data/processed/MANIFEST.md`,
  `docs/reproduction.md`, `docs/decisions.md`, `reports/compute_log.md`.
