# Retriever pilot

Status: **SMOKE CHECK ONLY; no research decision**.

Shared query/evidence pairs: 20. Positive passage IDs came from the supplied pair file; this runner does not certify independent annotation.
Corpus SHA-256: `7b843fe072573fe7b3d54f89af6b2128bf61abe4115b4059d57665e9638543d3`.
Pair file SHA-256: `de6c265557d352516bc97cae762e109c5e50c99c315264bc373f7748adb11f8d`.
Alias file SHA-256: `826f0e59c3ad98b2ca3d6ff08027ead08c917fed36d9d0a711cf802a1eebe843`.
Embedding: `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`.
Device: `cpu`; dense backend: `faiss`; RRF constant: 60; candidate pool: 50.
Maximum input tokens: 1024; embedding batch size: 8; reranker batch size: 1.
Package versions: `{"faiss-cpu": "1.15.1", "sentence-transformers": "6.2.0", "torch": "2.14.1", "transformers": "5.20.2"}`.
Elapsed wall time: 20.14 seconds.
Cache state at start: `{"dense_index_preexisting": true, "embedding_checkpoint_preexisting": true}`. Elapsed time excludes earlier checkpoint/index precomputation.
The dense model is unloaded before the cross-encoder; first-stage candidates are cached unchanged.

| Configuration | Recall@5 | Recall@10 | MRR@50 |
|---|---:|---:|---:|
| bm25 | 0.7250 | 0.9000 | 0.5796 |
| bm25_alias | 0.6500 | 0.7250 | 0.5465 |
| bge_m3 | 0.7750 | 0.8500 | 0.7366 |
| hybrid_rrf | 0.6750 | 0.9250 | 0.6777 |

Simplest configuration within 0.03 Recall@10 of the best: `bm25`.
Smoke checks do not resolve D-02/D-03. Review the evidence and corpus quality before recording a research decision.

Unranked review candidate pool SHA-256: `4312b49706fcf03e2fcf9867dfadc6729c68fd2cbcb9dd6cce6f4cb15f181e43`.
Candidate pool contains the union of all four first-stage top-50 lists, without scores or relevance judgments.
