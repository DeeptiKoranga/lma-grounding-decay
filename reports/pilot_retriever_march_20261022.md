# Retriever pilot

Status: **SMOKE CHECK ONLY; no research decision**.

Shared query/evidence pairs: 20. Positive passage IDs came from the supplied pair file; this runner does not certify independent annotation.
Corpus SHA-256: `7b843fe072573fe7b3d54f89af6b2128bf61abe4115b4059d57665e9638543d3`.
Pair file SHA-256: `de6c265557d352516bc97cae762e109c5e50c99c315264bc373f7748adb11f8d`.
Alias file SHA-256: `826f0e59c3ad98b2ca3d6ff08027ead08c917fed36d9d0a711cf802a1eebe843`.
Embedding: `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`.
Device: `mps`; dense backend: `faiss`; RRF constant: 60; candidate pool: 50.
Maximum input tokens: 1024; embedding batch size: 8; reranker batch size: 1.
Package versions: `{"faiss-cpu": "1.15.1", "sentence-transformers": "6.2.0", "torch": "2.14.1", "transformers": "5.20.2"}`.
Elapsed wall time: 327.29 seconds.
Cache state at start: `{"dense_index_preexisting": false, "embedding_checkpoint_preexisting": true}`. Elapsed time excludes earlier checkpoint/index precomputation.
The dense model is unloaded before the cross-encoder; first-stage candidates are cached unchanged.

| Configuration | Recall@5 | Recall@10 | MRR@50 |
|---|---:|---:|---:|
| bm25 | 0.7250 | 0.9000 | 0.5796 |
| bm25_alias | 0.6500 | 0.7250 | 0.5465 |
| bge_m3 | 0.7750 | 0.8500 | 0.7366 |
| hybrid_rrf | 0.6750 | 0.9250 | 0.6777 |
| bm25 + reranker | 0.9000 | 0.9750 | 0.8800 |

Reranker: `BAAI/bge-reranker-v2-m3`, revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`; top 50 rescored.

Simplest configuration within 0.03 Recall@10 of the best: `bm25`.
Smoke checks do not resolve D-02/D-03. Review the evidence and corpus quality before recording a research decision.

Limitations: machine-curated March convenience pairs, 29 incomplete known-positive
references, and no independent relevance review. Corpus source balance and
extraction quality still require review. Query 10 was replaced after a temporal
source audit, and three IDs migrated without changing positive text. No query
was tuned to these rankings. See `reports/pilot_pair_review.md`,
`reports/pilot_pair_id_migration.json`, and `reports/acquisition_review.md`.

Execution/cache details and saved-index reload validation are in
`reports/retrieval_run_provenance.json`. Earlier precomputation took 977.67 seconds
with an existing checkpoint; it is additional to the comparison time above.
