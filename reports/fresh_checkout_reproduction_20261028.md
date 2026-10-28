# Fresh-checkout reproduction — 28 October 2026

**Passed: Track A / Varun task 4.3 in PLAN_MIDSUB.md.** A clean GitHub clone at
`07f10f08870860388ec05207ecfd497f2ed8fad3` passed setup, Ruff/Black, all **663 tests**
without skips and the full `make run-dev` matrix: **B0, B1, B2 and M on all six
existing development candidates, 24 newly generated graphs**. The complete
matrix audit passed with no recorded failures or unbound logs. Repeating the
same command reused all 24 outputs without another model call.

This completes local software reproduction for the planned command. It does
not accept the development episodes, provide reviewed UER/reference recall,
complete the model pilot, or verify another laptop or Kaggle.

## Source, inputs and execution

- GitHub origin: https://github.com/DeeptiKoranga/lma-grounding-decay.git; branch `varun`.
- Fresh checkout: `/private/tmp/lma-track-a-full-reproduction-20261027`; clean before and after.
- Runtime source identity: `1edb5441d5d627ac6cf451ab6588c31d0a271482662a5e417dda34dbcf708a86`.
- Frozen v7 corpus: 1,156 documents / 16,472 passages; SHA-256
  `25ad7ad94d4e657195bdb83d0ff95b43335e6613ad3a18e0657b1da2dce38496`.
- Dense index SHA-256: `5345b8a3384f759f73a7fee6c58ef544a4ad6ad47f04262fc81efafb5e038d2c`.
- Model: `mlx-community/Qwen3-8B-4bit`, revision `545dc4251c05440727734bcd94334791f6ab0192`.
- Retrieval: pinned BGE-M3/FAISS, embedding revision
  `5617a9f61b028005a4858fdac845db406aefb181`, eligible evidence restricted by cutoff.
- Fresh core/dev environment: Python 3.12.13, created on
  27 October for this clean checkout; setup rechecked on 28 October.
  All inference source was imported from the clean checkout.

The corpus/archive and vector index were supplied separately and checksummed;
previous run outputs were not copied into the fresh run. Cached pretrained
weights and the existing native generation/retrieval environments were reused.
The pinned PDF package was installed into the fresh core environment from
unchanged local distribution files after checking all 221 file hashes and sizes
against their original package RECORD. Its dependencies came from package cache.
This checks clean source and a fresh core environment with cached native assets;
it is not a cold-machine installation.

The first redundant PDF network download was deliberately stopped after slow
progress. An attempted offline install then exposed pruned files in the older
cache. Both attempts remain recorded; the verified cached-distribution
installation, tests and all subsequent stages passed. No source repair was
needed for this reproduction.

## Measured checks

| Stage | Result | Wall seconds |
|---|---|---:|
| setup | Passed | 0.39 |
| pdf_optional_dependency | Passed | 0.66 |
| lint | Passed | 4.19 |
| tests | Passed | 7.48 |
| run_dev | Passed | 2666.02 |
| audit | Passed | 0.36 |
| resume | Passed | 2.82 |

The model-run stage took **2666.02 seconds
(44.43 minutes)**. Model-call time below is measured call
wall time, not GPU-active time. It excludes setup and failed dependency attempts.

| Condition | Graphs | Model calls | Prompt tokens | Completion tokens | Model-call seconds | Tool calls |
|---|---:|---:|---:|---:|---:|---:|
| B0 | 6 | 12 | 16,680 | 1,986 | 366.85 | 6 |
| B1 | 6 | 12 | 46,830 | 5,369 | 870.77 | 12 |
| B2 | 6 | 6 | 29,546 | 4,136 | 585.00 | 12 |
| M | 6 | 15 | 34,741 | 5,129 | 744.12 | 68 |

Totals: **45 model calls**, **127,797
prompt tokens**, **16,620 completion tokens**,
**2566.74 model-call wall seconds** and
**98 tool calls**. Summed case wall time:
**2657.26 seconds**. Invalid-JSON calls: **0**.
No paid API or Kaggle execution occurred.

## Output and trace verification

The auditor checked the declared 24-case matrix, schemas, source safety,
artifact/log hashes, run identities and budgets. An additional trace pass
checked every prompt hash, model/backend/revision, query/condition identity,
tool-call/result pair, pinned cutoff, exact retrieved corpus bytes, visibility
date and stop record. All 24 run identifiers were new; every log began after
this run started. Each case stayed within the common 12-call budget.

The baseline source screen flags **four nonverbatim citation spans across three
outputs**: B1/dev-candidate-01 (one), B1/dev-candidate-06 (one), and
B2/dev-candidate-01 (two). All six M outputs pass source/date/span checks.
The flagged baseline outputs remain unchanged for correction/support review;
successful software reproduction does not establish their evidential quality.
The machine-readable audit retains each flagged edge and its failure kind.

For the eight overlapping cases from the earlier current-v7 smoke run,
**8/8** canonical graphs match after excluding
only run identifiers. The other 16 cases were generated for this reproduction.
Historical v1 runs keep their original bindings.

Retained outputs: `runs/track_a_fresh_checkout_20261028`.
Stage logs, audit and installation receipts:
`data/interim/track_a_reproduction_20261028`.
Both remain ignored local artifacts because logs can contain corpus passages.
The public [machine-readable receipt](fresh_checkout_reproduction_20261028.json)
binds the exact source, inputs and every graph/log hash.

Task 4.3 is complete for the current local development configuration. Shared
human support/correction work, result figures and other-machine/Kaggle checks
remain separate. No human review judgment or attestation was changed. No final
mid-submission report was written, release tagged or pull request created.
