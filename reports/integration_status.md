# Integrated development pipeline — updated 30 October 2026

**Current Track C disposition — 30 October:** all Phase 1 C1–C11 deliverables
are complete. The project-schema pilot resolves D-01 to `mlx-community/Qwen3-8B-4bit` at
`545dc4251c05440727734bcd94334791f6ab0192`; all 200 raw case scores reproduce.
The selected model's 25-response safety evaluation covers all four risks with
explicit assistant review. A fresh private Kaggle run completed all 14 graphs
and cached all 14 on resume, using 1.211103 measured allocated GPU-hours.
Native Windows, Ubuntu and macOS each pass 724 tests without skips, plus
Ruff and notebook-inclusive Black. See [the closeout](phase1_track_c_closeout_20261030.md).
The dated development history below retains its original model/source scope.
Independent gold/support judgments, full scientific sweeps and headline UER
remain later-phase requirements.

**Fresh-checkout update — 28 October:** Track A / Varun task 4.3 is complete
for the local development configuration. A clean GitHub checkout passed setup,
Ruff/Black and **663 tests with no skips**, then generated **24/24 new graphs**
(B0/B1/B2/M × six current-v7 candidates). Full audit, independent trace checks
and unchanged resume (24 cached, no new model calls) passed. Cached model weights,
native inference environments and the verified PDF distribution were reused;
other laptops/Kaggle remain unverified. See
[fresh-checkout evidence](fresh_checkout_reproduction_20261028.md).

**Latest engineering check:** all five findings from the original audit are
fixed. The command uses the selected BGE-M3/FAISS first stage, performs logged
series checks, rejects stale resumes and incomplete sweeps, and installs its
default verifier alias resource. The suite passes 663 tests, Ruff and Black.
See [fix validation](integration_fixes_20261027.md). The actual selected-configuration
smoke completed all 14 graphs (two development candidates × seven conditions),
passed the complete-matrix audit and reused all 14 results on unchanged resume.
Experiment acceptance still requires the research gates below; the original
audit remains historical.

The scoped Track A development handoff is closed under
`reports/track_a_mid_submission_scope_20261027.md`. Reduced publisher coverage,
narrative-only PDFs and sparse original-vintage series are documented delivery
deviations. Varun's user-declared independent/blinded Track A review now passes
record validation. The experiment gates below remain open; this does not close
the other tracks or the full mid-submission.

Current Track A delivery: **v7 narrative development**, 1,156 documents and
16,472 passages, with a rebuilt pinned dense index. The new 2,035-item source
review is complete (195 relevant, 1,840 irrelevant); separate completed records
now validate on Varun's attestations. Dense retrieval has Recall@10 0.4259 and
0.5296 after top-50 reranking. See `reports/track_a_progress.md`.

The clean 28 October checkout passes **663 tests**, Ruff and Black. Earlier
637-test and 659-test/four-skip environment checks remain historical evidence.
The earlier clean-source reparse reproduces the v7 corpus/archive hashes.
Historical tools retain 161 original series
observations; the separate 317-observation October snapshot is excluded at
March–September cutoffs. New review delivery contains wholly blank human
judgments; the gates reject blank exports.

The 23 October run evidence below remains **v1**, with its archived corpus and
old shared settings. The 28 October reproduction above uses the current v7
corpus. No historical run is relabelled as a v7 experiment. Independent human
support/reference labels, corrected baselines, accepted anchors and final UER
remain separate research requirements.

The user identifies the reviewer as Varun, gives 27 October 2026 as the review
date and explicitly attests independence and blinding. Both completed-record
exports pass schemas, packet bindings, coverage and exact spans. Original
automated-label provenance and the initially supplied files remain preserved;
user-declared review conduct and timing are not independently verified. Experiment
support review and main hypothesis findings remain separate. See
`reports/track_a_reviewer_identity_20261027.json`; the initial rejection remains
historical in `reports/track_a_submitted_review_validation_20261027.json`.

## Implemented and checked

- The existing Track B deterministic verifier and its 100 tests were integrated
  from commit `f788c7a` on `origin/b/verifier-rules`. Its original ownership and
  implementation are credited here; they were not independently reimplemented.
- A measured MLX interface runs pinned Qwen3-8B locally. Explicit local
  llama.cpp/vLLM and compatible API transport adapters share the interface;
  remote use requires explicit opt-in and no paid request was made.
- Baselines B0/B1/B1-R generate prose, then mechanically extract its links.
  B2 requests provenance labels. A-NoVerify, A-NoLoop and M use the same path
  with verification/loop flags. Archived v1 runs shared plain BM25. New runs share the selected BGE-M3/FAISS
  first stage; B1-R adds the pinned cached top-50 cross-encoder.
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
5/40 cases (12.5%); 34/40 calls (85%) passed schema/cutoff checks. This historical
diagnostic did not resolve D-01; the completed 30 October project-schema pilot
and decision are recorded above. The executed controller uses deterministic priority.
The 25-prompt safety screen found zero regex advice/own-forecast flags; all
responses were subsequently reviewed across all four risks with explicit
assistant provenance; independent human certification is not claimed.
A fresh-clone B0/B1/B2/M probe on one
query completed four valid graphs, identical to the original graphs after
excluding run IDs. It reused the heavy runtime and corpus, and is not a full
frozen-gold reproduction. See `reports/capability_diagnostics.json`,
`reports/fresh_clone_validation.json` and `reports/compute_log.md`.
The earlier software gate was 547 tests (545 plus two skips in the core clone);
current verification is recorded in `reports/track_a_validation_20261026.json`.

## Research gates still open

1. Corpus acceptance: RBI coverage, publisher balance, broader extraction review
   and reproduction terms remain incomplete. The saved corpus is a convenience
   collection with integrity checks, not a representative accepted sample.
2. Series and episodes: all six historical files have observations, but Brent, benchmark
   yields, FPI and Indian basket have sparse histories with explicit measurement
   limitations. Eight
   anchor episodes have not been independently confirmed from complete original-vintage series.
   The separate October-captured backfills cover all seven months with explicit
   measurement differences; they cannot repair historical availability or daily
   resolution gaps automatically.
3. Annotation: the six new queries span six months and are source-backed, but
   remain candidates. They do not replace the planned 30-query split, six
   reviewer gold graphs, ten annotated test queries, independent support labels,
   double annotation/kappa or the public-dataset strength/direction checks.
4. Retriever/reranker acceptance: the current v7 2,035-item pool covers 20
   questions across March–September. Development judgments and dense/reranker
   selection are complete; separate records now carry Varun's explicit
   independent/blinded review attestations and validate successfully. Original
   blank v7/v3 workspaces remain unchanged. This is recorded-attestation
   acceptance, not independent verification of procedure or end-to-end benefit.
5. Results: human correction of baseline extraction and blinded support review
   are required before reporting UER or strength inflation. The recall guard
   also needs independently reviewed reference graphs. No zero-denominator
   shortcut or verifier self-judgment is accepted as research truth.
6. Frozen research reproduction remains separate: native three-platform tests
   and the 14-graph Kaggle engineering execution now pass. They do not certify
   a reviewed-gold experiment or every team laptop configuration.
7. TA decisions D-05/D-06/D-07 and final report acceptance are still human decisions.

These gates require actual data, judgments or decisions. The implementation
does not fabricate them or mark the corresponding research issues complete.
