# Retriever pilot

Status: **SMOKE CHECK ONLY; no research decision**.

Shared query/evidence pairs: 20. Positive passage IDs came from the supplied pair file; this runner does not certify independent annotation.
Corpus SHA-256: `24c925d01e6d3b5515962ff9b732341f76c5ee23a440bf6e011f8243ad46f9c6`.
Pair file SHA-256: `d4db13ec3fc5d76fe483be6d05c6bb3780f55187e33d5b77633eeb03af07a4be`.
Alias file SHA-256: `826f0e59c3ad98b2ca3d6ff08027ead08c917fed36d9d0a711cf802a1eebe843`.
Embedding: `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`.
Device: `cpu`; dense backend: `faiss`; RRF constant: 60; candidate pool: 50.
Maximum input tokens: 1024; embedding batch size: 8; reranker batch size: 1.
Package versions: `{"faiss-cpu": "1.15.1", "sentence-transformers": "6.2.0", "torch": "2.14.1", "transformers": "5.20.2"}`.
Elapsed wall time: 147.33 seconds.
Cache state at start: `{"dense_index_preexisting": true, "embedding_checkpoint_preexisting": false}`. Elapsed time excludes earlier checkpoint/index precomputation.
The dense model is unloaded before the cross-encoder; first-stage candidates are cached unchanged.

| Configuration | Recall@5 | Recall@10 | MRR@50 |
|---|---:|---:|---:|
| bm25 | 0.2624 | 0.3751 | 0.4555 |
| bm25_alias | 0.2334 | 0.3718 | 0.5454 |
| bge_m3 | 0.3740 | 0.4506 | 0.6981 |
| hybrid_rrf | 0.3231 | 0.4319 | 0.6663 |
| bge_m3 + reranker | 0.4363 | 0.5583 | 0.7101 |

Reranker: `BAAI/bge-reranker-v2-m3`, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`; top 50 rescored.

Simplest configuration within 0.03 Recall@10 of the best: `bge_m3`.
Smoke checks do not resolve D-02/D-03. Review the evidence and corpus quality before recording a research decision.

Unranked review candidate pool SHA-256: `6a3930794c41687fe85ea937aebd1fe81aefecda9144cca65dd8500da762e4b5`.
Candidate pool contains the union of all four first-stage top-50 lists, without scores or relevance judgments.
