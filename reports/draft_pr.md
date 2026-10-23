# Integrate dated corpus and seven-condition development pipeline

The scaffold could validate records but could not run the planned conditions against a real dated corpus. This change connects source acquisition, retrieval, local generation, extraction, verification, bounded repair and evaluation through one pipeline. B0/B1/B1-R generate prose before extraction; human correction and independent support/reference review are required before final scoring.

The development checkpoint completes 42 graphs over six unreviewed candidates using pinned local Qwen3-8B weights and shared BM25 retrieval. Baseline and corrected controller phases retain distinct source hashes and matching shared input hashes. Raw corpus/model/run payloads remain outside git. Fifteen quotation mismatches in unverified conditions remain visible as experimental outcomes; verified assertions pass structural source/date/span checks.

Validation: 547 tests, Ruff and Black pass. A core-only fresh clone passes 545 tests with two optional-library skips. All 42 graphs and 188 actual tool calls pass graph, cutoff, trusted-source and budget/accounting checks. Twenty synthetic boundary faults pass. The separate synthetic model probe chooses only 5/40 expected tools, with 34/40 schema/cutoff-valid calls. Its 25 safety responses have no regex flags and remain unreviewed. A fresh-clone one-query B0/B1/B2/M probe reproduces all four canonical graphs while reusing the heavy runtime and corpus.

Research acceptance remains open: model/retriever selection, broader corpus review, missing series, confirmed episodes, independent gold/annotation, prose correction, blinded support judgments, agreement and TA decisions. No human UER, strength inflation, recall result, accepted model selection or Kaggle execution is claimed. See `reports/integration_status.md`, `reports/mid_submission_draft.md`, `reports/compute_log.md` and `docs/reproduction.md`.

The deterministic Track B verifier and its tests are integrated from `origin/b/verifier-rules` commit `f788c7a`, with attribution retained in the integration report. Added Track B/C components are development integrations for review, not claims of teammate acceptance.
