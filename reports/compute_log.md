# Compute log — 23 October 2026

Actual completed-call usage from validated local logs. All generation used pinned
Qwen3-8B 4-bit revision `545dc4251c05440727734bcd94334791f6ab0192` under MLX.
No paid API requests were made. No Kaggle job was executed and no Kaggle GPU
hours are claimed. Token counts are backend-reported; times below are measured
model-call wall times, **not GPU-active hours or total device/runtime expense**.

## Included seven-condition development assembly

| Condition | Graphs | Model calls | Prompt tokens | Completion tokens | Model-call seconds | Tool calls |
|---|---:|---:|---:|---:|---:|---:|
| A-NoLoop | 6 | 8 | 29,909 | 4,458 | 554.21 | 72 |
| A-NoVerify | 6 | 14 | 55,904 | 9,705 | 1035.32 | 27 |
| B0 | 6 | 12 | 16,680 | 1,986 | 312.78 | 0 |
| B1 | 6 | 12 | 45,255 | 5,360 | 674.65 | 6 |
| B1-R | 6 | 12 | 45,907 | 5,805 | 765.88 | 6 |
| B2 | 6 | 6 | 28,847 | 4,209 | 692.36 | 6 |
| M | 6 | 23 | 37,823 | 5,781 | 710.48 | 71 |
| **Total** | **42** | **87** | **260,325** | **37,304** | **4745.68** | **188** |

The baseline phase and corrected controller phase retain different source hashes
and identical shared input hashes in `runs/development_complete_20261023/phases.json`.
The assembly is unreviewed development work. B1-R cross-encoder work runs in a
separate cached CPU worker; it is not included in generator/verifier token or
model-call totals. Summed case wall times include retrieval/worker overhead:

- A-NoLoop: 554.71 case wall seconds.
- A-NoVerify: 1039.28 case wall seconds.
- B0: 313.42 case wall seconds.
- B1: 675.70 case wall seconds.
- B1-R: 851.90 case wall seconds.
- B2: 692.93 case wall seconds.
- M: 714.76 case wall seconds.

These sums exclude model/index loading and idle time between cases/phases; they
must not be treated as GPU-active time. Original timestamps remain in the logs.

## Additional measured local work

| Work | Model calls | Prompt tokens | Completion tokens | Model-call seconds |
|---|---:|---:|---:|---:|
| 40 action and 25 safety synthetic probes | 65 | 160,470 | 4,234 | 1765.61 |
| Fresh-clone four-condition, one-query probe | 9 | 21,409 | 3,406 | 415.28 |
| Excluded first integration probe | 1 | 4,731 | 764 | 70.21 |
| Excluded preliminary direct-graph sweep | 5 | 12,269 | 1,763 | 172.60 |
| Excluded interrupted old agent attempt | 0 | 0 | 0 | 0.00 |

An interrupted in-flight generation has no completed response/usage record. Its
unmeasured work is not filled with an estimate, so these are not all-device totals.
Excluded runs never enter support comparisons. Synthetic probes have no human
support labels and no synthetic safety certification is claimed.

## Retrieval and downloaded artifacts

The earlier BGE-M3 precomputation phase recorded 977.67 seconds; the corrected
full-corpus comparison recorded 327.29 seconds, with cached work reused. Their
sum, 1,304.96 seconds, excludes downloads, previous checks and the saved-index
reload. See `reports/retrieval_run_provenance.json` for exact scope and hashes.

The local generator/tokenizer files total 4,623,782,544 bytes; file hashes and
runtime versions are in `reports/generator_provenance.json`. Raw weights, corpus,
vectors and full logs remain ignored. Heavy dependency versions are pinned in
`configs/requirements-local-llm.txt` and `configs/requirements-retrieval.txt`.

The 20 synthetic faults are boundary tests, not GPU model-recovery runs. The
fresh probe reuses the local model runtime and corpus with fresh-clone source
code; it does not establish an all-laptop/Kaggle or full frozen-gold sweep.
