# Corpus snapshot v3-candidate

**Status: TARGET COUNTS MET — source coverage, extraction quality and licences still require review before the final research freeze.**

Publication window: 2026-03-01 through 2026-09-30 (inclusive).
Retained: 1177 documents (1116 news, 61 official), 28391 passages.
Removed duplicates: 6; input documents: 1183.
Plan targets: at least 900 news articles and 60 official documents. Shortfalls: 0 news, 0 official.

## Documents by source and publication month

| Source | 2026-03 | 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 | 2026-09 | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| business_standard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| businessline | 31 | 30 | 34 | 33 | 28 | 25 | 34 | 215 |
| eaindustry | 1 | 1 | 1 | 2 | 2 | 1 | 2 | 10 |
| economic_times | 154 | 123 | 123 | 119 | 124 | 117 | 129 | 889 |
| mint | 2 | 2 | 2 | 1 | 2 | 2 | 1 | 12 |
| mospi | 6 | 2 | 6 | 5 | 5 | 7 | 6 | 37 |
| pib | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ppac | 1 | 2 | 0 | 5 | 2 | 4 | 0 | 14 |
| rbi | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## SHA-256 and sharing

Share `corpus-v3-candidate.zip` separately; corpus payloads remain outside git. The zip contains the three JSONL files below.

| File | Bytes | SHA-256 |
|---|---:|---|
| `articles.jsonl` | 21506866 | `1df503a6101471a8646f6521f7c44ffbd946661ea79e63057f1bedf06c2a9164` |
| `corpus-v3-candidate.zip` | 26320210 | `3489d75ace9a7ed3ddc30c29fb596259940bcb777ef3f0a70dabe58f1c6dd427` |
| `documents.jsonl` | 4812009 | `d82e1da13ce405c7431c03e1238562f52303c1e4adb811249d33e62e2f55b212` |
| `duplicates.jsonl` | 995 | `68259d98c1adcd1d60cb1d0d4babc1aaeb39f044048d49c0120f2aef7d7fd840` |

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
