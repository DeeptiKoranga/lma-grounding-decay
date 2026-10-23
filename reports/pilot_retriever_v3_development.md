# Retriever pilot

Status: **SMOKE CHECK ONLY; no research decision**.

Shared query/evidence pairs: 20. Positive passage IDs came from the supplied pair file; this runner does not certify independent annotation.
Corpus SHA-256: `1df503a6101471a8646f6521f7c44ffbd946661ea79e63057f1bedf06c2a9164`.
Pair file SHA-256: `0133cefc4246ed15673e78c1d7efc8b7f5f0954883efcbe91dc32d92efa18f2f`.
Alias file SHA-256: `826f0e59c3ad98b2ca3d6ff08027ead08c917fed36d9d0a711cf802a1eebe843`.
Embedding: `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`.
Device: `cpu`; dense backend: `faiss`; RRF constant: 60; candidate pool: 50.
Maximum input tokens: 1024; embedding batch size: 8; reranker batch size: 1.
Package versions: `{"faiss-cpu": "1.15.1", "sentence-transformers": "6.2.0", "torch": "2.14.1", "transformers": "5.20.2"}`.
Elapsed wall time: 357.87 seconds.
Cache state at start: `{"dense_index_preexisting": false, "embedding_checkpoint_preexisting": true}`. Elapsed time excludes earlier checkpoint/index precomputation.
The dense model is unloaded before the cross-encoder; first-stage candidates are cached unchanged.

| Configuration | Recall@5 | Recall@10 | MRR@50 |
|---|---:|---:|---:|
| bm25 | 0.2667 | 0.4333 | 0.2510 |
| bm25_alias | 0.3250 | 0.5167 | 0.3211 |
| bge_m3 | 0.4750 | 0.6000 | 0.3957 |
| hybrid_rrf | 0.5083 | 0.5833 | 0.4600 |
| bge_m3 + reranker | 0.6500 | 0.7667 | 0.4818 |

Reranker: `BAAI/bge-reranker-v2-m3`, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`; top 50 rescored.

Simplest configuration within 0.03 Recall@10 of the best: `bge_m3`.
Smoke checks do not resolve D-02/D-03. Review the evidence and corpus quality before recording a research decision.

Unranked review candidate pool SHA-256: `57cfa38c7a69dd0c6a4f4bf38424675793de4f5e1f05d8832b5e9ae2f0091acd`.
Candidate pool contains the union of all four first-stage top-50 lists, without scores or relevance judgments.
