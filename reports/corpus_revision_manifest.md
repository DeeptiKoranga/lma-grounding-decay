# Corpus snapshot v2-candidate

**Status: TARGET COUNTS MET — source coverage, extraction quality and licences still require review before the final research freeze.**

Publication window: 2026-03-01 through 2026-09-30 (inclusive).
Retained: 1183 documents (1122 news, 61 official), 26888 passages.
Removed duplicates: 0; input documents: 1183.
Plan targets: at least 900 news articles and 60 official documents. Shortfalls: 0 news, 0 official.

## Documents by source and publication month

| Source | 2026-03 | 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 | 2026-09 | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| business_standard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| businessline | 31 | 30 | 34 | 34 | 28 | 27 | 34 | 218 |
| eaindustry | 1 | 1 | 1 | 2 | 2 | 1 | 2 | 10 |
| economic_times | 154 | 124 | 123 | 120 | 124 | 117 | 130 | 892 |
| mint | 2 | 2 | 2 | 1 | 2 | 2 | 1 | 12 |
| mospi | 6 | 2 | 6 | 5 | 5 | 7 | 6 | 37 |
| pib | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ppac | 1 | 2 | 0 | 5 | 2 | 4 | 0 | 14 |
| rbi | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## SHA-256 and sharing

Share `corpus-v2-candidate.zip` separately; corpus payloads remain outside git. The zip contains the three JSONL files below.

| File | Bytes | SHA-256 |
|---|---:|---|
| `articles.jsonl` | 20215966 | `b63a8743e7f227a90f4d08ae73a5f195ac10ceb581ee11060d59815b1e5f80e2` |
| `corpus-v2-candidate.zip` | 24664854 | `19c1a37d7fadd33b1462336dec9956af8c30902f29e0bc583e7bc9c3ee1ec072` |
| `documents.jsonl` | 4448548 | `f58ff5c1df8b2c697084c235c74cb526c943969f0df1200c40f5f55dc98e5aa8` |
| `duplicates.jsonl` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

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
