# Track A source and relevance review — 25 October 2026

The review is complete for **73 corpus samples and all 2,062 pooled passage
judgments across 20 questions**. The reviewed v3 corpus is **not accepted**:
extraction, scope and PDF layout defects remain. The findings below distinguish
the reviewed text from a separately staged repair candidate.

Reviewer: **Codex**, with prior exposure to project results. This is development
source review, not independent human expert acceptance. No reviewer identity,
independence or blinding attestation has been supplied on someone else's behalf.

## Corpus findings

All 40 sampled HTML article texts were read. Saved HTML publication metadata
matches the recorded publication timestamps. Visible article text and declared
bodies were compared where available. All 33 PDF covers were inspected, along
with native first/last-page text and selected second-page layouts. Native PDF
block extraction reproduces every sampled stored PDF text exactly. This is
**not an exhaustive audit of every PDF table cell** and does not establish
source-rights clearance or historical intraday availability.

| Sample disposition | Count | Interpretation |
|---|---:|---|
| Usable with stated limits | 17 | No identified blocking extraction defect in the inspected material; no global acceptance implied |
| Minor cleanup | 4 | Joined words or publisher promotion in BusinessLine text |
| Repair required | 48 | 17 HTML body/biography/duplication defects and 31 PDF layout/context problems |
| Out of scope | 2 | Company promotional release and a party bank-account story admitted through CPI(M) |
| Further review | 2 | Missing infographic content and an article without a matching declared-body completeness check |

The original Economic Times sample loses visible material in **12 of 14**
stories, including the subsequently excluded party-account story. Omissions
include the Russian supply-routing explanation, arbitrage-related dollar
demand, and the conditional caveat on foreign bond inflows. The new parser
recovers those 12 samples from visible cached HTML across embedded widgets and
lists, without importing metadata-only text or explicit related-story links.

Five Mint samples include author biographies; another repeats its standfirst.
Matching publisher brand suffixes correctly restores the body filter. The
scope screen now distinguishes CPI(M) from consumer-price-index references
and excludes an explicit noneditorial company-release disclaimer.

The PDF defects concern **context**, not simply missing bytes: isolated values
can lose their row label, unit, month, series base, or provisional status. The
PPAC consumption sample contains 1,024 short/numeric/header paragraphs. A printed
PIB release includes browser timestamp/URL furniture. Two narrative committee
press notes are substantially more coherent. PDF creation time and observation
month do not prove publication time; release-list metadata remains necessary.

Full-pool reading also found unlabelled recommended headlines inside an ET
article and a movie story admitted by the word *rupee*. These remain explicit
findings; the HTML fixes do not establish an entirely clean corpus.

## Relevance judgments

The reviewer read every candidate against its fixed question and cutoff. A
direct partial answer may be relevant; general topic overlap, another dated
episode, a different measure, or an unexplained number is insufficient. Earlier
mechanism evidence is allowed where the question asks for an explanation, but
cannot substitute for the figures or policy outlook of a specified release.
Question-specific criteria and every decision are saved in the machine-readable
review. Prior local classifier outputs were not used.

| Decision | Query–passage judgments |
|---|---:|
| Relevant | 182 |
| Irrelevant | 1,874 |
| Uncertain | 6 |
| Total | 2,062 |

There are 1,646 distinct passages; the same passage can have different relevance
to different questions. Every question retains at least one positive passage.
The six uncertain cases concern unresolved references or table-column context.
They are **not negatives**. Matching text without its measure/column label is
not promoted to evidence just because the number matches an expected answer.

Every judgment is bound to the unchanged packet and passage text hash. Positive
evidence offsets identify exact spans in that packet. The report stores offsets
and hashes instead of republishing article text. These labels are not a human
receipt, an independent second annotation, or final retrieval research scores.

## Repairs and verification

The separate candidate contains **1,159 documents and 29,595 passages**. Reparse
changed 643 retained documents: 637 ET and six Mint. The scope screen removed
18 documents: 17 party/political false positives and one explicit promotional
release. All 61 official documents remain unchanged.

Candidate passage SHA-256:
`9d76908d9fb46488f096700055af4d5ec734cf838e92a639517135ff6379e97e`.
Every candidate passage matches its parent-text offsets; reverse input order
produces the same archive. The active v3 corpus, its index, prior experiments,
and all **83 original review-delivery files** remain unchanged. The candidate
has not been promoted: changed paragraph boundaries require rebuilt indexes
and migrated/reviewed passage identities before new experiments.

The local suite passes **623 tests**, with Ruff and Black clean. Regression
checks cover recovery across widgets/lists, exclusion of hidden/metadata-only
content, Mint author biographies, the CPI(M) collision and the company-release
disclaimer. Review validation confirms complete packet coverage, exact evidence
offsets, eligible dates and the unchanged original human-review files. These
mechanical checks do not certify the semantic correctness of judgments.

Records:

- [All sample findings and pooled decisions](track_a_source_review_20261025.json).
- [Repair provenance and exclusions](corpus_source_review_repairs_20261025.json).
- [Coverage, hashes and preservation checks](track_a_source_review_validation_20261025.json).

## Remaining acceptance work

Resolve PDF table context, the missing infographic and residual scope/navigation
defects; establish source terms and dated-source adequacy. Rebuild the chosen
corpus/index and migrate its review references before selection experiments.
Independent corpus/relevance acceptance and D-02/D-03 remain open. Baseline
correction, support/reference labels and final UER/recall figures belong to the
separate experiment-review work and were not completed by this source review.
No pull request or research signoff was created.
