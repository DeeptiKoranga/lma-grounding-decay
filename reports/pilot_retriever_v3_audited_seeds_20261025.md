# Retriever pilot

Status: **SMOKE CHECK ONLY; no research decision**.

Shared query/evidence pairs: 20. Positive passage IDs came from the supplied pair file; this runner does not certify independent annotation.
Corpus SHA-256: `1df503a6101471a8646f6521f7c44ffbd946661ea79e63057f1bedf06c2a9164`.
Pair file SHA-256: `6d02f0299a12ac1565874071dc307ad15449f851a3137513ffb3aa08b48a2823`.
Alias file SHA-256: `826f0e59c3ad98b2ca3d6ff08027ead08c917fed36d9d0a711cf802a1eebe843`.
Embedding: `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`.
Device: `cpu`; dense backend: `faiss`; RRF constant: 60; candidate pool: 50.
Maximum input tokens: 1024; embedding batch size: 8; reranker batch size: 1.
Package versions: `{"faiss-cpu": "1.15.1", "sentence-transformers": "6.2.0", "torch": "2.14.1", "transformers": "5.20.2"}`.
Elapsed wall time: 145.04 seconds.
Cache state at start: `{"dense_index_preexisting": true, "embedding_checkpoint_preexisting": false}`. Elapsed time excludes earlier checkpoint/index precomputation.
The dense model is unloaded before the cross-encoder; first-stage candidates are cached unchanged.

| Configuration | Recall@5 | Recall@10 | MRR@50 |
|---|---:|---:|---:|
| bm25 | 0.2667 | 0.4333 | 0.2455 |
| bm25_alias | 0.3000 | 0.4917 | 0.3018 |
| bge_m3 | 0.4750 | 0.6000 | 0.3918 |
| hybrid_rrf | 0.5333 | 0.5583 | 0.4490 |
| bge_m3 + reranker | 0.6250 | 0.7667 | 0.4568 |

Reranker: `BAAI/bge-reranker-v2-m3`, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`; top 50 rescored.

Simplest configuration within 0.03 Recall@10 of the best: `bge_m3`.
Smoke checks do not resolve D-02/D-03. Review the evidence and corpus quality before recording a research decision.
