# Corpus snapshot v1

**Status: TARGET COUNTS MET — source coverage, extraction quality and licences still require review before the final research freeze.**

Publication window: 2026-03-01 through 2026-09-30 (inclusive).
Retained: 1173 documents (1112 news, 61 official), 27286 passages.
Removed duplicates: 1; input documents: 1174.
Plan targets: at least 900 news articles and 60 official documents. Shortfalls: 0 news, 0 official.

## Documents by source and publication month

| Source | 2026-03 | 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 | 2026-09 | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| business_standard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| businessline | 31 | 30 | 34 | 34 | 28 | 27 | 34 | 218 |
| eaindustry | 1 | 1 | 1 | 2 | 2 | 1 | 2 | 10 |
| economic_times | 154 | 124 | 123 | 120 | 124 | 117 | 130 | 892 |
| mint | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| mospi | 6 | 2 | 6 | 5 | 5 | 7 | 6 | 37 |
| pib | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ppac | 1 | 2 | 0 | 5 | 2 | 4 | 0 | 14 |
| rbi | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## SHA-256 and sharing

Share `corpus-v1.zip` separately; corpus payloads remain outside git. The zip contains the three JSONL files below.

| File | Bytes | SHA-256 |
|---|---:|---|
| `articles.jsonl` | 20486594 | `7b843fe072573fe7b3d54f89af6b2128bf61abe4115b4059d57665e9638543d3` |
| `corpus-v1.zip` | 24935738 | `ebef2e56b9db7c331289479e5dc9e67850edd5546364dc9844e79eeb6264a3f4` |
| `documents.jsonl` | 4448672 | `57f437f8b62b4a4c404a3a83b2f899cee4e9809039d7e05abd9766589d09d91f` |
| `duplicates.jsonl` | 132 | `434290347676a1c9d87c4499fc0d66e789c9fcbf0d51566e886139e4c11e791d` |

## Deduplication and offsets

Exact full-text hashes for all sources; news additionally uses MinHash on case-folded title + first-paragraph word trigrams with 128 deterministic permutations, 32 bands x 4 rows, exact Jaccard >= 0.85 required for near matches. Official releases use full-text equality only: identical cover pages can accompany distinct monthly data or vintages.
MinHash candidate recall is approximate. Earliest publication timestamp, then source/id, chooses the retained representative. Each removal is recorded in `duplicates.jsonl`.
Parent text is preserved in `documents.jsonl`; `articles.jsonl` contains paragraph passages whose character offsets address that exact normalised parent text. Raw publisher payloads and collection logs remain in `data/raw/`.
The zip uses sorted entries, fixed timestamps and permissions, and stored bytes so identical inputs and settings yield identical archive hashes.

## Licence notes

These are collection notes, not redistribution permission. Confirm source terms before sharing publisher text.
- businessline: Copyright retained by publisher; research use, no redistribution licence assumed.
- eaindustry: Official publisher retains rights; research use. Check the release's reproduction policy before redistributing source text.
- economic_times: Copyright retained by publisher; research use, no redistribution licence assumed.
- mint: Copyright retained by publisher; research use, no redistribution licence assumed.
- mospi: Official publisher retains rights; research use. Check the release's reproduction policy before redistributing source text.
- ppac: Official publisher retains rights; research use. Check the release's reproduction policy before redistributing source text.

Macro series confirm observed moves only; they are never evidence for causal edges and are excluded from this text corpus snapshot.
