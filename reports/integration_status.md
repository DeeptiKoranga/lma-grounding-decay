# Integrated development pipeline — 23 October 2026

Current Track A delivery is in `reports/track_a_progress.md`. The active root
corpus is repaired v3 (1,177 documents, 28,391 passages). All six series contain
161 total observations, with sparse histories. The 42-graph assembly below
retains archived v1; audits/review preparation must explicitly select
`data/interim/frozen_v1_20261023/articles.jsonl`. Full fresh-source B0/B1/B2/M
reproduction now matches all 24 original graphs. Independent research acceptance
remains open. Current checks: 586 tests, Ruff and Black pass.

The software path now connects corpus/retrieval, model generation, extraction,
verification, tools, controller, condition configs, run logging and evaluation.
Research completion is **not** established by this implementation checkpoint.

Earlier counts in the following run sections describe the preceding v1
integration checkpoint. Current Track A versions and evidence are recorded in
the delivery report above. A corpus/retriever change requires new experiments
and corresponding review packets.

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
- Reference recall additionally requires independently reviewed, nonempty
  reference graphs with exact eligible citations and a hash-bound receipt.
  Changes to gold bytes, corpus or anchor invalidate that scoring path.
- Twenty synthetic tool faults were executed: all preserved the graph/cutoff,
  returned the expected boundary outcome and counted attempted calls. This is
  not evidence of model-led recovery. The 40 action states and 25 safety prompts
  are explicitly synthetic, not human-labelled real-run benchmarks.

## Completed local integration run

All **42 graphs** are complete: seven conditions × six source-backed, unreviewed
candidates. The assembly retains baseline commit `20389a2` and corrected agent
commit `79a1326` with their distinct source hashes; shared input hashes match.
Earlier direct-graph baselines and the interrupted old agent attempt are excluded.
This is not a single-version frozen research experiment.

The completed run logged **87 model calls**, **260,325 prompt tokens**, **37,304
completion tokens** and **188 tool calls**. Independent trace checks matched all
354 retrieved passage occurrences to trusted source bytes and the pinned cutoff;
model identity, prompt hashes, call/result pairs and budget/stop accounting pass.
All 42 graphs validate, with at most 12 tool calls each. See
`reports/integration_validation.json` and `reports/run_log_validation.json`.

Fifteen asserted-edge spans are nonverbatim: B1 eight, B1-R one, B2 three and
A-NoVerify three. These are preserved baseline/ablation outcomes, not silently
corrected support scores. No asserted M/A-NoLoop edge fails the structural
source/date/span audit. M retains eight model-verified assertions across 35
edges, with 18 inferred edges lacking a verifier verdict. A-NoLoop retains no
assertions and leaves five inferred edges without a verdict. These counts do
not measure semantic support or reference recall.

Eighteen prose corrections and a **227-edge support preview** are prepared.
Correct prose first and rebuild the final blinded support packet afterward;
do not label the preview. Reviewer identity is still unassigned. The separate
retrieval pool has 1,988 items. Actual packet locations/hashes are in
`reports/review_readiness.json`, with instructions in `reports/review_handoff.md`.

The actual M example is exported to `reports/development_example.svg` and PNG,
visually checked, and marked as awaiting independent review. No UER chart has
been fabricated. Five observed trace/extraction cases are documented in
`reports/development_failure_analysis.md`; they are not ranked human UER cases.
The completed 40-state synthetic model probe chose the expected tool in only
5/40 cases (12.5%); 34/40 calls (85%) passed schema/cutoff checks. This development diagnostic leaves D-01 open; the full two-model, five-task
pilot remains required. The executed controller uses deterministic priority.
The 25-prompt safety screen found zero regex advice/own-forecast flags; all
responses still need human adjudication. A fresh-clone B0/B1/B2/M probe on one
query completed four valid graphs, identical to the original graphs after
excluding run IDs. It reused the heavy runtime and corpus, and is not a full
frozen-gold reproduction. See `reports/capability_diagnostics.json`,
`reports/fresh_clone_validation.json` and `reports/compute_log.md`.
The earlier software gate was 547 tests (545 plus two skips in the core clone);
current verification is recorded in `reports/track_a_validation.json`.

## Research gates still open

1. Model selection: the two-model, five-task selection pilot is not complete.
   The downloaded model is for development integration, not an accepted D-01.
2. Corpus acceptance: RBI coverage, publisher balance, broader extraction review
   and reproduction terms remain incomplete. The saved corpus is a convenience
   collection with integrity checks, not a representative accepted sample.
3. Series and episodes: all six files now have observations, but Brent, benchmark
   yields, FPI and Indian basket have sparse histories with explicit measurement
   limitations. Eight
   anchor episodes have not been independently confirmed from complete series.
4. Annotation: the six new queries span six months and are source-backed, but
   remain candidates. They do not replace the planned 30-query split, six
   reviewer gold graphs, ten annotated test queries, independent support labels,
   double annotation/kappa or the public-dataset strength/direction checks.
5. Retriever/reranker acceptance: the current v3 blinded 2,062-item pool covers
   20 questions across March–September. Its human judgments are blank; the older
   March/v2 pools remain historical. D-02/D-03 remain open.
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
