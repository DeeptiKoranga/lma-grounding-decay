# Gold-backed development sweeps — 10 November 2026

Both pre-registered D-28 arms completed on Varun's local machine using the four
gold-backed development queries and the current v7 corpus. These are execution
results, not reviewed UER or hypothesis results.

| Arm | Model revision | Graphs | Structural audit | Generated edges | Established edges | Model calls | Prompt / completion tokens | Model-call wall time |
|---|---|---:|---|---:|---:|---:|---:|---:|
| Primary, `runs/dev-gold-qwen3-8b` | `545dc4251c05440727734bcd94334791f6ab0192` | 28/28 | passed, 0 failures | 166 | 111 | 54 | 167,497 / 26,628 | 3,916.6 s |
| Sensitivity, `runs/dev-gold-qwen35-9b` | `8b2b98c00a6b4d291155e4890773ca8f769aee53` | 28/28 | passed, 0 failures | 109 | 74 | 67 | 165,644 / 23,221 | 3,047.8 s |

Each arm has four successful graphs for every condition: B0, B1, B1-R, B2,
A-NoVerify, A-NoLoop and M. The full per-artifact audits are
`dev_gold_qwen3-8b_audit.json` and `dev_gold_qwen35-9b_audit.json` in this
directory. The model-call times are summed measured call times, excluding
retrieval, setup, model loading, idle time and earlier index creation.

The bound `inputs.json` records differ only in `model`, `revision` and
`local_model_files`. Corpus, query file, dense index, selected retriever,
conditions, source-code hash and runtime identity are identical. The corpus
SHA-256 is `25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496`,
matching the signed dev reference receipt. The dense index SHA-256 is
`5345b8a3384f759f73a7fee6c58ef544a4ad6ad47f04262fc81efafb5e038d2c`.

| Local ignored run record | SHA-256 |
|---|---|
| Primary `inputs.json` | `006a8d9dcb52c3b685b9ae2a6f908c699f5d2630e024fee1a05a6eb2d8bfe143` |
| Primary `artifacts.json` | `039ddc659ccb4b3ff1c0cf3c2f35d3380450d6c92f29c52f03799444b51ccd67` |
| Sensitivity `inputs.json` | `3b470b2f3ba24154899bddfaf3f18bd92ebb5e72c35084f598ebee84f6229c13` |
| Sensitivity `artifacts.json` | `9c8a4227810e401e940b777ac5bab926c32a9f1da37bec2afa2a4abf7b7c2b32` |

The local files `data/interim/prose_correction_qwen3-8b_20261110.json` and
`data/interim/prose_correction_qwen35-9b_20261110.json` contain 12 baseline
answers each for faithful prose-to-graph correction. They are unfilled review
packets preserved from before review. Varun's completed correction and support
review, official scores, RQ reports, UER chart and five-case failure analysis
are recorded in `dev_gold_varun_review_20261110.md`. No metric was inferred
from the original unreviewed graph labels.
