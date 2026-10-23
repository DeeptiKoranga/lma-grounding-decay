# Macro series store (Track A, A10)

The importer and date-aware read layer are implemented. **All six required series
now have observations, with explicitly sparse coverage.** CPI and FX use official
sources; Indian basket has two official monthly averages. Brent, benchmark yield
and FPI use the dated news-reported observations below. These do not constitute
complete daily/monthly histories or confirmation of all planned anchor episodes.
No missing values are filled or interpolated.

## Acquired observations

- `cpi_headline_yoy.csv`: seven original MoSPI provisional combined headline YoY
  observations for February–August 2026, published March–September. Base: 2024=100.
  `cpi_provenance.json` records release URLs, raw-file checksums and extraction
  details. August's original provisional value is 4.82, not its later revision.
  September's observation was released in October and is excluded.
- `inr_usd.csv`: 141 FBIL daily reference-rate observations, 2 March–30 September
  2026. These are reference rates rather than market closes. The original API's
  `processRunDate` dates observations and `displayTime` dates availability.
  `inr_provenance.json` records the seven monthly response URLs and checksums.
  Holidays and other missing dates are omitted.
- `indian_basket_usd_bbl.csv`: two PPAC monthly averages for April and May 2026,
  both available from the May snapshot published **17 June 2026**. April's
  comparison value retains that June availability date. Summary text on PDF
  page 5 and the price table on page 38 agree on May's value.
  `indian_basket_provenance.json` binds the release/archive URLs, checksums,
  extraction pages and four excluded later-version snapshots. Coverage remains
  missing for March and June–September. Monthly averages cannot establish a
  daily threshold crossing or the date of an anchor episode.
- `brent_usd_bbl.csv`: four **intraday front-month futures quotes** on 1 April, 29 May,
  30 June and 4 August. April and August explicitly say front month. May and
  June concern the nearby contract expiring on that day; the more-active
  deferred contract is excluded. These are not settlement closes or a
  back-adjusted continuous series, and their intraday observation times differ.
- `gsec_10y_pct.csv`: six reported **current benchmark closing yields** on
  9 March, 27 March, 13 April, 11 June, 2 July and 31 August. The March/April
  observations identify 6.48% GS 2035; June/July/August identify 6.94% GS 2036. The security labels are retained in provenance.
  No benchmark roll date or missing yield is interpolated.
- `fpi_flows_usd_mn.csv`: one news-reported completed-March net **local stocks
  plus bonds** outflow, available **13 April**. Native USD 13.6 billion is
  converted to −13,600 USD million; reported precision is 100 million. This
  single point returns `move=None` and does not establish a monthly history.

`news_reported_provenance.json` records the latter eleven observations, exact
archived passage/raw hashes, publication timestamps, measurement definitions,
security identities and limitations. These are specific **published news
vintages**, not an acceptance of the dynamically generated CDSL archive or the
undated FBIL newsletter candidates. Unknown historical article edits remain a
limitation, as for the text corpus; known later-day versions are rejected.

The reproducible news importer validates the full input before writing and
refuses to replace any existing series. Use a fresh output directory to recheck:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.fetch.news_series \
  --output data/interim/news_series_recheck \
  --report reports/news_series_recheck.json
```

Raw CPI/FX responses are retained under `data/raw/series/`; PPAC originals remain
under `data/raw/ppac/` locally.
The CSVs and provenance records are tracked. These observations only confirm
measured moves; they do not confirm the project's anchor episodes automatically.

Reproduce these acquisitions with the existing optional PDF dependency:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.fetch.cpi_series
PYTHONPATH=src .venv/bin/python -m scripts.fetch.fbil_series
PYTHONPATH=src .venv/bin/python -m scripts.fetch.ppac_series
```

The PPAC importer reuses the official collector's checksummed PDFs and saved
archive at `data/raw/ppac/acquisition_archive.html`; it does not download them.
On another machine, collect the seed releases with `scripts.fetch.official`
and save the PPAC archive before running it. The archive must link each exact
PDF URL to the publication date recorded in `scripts/fetch/official_seeds.jsonl`.

## Files and units

Use one CSV per frozen ontology series id. Units must match exactly; convert
explicitly and preserve the conversion audit before importing.

| Filename | Ontology variable | Required unit | Acquisition source to check |
|---|---|---|---|
| `brent_usd_bbl.csv` | `BRENT` | `USD per barrel` | A source matching the ontology's front-month Brent definition |
| `indian_basket_usd_bbl.csv` | `INDIAN_BASKET` | `USD per barrel` | PPAC Indian crude basket releases |
| `inr_usd.csv` | `INR_USD` | `INR per USD` | RBI/FBIL reference exchange-rate releases |
| `cpi_headline_yoy.csv` | `CPI_HEADLINE` | `percent year on year` | MOSPI CPI press releases |
| `gsec_10y_pct.csv` | `GSEC_10Y` | `percent` | RBI/FBIL benchmark 10-year government-security series |
| `fpi_flows_usd_mn.csv` | `FPI_FLOWS` | `USD million, net` | NSDL/CDSL net FPI equity-and-debt flow releases |

