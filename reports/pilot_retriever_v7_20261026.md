# Retriever pilot

Status: **SMOKE CHECK ONLY; no research decision**.

Shared query/evidence pairs: 20. Positive passage IDs came from the supplied pair file; this runner does not certify independent annotation.
Corpus SHA-256: `25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496`.
Pair file SHA-256: `7ef70e5e65dcedc1e511673fa5ec4eab4ea1709564159c3f70e507547e609438`.
Alias file SHA-256: `826f0e59c3ad98b2ca3d6ff08027ead08c917fed36d9d0a711cf802a1eebe843`.
Embedding: `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`.
Device: `cpu`; dense backend: `faiss`; RRF constant: 60; candidate pool: 50.
Maximum input tokens: 1024; embedding batch size: 8; reranker batch size: 1.
Package versions: `{"faiss-cpu": "1.15.1", "sentence-transformers": "6.2.0", "torch": "2.14.1", "transformers": "5.20.2"}`.
Elapsed wall time: 135.28 seconds.
Cache state at start: `{"dense_index_preexisting": true, "embedding_checkpoint_preexisting": false}`. Elapsed time excludes earlier checkpoint/index precomputation.
The dense model is unloaded before the cross-encoder; first-stage candidates are cached unchanged.

| Configuration | Recall@5 | Recall@10 | MRR@50 |
|---|---:|---:|---:|
| bm25 | 0.2405 | 0.3518 | 0.4555 |
| bm25_alias | 0.2211 | 0.3551 | 0.5787 |
| bge_m3 | 0.3327 | 0.4259 | 0.6981 |
| hybrid_rrf | 0.2958 | 0.4161 | 0.6663 |
| bge_m3 + reranker | 0.4072 | 0.5296 | 0.7101 |

Reranker: `BAAI/bge-reranker-v2-m3`, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`; top 50 rescored.

Simplest configuration within 0.03 Recall@10 of the best: `bge_m3`.
Smoke checks do not resolve D-02/D-03. Review the evidence and corpus quality before recording a research decision.

Unranked review candidate pool SHA-256: `2a5d124bcf6298793e624adb2296018019d56fbc099e6802488745d12cb76b19`.
Candidate pool contains the union of all four first-stage top-50 lists, without scores or relevance judgments.
