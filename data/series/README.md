# Macro series store (Track A, A10)

The importer and date-aware read layer are implemented. **Two of the six series
have real observations; A10 is incomplete.** No demonstration values, interpolation,
or substitutes for the frozen definitions are stored as project data.

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

Raw release PDFs and API responses are retained under `data/raw/series/` locally.
The CSVs and provenance records are tracked. These observations only confirm
measured moves; they do not confirm the project's anchor episodes automatically.

Reproduce the two acquisitions with the existing optional PDF dependency:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.fetch.cpi_series
PYTHONPATH=src .venv/bin/python -m scripts.fetch.fbil_series
```

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

Brent, Indian basket, benchmark 10-year yield and FPI flows are still missing.
The remaining source entries above are acquisition guidance, not downloaded data.
Do not substitute spot Brent for front-month futures, CPI index levels for annual
inflation, or INR-crore FPI values for USD million. Upward `inr_usd` means a weaker
rupee. Keep the benchmark/security definition consistent for bond yields.

Acquisition checks found that PPAC's current monthly price table was modified in
October; it cannot be backdated into March–September. Its news archive did not
provide the required in-window daily basket records. FBIL's GSEC listing returns
dated download links, not a verified benchmark-yield series. The NSDL production
report pages were inaccessible in this session; pilot/test-domain values were
not imported. A licensed front-month Brent history, benchmark identification,
and source publication dates still need verification for the remaining files.

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
