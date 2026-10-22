# Track A series continuation — 23 October 2026

A10 now has three populated canonical series: seven CPI observations, 141
USD/INR reference rates, and two Indian basket monthly averages. Indian basket
coverage is partial. Front-month Brent, benchmark 10-year GSEC yields and
accepted FPI flows remain missing; A10 is not complete.

## Indian basket

`scripts/fetch/ppac_series.py` reuses the existing official collector's raw PDFs,
identity/checksum sidecars and saved release archive. It checks that the exact
PDF link and publication date appear together in one archive row, rejects
known later file versions, and cross-checks the narrative value against the
monthly price table. No new corpus freeze or retrieval embedding run is needed.

The accepted May snapshot gives April's monthly average of 114.48 and May's
106.23 USD per barrel. Both retain **17 June 2026** as the availability date of
the specific acquired release. Earlier availability for April is not inferred.
The source PDF's summary and price table were visually inspected. The four
other cached snapshot PDFs are excluded because their creation/modification
days follow their listed release dates. March and June–September remain gaps.
Monthly averages cannot establish a daily price threshold or an anchor date.

The canonical CSV and its source audit are `data/series/indian_basket_usd_bbl.csv`
and `data/series/indian_basket_provenance.json`.

## FPI candidates

CDSL's public date filter returned historical investment tables with native USD
values. `scripts/fetch/cdsl_series.py` downloads them with bounded requests,
robots checks, pacing and a transient public session; it can replay verified
local caches. It extracts Equity + Debt + Debt-VRR + Debt FAR, excludes other
categories, checks net arithmetic, and reconciles monthly and daily USD totals
within the source's rounding precision.

Five reporting-month candidates were extracted for April, June, July, August
and September. March and May have no actual reporting row on their selected
calendar month-end, so no publication date was inferred for those monthly totals.

**FPI is still unavailable to SeriesStore.** The archive is generated on request,
and source reporting dates do not certify the historical vintage of its values.
Candidates stay at `data/interim/series/fpi_flows_usd_mn_candidate.csv`, outside
the canonical store. `reports/fpi_acquisition_review.json` records all returned
values, component sums, selected dates, source URLs, raw checksums and exclusions.
An original dated release or independent evidence of vintage stability is still
required before importing them. The series also requires acceptance of the
custodian reporting-month convention rather than a trading-month convention.

## Validation and remaining work

The 28 new source-specific tests pass. They cover early as-of exclusion,
wrong price definitions, period mismatches, missing/deviant table values,
later PDF versions, cache corruption, source identity, FPI category selection,
rounding disagreement, date-selection failures and request/byte limits.

The project-wide `make lint test` gate passed: Ruff, Black and **412 tests** on
the current shared working tree. This includes concurrent retrieval-review work;
this continuation edits the two new source importers, their tests, series data
and series documentation only. The production CDSL downloader is also checked
against one real historical snapshot separately from its fixture tests.

Next A10 work: find original Indian basket releases for the remaining months;
verify FPI historical vintages and missing monthly availability; acquire a
front-month Brent history and a consistently identified benchmark 10-year GSEC
yield series. Do not substitute spot Brent, generic par yields or unconverted
INR FPI amounts. Independent corpus/pilot review and Track C integration remain
separate acceptance gates in `reports/track_a_progress.md`.
