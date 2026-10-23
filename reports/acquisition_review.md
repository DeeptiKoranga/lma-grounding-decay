# Track A acquisition and temporal review

Reviewed 22 October 2026. The corpus manifest is the authority for final retained
counts and hashes. Download counts include material later rejected and must not
be reported as corpus size.

## Selection and coverage

Economic Times archive sitemaps were sampled across March–September 2026 with a
fixed SHA-256 ordering and macro-topic URL screen, up to 145 candidates per month.
BusinessLine's archive is a URL set of daily sitemap links; these were traversed
by month and sampled at 35 candidates per month. Requests share robots policy,
origin pacing, a bounded budget and checksummed caches, including concurrent
response reads. Publisher article metadata supplies publication dates; sitemap
filenames and lastmod only schedule discovery.

This is a targeted convenience collection, not a representative sample of all
news. Economic Times dominates. BusinessLine contributes all seven months; Mint
has only two March items. Business Standard's robots endpoint returned 403, so
collection failed closed. Explicit subscription declarations are excluded. Source
coverage and the final topic/extraction review remain incomplete even when the
900-news target is met.

Official material comes from MoSPI's dated public release index, PPAC's dated
report archive, and original WPI/PPI and core-industry PDFs from the Office of
the Economic Adviser. OEA is a documented addition to the planned source list;
its PDF embargo headers supply dates. An original PIB-hosted CPI PDF was also
acquired; its identical text is deduplicated against MoSPI's copy. RBI's main
robots endpoint returned 418, and the main PIB robots endpoint returned 403.
No access restrictions were bypassed. A2 still has an RBI coverage gap.

The MoSPI additions concern CPI, GDP, industrial/services production,
infrastructure, national-accounts methodology and industry/enterprise output.
Staff notices, training events and general ministry news were excluded. Dates
refer to release/publication, not the economic observation month. The index
query and response are cached under `data/raw/series/`; each selected original
URL and date-source URL is in `scripts/fetch/official_seeds.jsonl`.

## Temporal and extraction checks

- A later-day news update cannot be used as the original publication's text.
  The research rebuild excludes such copies rather than backdating their body.
- Official PDFs with a file creation/modification day after the listed release
  are also excluded from the research snapshot. File metadata only flags a
  version conflict; it never supplies a publication date. This is conservative:
  a later timestamp could reflect a technical re-export rather than changed
  content. An archived original or a verified revision is required to readmit it.
- Some Economic Times pages embed current recommended-story summaries inside
  their article area. Extracted paragraphs are screened against the matching
  publisher-declared story body. Comparison tolerates quotation marks omitted
  by JSON-LD; stored evidence text keeps its original punctuation.
- Recognised app/subscription/market-navigation promotions are removed before
  normalisation and offset assignment. This also prevents recurring promotion
  text from distorting lexical statistics or embeddings.
- Seven official downloads have insufficient readable native PDF text or fail
  the extraction threshold. They are excluded. No OCR-derived text was admitted.
- A small source-stratified sample of article starts/ends and official headers
  was inspected during development. Some publisher extraction omits the opening
  sentence, and PDF blocks can flatten tables or retain page headers. The
  automated offset check proves text alignment, not complete extraction or
  causal relevance. Broader manual review is still needed.
- Every stored passage must exactly equal its parent's character slice. All
  stored publication dates must fall in 1 March–30 September 2026 inclusive.
  Retrieval filters visibility before scoring and before candidate cutoffs.

Unknown version history remains a limitation: absence of a modification tag
cannot prove that a currently fetched page is the original historical body.
The frozen interface has day-level dates; intraday cutoffs are unsupported.

## Duplicate policy

All documents use exact full-text hashes. News additionally uses deterministic
128-permutation MinHash/LSH on title-plus-first-paragraph word trigrams and
confirms candidates with exact Jaccard >= 0.85. Candidate recall is approximate.
Official statistical reports use full-text equality only: matching cover pages
must not collapse distinct monthly tables. A regression test covers this case.
The duplicate log identifies the retained representative for every removal.

## Series provenance

`data/series/cpi_provenance.json` records seven original provisional combined
headline inflation observations from MoSPI PDFs, with the 2024=100 base and
actual release dates. `data/series/inr_provenance.json` records 141 FBIL reference
exchange rates, with observation and public display timestamps. Both keep raw
checksums. Missing days are omitted, and subsequent revisions do not replace
values in earlier as-of queries.

Three required series remain unpopulated: front-month Brent,
benchmark 10-year GSEC yield and equity-plus-debt FPI flows in USD million.
The 23 October continuation added two Indian basket observations (April/May,
both available 17 June); its other months are still missing. Four FBIL yield
candidates are separately staged, without verified publication dates/benchmark
roll. See `reports/track_a_continuation.md` for the candidate corpus cleanup,
broader temporal pilot and subsequent source checks. PPAC's
current monthly table has an October modification date; its available news
archive lacked the in-window daily basket records. FBIL's GSEC endpoint exposed
report links but did not establish a consistent benchmark-security series.
NSDL's production reports were inaccessible; pilot/test-domain data was rejected
as an acquisition source. Spot Brent, generic par yields and unconverted INR
flows would violate the frozen definitions and were not substituted.

Sources: [MoSPI release index](https://mospi.gov.in/api/latest-release/get-web-latest-release-list),
[PPAC archive](https://ppac.gov.in/archives/reports),
[OEA WPI archive](https://eaindustry.nic.in/wpi_press_release_archive.asp),
[OEA core-industry archive](https://eaindustry.nic.in/ici_press_release_archive.asp),
[FBIL](https://www.fbil.org.in/),
[NSDL production reports](https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx).

## Retrieval evidence review

The 20 queries and 29 positive passages in `reports/retriever_pilot_pairs.jsonl`
are machine-curated and pending independent review. Their source anchors and
rationales are in `reports/pilot_pair_review.md`. They are concentrated in March,
have incomplete positive labels, and were selected from the initial convenience
sample. The four-way comparison and reranker run are software/development
results, not independent research evidence or a frozen D-02/D-03 decision.

The first development run was invalidated when one March 28 item was found to
contain a March 29 update. That pair was replaced with an eligible source-backed
refinery-compatibility question before the corrected comparison. Navigation
removal changed two paragraph IDs; exact deduplication changed one CPI source
ID. The 29 selected positive texts were otherwise preserved verbatim, and the
ID migration is recorded separately. Changes were based on source/version audits,
not observed retrieval rankings. The superseded report is labelled accordingly.
