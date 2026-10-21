# Corpus snapshot v1

**Status: PROVISIONAL — acquisition targets are not met; this is a pipeline snapshot, not the final frozen research corpus.**

Publication window: 2026-03-01 through 2026-09-30 (inclusive).
Retained: 35 documents (34 news, 1 official), 664 passages.
Removed duplicates: 0; input documents: 35.
Plan targets: at least 900 news articles and 60 official documents. Shortfalls: 866 news, 59 official.

## Documents by source and publication month

| Source | 2026-03 | 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 | 2026-09 | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| business_standard | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| businessline | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| economic_times | 32 | 0 | 0 | 0 | 0 | 0 | 0 | 32 |
| mint | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |
| mospi | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| pib | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| ppac | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| rbi | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## SHA-256 and sharing

Share `corpus-v1.zip` separately; corpus payloads remain outside git. The zip contains the three JSONL files below.

| File | Bytes | SHA-256 |
|---|---:|---|
| `articles.jsonl` | 496428 | `63aa2e5e59c501d5b8441698a2bf0b156483f42638b6bc9cc061effb515cfe59` |
| `corpus-v1.zip` | 606792 | `48f50f879ec993bfd2e91adec677b21fc867064844e78f5002a0cb2f46787e89` |
| `documents.jsonl` | 110024 | `031c1b857f553594664a3552c914040a6be6aca408144663dd3377ea9ba184e8` |
| `duplicates.jsonl` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## Deduplication and offsets

Exact full-text hashes plus MinHash on case-folded title + first-paragraph word trigrams; 128 deterministic permutations, 32 bands x 4 rows, exact Jaccard >= 0.85 required for near matches.
MinHash candidate recall is approximate. Earliest publication timestamp, then source/id, chooses the retained representative. Each removal is recorded in `duplicates.jsonl`.
Parent text is preserved in `documents.jsonl`; `articles.jsonl` contains paragraph passages whose character offsets address that exact normalised parent text. Raw publisher payloads and collection logs remain in `data/raw/`.
The zip uses sorted entries, fixed timestamps and permissions, and stored bytes so identical inputs and settings yield identical archive hashes.

## Licence notes

These are collection notes, not redistribution permission. Confirm source terms before sharing publisher text.
- economic_times: Copyright retained by publisher; research use, no redistribution licence assumed.
- mint: Copyright retained by publisher; research use, no redistribution licence assumed.
- pib: Official publisher retains rights; research use. Check the release's reproduction policy before redistributing source text.

Macro series confirm observed moves only; they are never evidence for causal edges and are excluded from this text corpus snapshot.
