# Retriever pilot

Status: **SMOKE CHECK ONLY; no research decision**.

Shared query/evidence pairs: 20. Positive passage IDs came from the supplied pair file; this runner does not certify independent annotation.
Corpus SHA-256: `7b843fe072573fe7b3d54f89af6b2128bf61abe4115b4059d57665e9638543d3`.
Pair file SHA-256: `4eac1ee09440efaf1c9c947e781bc44f730c965dd78bdd7b856a21784bc11536`.
Alias file SHA-256: `826f0e59c3ad98b2ca3d6ff08027ead08c917fed36d9d0a711cf802a1eebe843`.
Embedding: `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`.
Device: `cpu`; dense backend: `faiss`; RRF constant: 60; candidate pool: 50.
Maximum input tokens: 1024; embedding batch size: 8; reranker batch size: 1.
Package versions: `{"faiss-cpu": "1.15.1", "sentence-transformers": "6.2.0", "torch": "2.14.1", "transformers": "5.20.2"}`.
Elapsed wall time: 137.61 seconds.
Cache state at start: `{"dense_index_preexisting": true, "embedding_checkpoint_preexisting": false}`. Elapsed time excludes earlier checkpoint/index precomputation.
The dense model is unloaded before the cross-encoder; first-stage candidates are cached unchanged.

| Configuration | Recall@5 | Recall@10 | MRR@50 |
|---|---:|---:|---:|
| bm25 | 0.3083 | 0.4333 | 0.2952 |
| bm25_alias | 0.3500 | 0.4917 | 0.3526 |
| bge_m3 | 0.5250 | 0.6000 | 0.4930 |
| hybrid_rrf | 0.5583 | 0.6500 | 0.4944 |
| hybrid_rrf + reranker | 0.6875 | 0.7542 | 0.5471 |

Reranker: `BAAI/bge-reranker-v2-m3`, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`; top 50 rescored.

Simplest configuration within 0.03 Recall@10 of the best: `hybrid_rrf`.
Smoke checks do not resolve D-02/D-03. Review the evidence and corpus quality before recording a research decision.

Unranked review candidate pool SHA-256: `2ab52892517cdb9f46ac9ef992b1e58d9b3d8ad0985ede9b1e1df9e4ab8a358b`.
Candidate pool contains the union of all four first-stage top-50 lists, without scores or relevance judgments.
