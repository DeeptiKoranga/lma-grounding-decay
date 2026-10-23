# Integrated development pipeline — 23 October 2026

The software path now connects corpus/retrieval, model generation, extraction,
verification, tools, controller, condition configs, run logging and evaluation.
Research completion is **not** established by this implementation checkpoint.

## Implemented and checked

- The existing Track B deterministic verifier and its 100 tests were integrated
  from commit `f788c7a` on `origin/b/verifier-rules`. Its original ownership and
  implementation are credited here; they were not independently reimplemented.
- A measured MLX interface runs pinned Qwen3-8B locally. Explicit local
  llama.cpp/vLLM and compatible API transport adapters share the interface;
  remote use requires explicit opt-in and no paid request was made.
- Baselines B0/B1/B1-R generate prose, then mechanically extract its links.
  B2 requests provenance labels. A-NoVerify, A-NoLoop and M use the same path
  with verification/loop flags. Every retrieved condition shares plain BM25
  for this development run; B1-R adds the pinned cached cross-encoder.
- The six tools validate arguments, pin the cutoff, reject forged backend
  passages and enforce at most 12 calls. Verified assertions require a matching
  fresh semantic verification result. Graph mutations regenerate BFS hops and
  bounded simple paths with weakest-link labels.
- Logs retain prompts, completions, actual token counts, call wall times,
  typed tool calls/results, state and stop records. Output/resume hashes bind
  the inputs and source code; failed attempts remain visible.
- UER, strength inflation, provenance accuracy, supported established reference
  recall and strict path validity are sliced by hop and macro averaged across
  queries. Zero denominators remain null. The two predeclared paired query
  contrasts are implemented for UER and strength inflation.
- Independent support review, prose-extraction correction, agreement and
  challenge-generation gates are available. The local review page uploads
  nothing. Scores cannot be exported from missing/partial support judgments or
  uncorrected prose baselines. UER figures reject unreviewed results.
- Twenty synthetic tool faults were executed: all preserved the graph/cutoff,
  returned the expected boundary outcome and counted attempted calls. This is
  not evidence of model-led recovery. The 40 action states and 25 safety prompts
  are explicitly synthetic, not human-labelled real-run benchmarks.

The first real-model integration probe produced a six-edge RAG graph with an
actual logged model call. A preliminary direct-graph sweep was interrupted
after detecting its mismatch with the proposal's prose baselines. It remains
local under `runs/development_20261023` and is excluded from comparisons.
The corrected sweep is under `runs/development_prose_20261023`; its completion
audit and compute report are separate artifacts. No hypothesis result is
claimed from either unreviewed run.

## Research gates still open

1. Model selection: the two-model, five-task selection pilot is not complete.
   The downloaded model is for development integration, not an accepted D-01.
2. Corpus acceptance: RBI coverage, publisher balance, broader extraction review
   and reproduction terms remain incomplete. The saved corpus is a convenience
   collection with integrity checks, not a representative accepted sample.
3. Series and episodes: Brent, identified benchmark 10-year yields and accepted
   FPI values remain unavailable; Indian basket coverage is partial. Eight
   anchor episodes have not been independently confirmed from complete series.
4. Annotation: the six new queries span six months and are source-backed, but
   remain candidates. They do not replace the planned 30-query split, six
   reviewer gold graphs, ten annotated test queries, independent support labels,
   double annotation/kappa or the public-dataset strength/direction checks.
5. Retriever/reranker acceptance: a blinded 1,988-item retrieval pool is prepared,
   but its human judgments are blank and its queries are March-only. D-02/D-03
   remain open. The new temporal candidates do not retroactively fix that pilot.
6. Results: human correction of baseline extraction and blinded support review
   are required before reporting UER or strength inflation. The recall guard
   also needs independently reviewed reference graphs. No zero-denominator
   shortcut or verifier self-judgment is accepted as research truth.
7. Deployment/reproduction: the Kaggle notebook is an unexecuted handoff template;
   all-laptop and Kaggle verification remain open. A fresh-clone local check is
   reported separately and cannot certify other machines or a frozen gold sweep.
8. TA decisions D-05/D-06/D-07 and final report acceptance are still human decisions.

These gates require actual data, judgments or decisions. The implementation
does not fabricate them or mark the corresponding research issues complete.
