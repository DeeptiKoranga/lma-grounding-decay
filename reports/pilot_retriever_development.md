# Retriever pilot

Status: **SUPERSEDED — temporal audit invalidated one original pair; do not use these metrics for a research decision**.

Shared query/evidence pairs: 20. Positive passage IDs came from a machine-curated file pending human review; they are not independently annotated gold.
Corpus SHA-256: `63aa2e5e59c501d5b8441698a2bf0b156483f42638b6bc9cc061effb515cfe59`.
Pair file SHA-256: `cd06b5e91937918914a76536afc42c88dc5d2faca990b12d1cae1d0948be8226`.
Alias file SHA-256: `826f0e59c3ad98b2ca3d6ff08027ead08c917fed36d9d0a711cf802a1eebe843`.
Embedding: `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`.
Device: `mps`; dense backend: `exact`; RRF constant: 60; candidate pool: 50.
Maximum input tokens: 1024; embedding batch size: 2; reranker batch size: 1.
Package versions: `{"faiss-cpu": "1.15.1", "sentence-transformers": "6.2.0", "torch": "2.14.1", "transformers": "5.20.2"}`.
Elapsed wall time: 82.48 seconds.
The dense model is unloaded before the cross-encoder; first-stage candidates are cached unchanged.

| Configuration | Recall@5 | Recall@10 | MRR@50 |
|---|---:|---:|---:|
| bm25 | 0.9000 | 0.9500 | 0.7708 |
| bm25_alias | 0.8500 | 0.9000 | 0.6754 |
| bge_m3 | 0.8750 | 0.9250 | 0.7475 |
| hybrid_rrf | 0.9250 | 0.9750 | 0.7850 |
| bm25 + reranker | 0.9750 | 1.0000 | 0.9000 |

Reranker: `BAAI/bge-reranker-v2-m3`, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`; top 50 rescored.

Simplest configuration within 0.03 Recall@10 of the best: `bm25`.
Smoke checks do not resolve D-02/D-03. Review the evidence and corpus quality before recording a research decision.

Limitations: March-only convenience sample; 35 initial documents and incomplete known-positive labels. These are functional development results, not a frozen retriever decision. The pair review is in `reports/pilot_pair_review.md`.
