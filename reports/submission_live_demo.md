# Model-backed submission demo

12 November 2026. Fresh execution of all seven conditions on the signed development
query `dev-oil-why`, with an 8 April cutoff and explicit Brent threshold. The run
used the pinned Qwen3-8B MLX weights, frozen v7 passages, BGE-M3 FAISS index and
the pinned top-50 cross-encoder in B1-R. The [reproduction instructions](../docs/reproduction.md#run-the-model-backed-demo)
show the command and the required local assets.

**7/7 graphs completed.** Input binding, artifact and log checks passed. Every
run confirmed its anchor under the new manifest. No retrieved passage in any
logged search exceeded the cutoff. The live graph viewer was generated from M.

| Condition | Edges | Established by condition | Tool calls | Structural citation flags |
|---|---:|---:|---:|---:|
| A-NoLoop | 6 | 1 | 12 | 0 |
| A-NoVerify | 6 | 6 | 10 | 0 |
| B0 | 6 | 5 | 1 | 0 |
| B1 | 4 | 4 | 2 | 0 |
| B1-R | 3 | 3 | 2 | 2 |
| B2 | 6 | 6 | 2 | 0 |
| M | 6 | 2 | 12 | 0 |

M exercised the competing-cause search, targeted search, semantic verifier and
graph update. Its two established edges passed structural checks. B1-R emitted
two nonverbatim spans. Both are kept as observed baseline failures, and neither
is counted as an independently supported result. This engineering run does not
change the scored development arms or add a held-out support result.

- Model revision `545dc4251c05440727734bcd94334791f6ab0192`.
- Corpus SHA-256 `25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496`.
- Dense index SHA-256 `5345b8a3384f759f73a7fee6c58ef544a4ad6ad47f04262fc81efafb5e038d2c`.
- Bound input SHA-256 `9d7e26f6750beffbd5d64e2f7bbbff7e1c844246ae398ac55e314e8c6f72bb83`.
- Artifact receipt SHA-256 `134da4e5587da89ecd91944efa27f62f07b4d97be472dc946d25c12e340b1460`.
- Recorded runtime-source SHA-256 `18dd989cf153b9b64dcb644a6f59f330bfd463fd80db91502a5bd0dcb565fc32`.

The live runner used the production source recorded above. The only subsequent
source-package change for the submission demo was adding a fixture-only log
backend label. Raw traces and the licensed-corpus viewer remain local.
