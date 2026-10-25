# Retrospective macro snapshots — captured October 2026

These six files contain **317 observations**, including exact copies of the
original CPI and FX files. The four new histories cover March–September 2026.
They support retrospective checks of measured moves. They are separate from
the default 161-observation historical store in the parent directory.

| Series | Observations | Measurement | Known availability |
|---|---:|---|---|
| Brent | 148 | Yahoo BZ=F NYMEX financial futures vendor continuous daily closes | 25 October |
| Indian basket | 7 | PPAC monthly averages | March value: 22 October; April–September: 25 October |
| Ten-year yield | 7 | FRED/OECD INDIRLTLT01STM, monthly main yield including benchmark | 25 October |
| FPI | 7 | CDSL monthly Equity + Debt + Debt-VRR + Debt FAR, native net USD million | 23 October |
| CPI | 7 | Original MoSPI provisional headline YoY, February–August | Original release dates, unchanged |
| USD/INR | 141 | FBIL daily reference rates, March–September | Original recorded availability, unchanged |

`available_on` for each newly captured history is its verified local cache capture
date in India time. This conservative bound **does not assert its first release
date**. An as-of query in March–September cannot see any of these four backfills.
The standard reader ignores nested directories. Explicitly load this directory
and use a post-capture cutoff for retrospective analysis.

The Brent provider's contract-roll mapping has not been independently verified
against every ICE contract. Its financial futures closes differ from the parent
store's intraday nearby quotes. The monthly bond series differs from the parent
store's named benchmark-security daily closes. Monthly observations are period
values labelled at month end; they cannot establish a daily threshold crossing.
FPI sums custodian reporting-month flows; it does not sum all investment products
or establish trading-month totals. No missing values are interpolated.

March's basket value was visually transcribed from page 5 of the checksummed
scanned PPAC April snapshot. The overlapping April value agrees with page 38
and the public current-year table. This is a recorded model transcription,
not an expert review or historical-vintage approval. The PDF's conflicting
listed/file-version dates remain excluded from the historical text corpus.

`PROVENANCE.json` records source URLs, cache checksums, definitions, capture times,
the visual transcription and unchanged hashes of all six parent CSVs. Sources:
[Yahoo Finance BZ=F](https://finance.yahoo.com/quote/BZ%3DF/history/),
[OECD via FRED](https://fred.stlouisfed.org/series/INDIRLTLT01STM),
[PPAC](https://ppac.gov.in/prices/international-prices-of-crude-oil), and
[CDSL](https://www.cdslindia.com/Publications/FIITrends.aspx).
Citation: OECD (2026), Main Economic Indicators, via FRED, Federal Reserve Bank
of St. Louis, INDIRLTLT01STM; accessed 25 October 2026.

From the repository root, replay public acquisition and import into a **fresh**
directory; existing caches are checked before any bounded download:

```sh
PYTHONPATH=src .venv/bin/python -m scripts.fetch.retrospective_sources \
  --report reports/retrospective_source_recheck.json
PYTHONPATH=src .venv/bin/python -m scripts.fetch.retrospective_series \
  --output data/interim/retrospective_series_recheck \
  --report reports/retrospective_series_recheck.json
PYTHONPATH=src .venv/bin/python -m scripts.validate_retrospective_series \
  --report reports/retrospective_read_layer_recheck.json
```

The importer also requires the existing checksummed CDSL selections and PPAC PDF
named in provenance. Raw caches are local and excluded from Git. The acquisition
commands cannot reconstruct an October 2026 snapshot from a later revised page.
