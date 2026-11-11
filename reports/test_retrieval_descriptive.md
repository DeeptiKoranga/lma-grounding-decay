# Descriptive retrieval on the signed FPI test references

Two queries share one episode. Recall uses the distinct adjudicated evidence passage IDs
per query. MRR@50 uses the first relevant passage. Means weight each query equally.
Other relevant passages may exist outside the signed references.

| Configuration | Query | Relevant passages | Recall@5 | Recall@10 | MRR@50 |
|---|---|---:|---:|---:|---:|
| BGE-M3 | test-fpi-why | 2 | 0.000 | 0.500 | 0.167 |
| BGE-M3 | test-fpi-effects | 2 | 0.000 | 0.000 | 0.000 |
| BGE-M3 | mean (n=2) | | 0.000 | 0.250 | 0.083 |
| BGE-M3 + top-50 cross-encoder | test-fpi-why | 2 | 0.000 | 0.000 | 0.053 |
| BGE-M3 + top-50 cross-encoder | test-fpi-effects | 2 | 0.000 | 0.000 | 0.000 |
| BGE-M3 + top-50 cross-encoder | mean (n=2) | | 0.000 | 0.000 | 0.026 |

Reference receipt `3d68111a038f549e7bc1c815da86708e5410c9f85d5874bcacb58de2e6415bd8`.
Query manifest `6160ccca0846eacc63a73aab5bcbca36da5e3cee9e67dfd2e1ff8446c1d26e6a`.
Corpus `25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496`.
Dense index `5345b8a3384f759f73a7fee6c58ef544a4ad6ad47f04262fc81efafb5e038d2c`.
Aliases `826f0e59c3ad98b2ca3d6ff08027ead08c917fed36d9d0a711cf802a1eebe843`.
BGE-M3 revision `5617a9f61b028005a4858fdac845db406aefb181`. Reranker revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`.

This report measures passage ranking for the signed FPI queries.