All six files are populated, but Brent/yield/FPI and Indian basket coverage
remain sparse. Four separately extracted FBIL month-end yield
candidates (March–June) remain outside this store; see
`reports/gsec_acquisition_review.json`. Their security coupon/maturity is
recorded, but media upload timestamps do not verify newsletter publication
dates or the historical benchmark roll. The July table is excluded because
its header and footnote name different months. No `available_on` was invented.

Reproduce the offline source audit after acquiring the checksummed original
newsletter assets and public listing:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.fetch.fbil_newsletters
```

The acquisition-source column describes preferred full-history sources.
Cached newsletter candidates do not constitute an accepted GSEC history; the
six populated yield points instead come from dated, named-security news reports.
Do not substitute spot Brent for front-month futures, CPI index levels for annual
inflation, or INR-crore FPI values for USD million. Upward `inr_usd` means a weaker
rupee. Keep the benchmark/security definition consistent for bond yields.

Acquisition checks found that PPAC's current monthly price table was modified in
October; it cannot be backdated into March–September. Its news archive did not
provide the required in-window daily basket records. The accepted May PDF
provides the two monthly observations above; four other cached snapshot PDFs
have later file versions and remain excluded. FBIL's GSEC listing returns
dated download links, not a verified benchmark-yield series. The NSDL production
report pages were inaccessible in this session; pilot/test-domain values were
not imported. Full front-month Brent, benchmark-yield and FPI histories remain
acquisition gaps; the sparse news observations do not fill those histories.

## FPI acquisition candidates, pending vintage review

The public CDSL archive is now accessible through its date-selection form.
`scripts.fetch.cdsl_series` extracts native USD monthly subtotals for Equity,
Debt, Debt-VRR and Debt FAR, excluding Hybrid, MF, AIF and derivatives. Monthly
totals are cross-checked against daily reporting rows with explicit rounding
tolerance. Five candidate observations cover April, June, July, August and
September. March and May are excluded because their selected month-end date
has no actual reporting row; an arbitrary date selection cannot prove publication.

**These are not in the canonical series store.** CDSL dynamically generates its
historical archive and provides no revision timestamps, so historical value
vintages remain unverified. The candidate CSV stays under the ignored
`data/interim/series/`, and the tracked audit is
`reports/fpi_acquisition_review.json`. Dates in that candidate file are
source-declared reporting dates, pending acceptance as availability dates for
the particular values. The CLI refuses output under canonical `data/series/`.
These are custodian reporting-month totals, not trading-month totals.

```sh
PYTHONPATH=src .venv/bin/python -m scripts.fetch.cdsl_series --download
# Subsequent runs can use the checksummed caches without --download.
```

The public archive depends on session state. The audit retains the form URL,
selected date, returned archive URL and raw checksum so the selection can be
replayed; opening the archive URL alone defaults to a current report.

## CSV contract

The exact header is `on,value,available_on,source_url,unit`.

- `on`: ISO observation date; for a monthly observation use the period's last date.
- `value`: finite numeric value in the required unit. Missing values are omitted,
  never interpolated or silently replaced with zero.
- `available_on`: ISO date the particular value/vintage became public. It must be
  at least `on`. Use the actual publication date, including for delayed releases.
  A March CPI value released in April is unavailable for March as-of queries.
- `source_url`: original public HTTP(S) data/release URL, retained for audit.
- `unit`: exact required unit from the table.

An observation may have multiple published vintages. Each `(on, available_on)`
pair must be unique. The reader selects only the latest vintage available by the
as-of date, then returns one point per observation date. A later revision never
replaces a value in earlier queries. The current day-level tool contract cannot
represent intraday release cutoffs; dates are inclusive.

## Import and inspect

Run from the repository root with its Python environment:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.fetch.series import \
  --series-id cpi_headline_yoy --input /path/to/audited-cpi.csv

PYTHONPATH=src .venv/bin/python -m scripts.fetch.series read \
  --series-id cpi_headline_yoy --start 2026-03-01 --end 2026-09-30 \
  --as-of 2026-09-30
```

Imports validate the whole file before creating a canonical CSV, report its SHA256,
and refuse to overwrite an existing series unless `--replace` is supplied. When
replacing, retain the historical vintages needed for prior as-of dates. Nothing is
downloaded automatically. Track C can call
`SeriesStore.from_directory(path).get_series(GetSeriesArgs(...), call_id=...)`.

The result matches the frozen `GetSeriesResult` schema. A move compares the first
and last visible levels, with `move=None` for one point; for FPI it compares net
flow observations rather than accumulating them. Series confirm a measured move.
They cannot supply source-asserted causal edges, evidence spans, or forecasts.
