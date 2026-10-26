# Corpus snapshot v7-narrative-development

**Status: TARGET COUNTS MET — source coverage, extraction quality and licences still require review before the final research freeze.**

Publication window: 2026-03-01 through 2026-09-30 (inclusive).
Retained: 1156 documents (1095 news, 61 official), 16472 passages.
Removed duplicates: 0; input documents: 1156.
Plan targets: at least 900 news articles and 60 official documents. Shortfalls: 0 news, 0 official.

## Documents by source and publication month

| Source | 2026-03 | 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 | 2026-09 | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| business_standard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| businessline | 30 | 30 | 34 | 33 | 28 | 24 | 34 | 213 |
| eaindustry | 1 | 1 | 1 | 2 | 2 | 1 | 2 | 10 |
| economic_times | 153 | 122 | 118 | 118 | 118 | 114 | 127 | 870 |
| mint | 2 | 2 | 2 | 1 | 2 | 2 | 1 | 12 |
| mospi | 6 | 2 | 6 | 5 | 5 | 7 | 6 | 37 |
| pib | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| ppac | 1 | 2 | 0 | 5 | 2 | 4 | 0 | 14 |
| rbi | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## SHA-256 and sharing

Keep `corpus-v7-narrative-development.zip` local until applicable source permissions and project scope are accepted; corpus payloads remain outside git. The zip contains the three JSONL files below.

| File | Bytes | SHA-256 |
|---|---:|---|
| `articles.jsonl` | 14163728 | `25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496` |
| `corpus-v7-narrative-development.zip` | 18505288 | `88ae396dc390ff562684e5ab642d09523315e4de01a208ad0608ecc0b3194037` |
| `documents.jsonl` | 4341220 | `d4d371d1b769b9c980a8f8c802f430dae2879c2e4b84f2d4adab3ffd2422eae0` |
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

## Scoped Track A delivery — 26 October 2026

Development corpus only; research acceptance remains pending. The original v1
experiments and v3 human-review packet remain bound to their original snapshots.

The final corpus contains 1,156 documents and 16,472 exact-offset passages. The
61 official PDFs contribute 949 narrative paragraphs. Numeric tables, charts,
image-only content and 53,967 rejected native line groups are outside the declared
PDF extraction scope; their original files and layout audit records remain local.
Twenty-one off-scope news documents were excluded. All 870 Economic Times
originals were checked for marked custom links: 105 identified links were removed
before extraction, with none of their long titles remaining in the corpus. Other
HTML is preserved exactly by range deletion. This is a targeted mechanical check,
not independent certification of complete article extraction.

Corpus SHA-256: `25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496`.
The fulltext, archives, source originals and dense vectors remain local; the
source-policy audit does not establish publisher redistribution permission.
