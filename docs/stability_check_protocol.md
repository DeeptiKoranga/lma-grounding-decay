# Development stability check for issue #61

Declared before running the repeats on 10 November 2026.

- Query: `dev-oil-effects` from `data/eval/queries_dev.jsonl`, unchanged.
- Condition: `M` only.
- Primary model: pinned `mlx-community/Qwen3-8B-4bit`, revision
  `545dc4251c05440727734bcd94334791f6ab0192`.
- Corpus, series, aliases, BGE-M3/FAISS dense index, retriever configuration,
  prompt templates, as-of date and pipeline are the same as the primary D-28
  development arm. Only decoding changes from greedy to temperature 0.7, with
  seeds `1101`, `1102`, `1103` in separate processes.
- Report proposed and established edge counts, normalized established-edge
  identities, model-call time, and whether the three sets match. If support
  labels can be legitimately applied to repeat edges, report UER with its
  denominator; otherwise say it is unavailable, without filling labels from
  the verifier's self-assessment.
- The three repeats are a descriptive stability check, not a new estimate of
  the population mean or a replacement for the pre-registered greedy arm.
