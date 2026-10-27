# Track A mid-submission scope and closeout — 27 October 2026

The **scoped Track A development handoff is complete**. This closeout adopts the
available source mix, narrative PDF extraction and sparse original-vintage
series for the mid-submission. Those are explicit delivery deviations; they are
not claims of complete acquisition or final experiment acceptance. Separate Track A
review records now pass validation on Varun's user-declared independent/blinded
review of 27 October; the procedure itself is not independently observed.

This is the assistant's implementation disposition under the user's instruction
to finish the remaining Track A work and subsequent “DO IT”. It is not a signed
reviewer, team, TA or publisher approval. The original plan and research-export
requirements remain intact.

## Disposition of the three reported remaining items

| Item | Mid-submission disposition | Limit retained |
|---|---|---|
| Review acceptance | **Record-validation gate passed on user attestations:** reviewer Varun, 27 October 2026, independent review and blinding declared true. Both corpus and retrieval exports pass. | This validates complete, hash-bound records and declarations; it does not independently verify identity, review procedure or blinding chronology. Original automated labels are unchanged and remain disclosed. No experiment support/UER acceptance follows. |
| Source and PDF scope | **Closed for this development handoff with declared deviations:** retain the acquired six-source corpus and narrative-only PDF passages. Report missing Business Standard/RBI/PIB corpus coverage, limited Mint coverage, ET concentration and OEA substitution. | Publisher permission has not been granted. Full text, source originals, indexes and corpus archives remain local. Tables, charts and image-only PDF material are outside the indexed evidence scope. |
| Historical-series scope | **Closed for this development handoff with declared deviations:** retain all six canonical series and their 161 original-vintage observations. Keep the 317-observation retrospective snapshot separate. | Complete Brent, basket, benchmark-yield and FPI histories are unavailable in this delivery. No interpolation, backdating or measure substitution is permitted. Track B must confirm, drop or redate unsupported anchors before experimental use. |

The original A1–A11 plan asks for a development retrieval pilot and a six-series
read layer. It also permits reporting acquisition shortfalls. The exact source
mix here differs from its suggested fallback, so this closeout records that
deviation explicitly. It does not present unavailable sources as collected.
Independent experimental support/reference annotation remains separate work.

## Delivered A1–A11

| Tasks | Handoff evidence | Completion scope |
|---|---|---|
| A1–A2 | 1,095 news documents: ET 870, BusinessLine 213, Mint 12. 61 official documents: MoSPI 37, PPAC 14, OEA 10. All March–September months represented. | Delivered with the acquisition deviations above. |
| A3–A5 | 1,156 deduplicated documents, 16,472 exact-offset passages; archive and source hashes; source/month counts and local layout audits. | Delivered with narrative-only PDF extraction: 949 official paragraphs. |
| A6–A7 | Plain/alias BM25, pinned BGE-M3, FAISS and RRF; final dense index matches every active passage. | Implemented and validated. |
| A8–A9 | 20 queries and 2,035 development judgments, including 195 relevant spans. BGE-M3 Recall@10 0.4259; top-50 reranking 0.5296. | Development selection complete; user-attested review records now validate. End-to-end B1-R benefit remains unestablished. |
| A10 | Six canonical files, provenance and date-aware read layer; separate October-captured histories. | Delivered with sparse coverage and explicit measure definitions. |
| A11 | Publication cutoffs enforced before ranking; saved-index and actual-query checks; all current review candidates date eligible. | Implemented and validated. |

Corpus SHA-256:
`25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496`.
Archive SHA-256:
`88ae396dc390ff562684e5ab642d09523315e4de01a208ad0608ecc0b3194037`.
The immutable archive is not rebuilt merely to change this scope documentation.

The development retriever choices apply to the new Track A handoff. Existing v1
experimental outputs retain their original corpus and retrieval settings. No
historical run is relabelled as a v7 experiment.

## Final bounded source check

An additional primary-source web check on 27 October admitted **zero new
original-vintage observations**. The current [PPAC home page](https://ppac.gov.in/home)
did not establish the original availability of the missing historical prices.
The FPI section of the [March SEBI bulletin](https://www.sebi.gov.in/sebi_data/attachdocs/apr-2026/1775034592968.pdf)
reports February and includes mutual-fund investment; it does not supply the
missing March–September equity-plus-debt history. The [DEA home page](https://www.dea.gov.in/)
timed out. These were web inspections, not acquired raw assets or a claim that
no other usable source exists. Earlier source and vintage audits remain available.

## Validation and remaining acceptance

The 27 October integrity rerun verifies the active corpus/archive and dense
index, every passage offset, all 2,035 decisions and 195 positive spans, both
unchanged review workspaces (82 current and 83 historical files), and both series
stores. The revised supplied files pass their schemas, packet bindings and
declared hashes. The original incomplete declarations were rejected, as recorded
in `track_a_mid_submission_validation_20261027.json`. After the user supplied
reviewer/date and explicit independent/blinded review attestations, both exports
passed and created receipts. The current update and limits are in
`track_a_reviewer_identity_20261027.json`; the earlier validation stays historical.

The last code validation remains 637 passing tests in both the working checkout
and a fresh core/PDF environment, with Ruff and Black clean. This closeout changes
reports and scope documentation; it does not claim a new model or experiment run.

No autonomous Track A engineering task remains for this scoped development
handoff. **Track A reviewer-record validation now passes** on the supplied user
attestations; this does not independently certify review conduct. Broader source
coverage, redistribution clearance
and complete historical-series/anchor acceptance remain prerequisites whenever
later research or sharing requires them. The entire mid-submission, other tracks
and final study are not declared complete. No pull request is created.
