# Retriever pilot

Status: **SMOKE CHECK ONLY; no research decision**.

Shared query/evidence pairs: 20. Positive passage IDs came from the supplied pair file; this runner does not certify independent annotation.
Corpus SHA-256: `b63a8743e7f227a90f4d08ae73a5f195ac10ceb581ee11060d59815b1e5f80e2`.
Pair file SHA-256: `59a7684d96dbc8c6108da799c459a9258b842a662b59b8c48e41c3c2dfc30ef0`.
Alias file SHA-256: `826f0e59c3ad98b2ca3d6ff08027ead08c917fed36d9d0a711cf802a1eebe843`.
Embedding: `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`.
Device: `cpu`; dense backend: `faiss`; RRF constant: 60; candidate pool: 50.
Maximum input tokens: 1024; embedding batch size: 8; reranker batch size: 1.
Package versions: `{"faiss-cpu": "1.15.1", "sentence-transformers": "6.2.0", "torch": "2.14.1", "transformers": "5.20.2"}`.
Elapsed wall time: 183.14 seconds.
Cache state at start: `{"dense_index_preexisting": false, "embedding_checkpoint_preexisting": true}`. Elapsed time excludes earlier checkpoint/index precomputation.
The dense model is unloaded before the cross-encoder; first-stage candidates are cached unchanged.

| Configuration | Recall@5 | Recall@10 | MRR@50 |
|---|---:|---:|---:|
| bm25 | 0.3083 | 0.4333 | 0.2588 |
| bm25_alias | 0.3500 | 0.5167 | 0.3288 |
| bge_m3 | 0.5250 | 0.6000 | 0.4915 |
| hybrid_rrf | 0.5583 | 0.6250 | 0.4932 |
| bge_m3 + reranker | 0.6500 | 0.7667 | 0.5369 |

Reranker: `BAAI/bge-reranker-v2-m3`, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`; top 50 rescored.

Simplest configuration within 0.03 Recall@10 of the best: `bge_m3`.
Smoke checks do not resolve D-02/D-03. Review the evidence and corpus quality before recording a research decision.

Unranked review candidate pool SHA-256: `85b90dfeddda2fa7ba7acd9782721c667837da377f0869a17f7919eea6433960`.
Candidate pool contains the union of all four first-stage top-50 lists, without scores or relevance judgments.
