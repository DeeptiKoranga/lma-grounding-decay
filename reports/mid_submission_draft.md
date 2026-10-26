# Mid-submission working draft — updated 27 October 2026

**Status: implementation checkpoint; research results and team acceptance pending.**
This is a working draft for the 30 October submission, not a finished report or
an accepted experimental freeze. The study asks whether unsupported established
edges increase with distance from an anchor, and whether targeted verification
and retrieval reduce that rate without losing supported reference edges.

Track A's current delivery is recorded in `reports/track_a_progress.md`: an
active v7 narrative development corpus of 1,156 documents and 16,472 passages,
a rebuilt dense index, and complete source judgments for the 2,035-item new
retrieval pool (195 relevant, 1,840 irrelevant). The 20-question development
comparison selects dense retrieval: Recall@10 0.4259, or 0.5296 with reranking.
These are single Codex judgments with prior exposure to results, not independent
human research scores. The saved human-review forms remain blank; the reported
completion is documented below.

The current checkout and a new clean environment with optional PDF/extraction
dependencies pass 637 tests. The earlier committed-source reparse reproduces all corpus
and archive hashes. All six series retain 161 original observations; the
317-observation October snapshot is available only for retrospective checks.
Original-vintage gaps, inaccessible publishers and source permissions are
explicit limitations. Existing 42-graph outputs and the 24-graph reproduction
retain archived v1; they are not v7 experiments. Final support/UER figures
still require reconciliation of the completed experiment-review records.

The subsequent official-source audit checks all 61 retained PDF file versions
and seven SEBI annexures. Five dated total-FPI candidates remain separate
because they include mutual-fund investment beyond the existing series. Dated
primary announcements now support April's domestic ATF announcement and the
August RBI meeting; this supplies Track B evidence, not independent anchor
acceptance. See `reports/track_a_followup_20261026.json`.

## Human review report — 27 October

The user confirms completing both the corpus/retrieval review and review of
experiment results, and reports that the outcome matched the hypothesis. This
is a user-reported qualitative conclusion. Completed review records, reviewed
packet/run versions, numerical results and review attestations have not yet
been reconciled with this checkout. Existing metrics retain their documented
provenance. No hypothesis effect size, significance test, agreement value or
final human-reviewed score is inferred from this summary. See
`reports/track_a_human_review_status_20261027.json`.

## What is built

The current development corpus contains 1,156 documents (1,095 news, 61 official)
and 16,472 passages spanning March–September 2026. Frozen passage offsets, corpus identity
and publication cutoffs are checked. Plain/alias BM25, pinned BGE-M3 dense and
hybrid retrieval, FAISS and the pinned cross-encoder have real cached-model
execution evidence. The corpus remains concentrated in Economic Times and
BusinessLine; RBI coverage and publisher balance are incomplete.

One pipeline implements seven conditions over the same development model and
first-stage BM25 retrieval. B0/B1/B1-R produce prose before mechanical graph
extraction; B2 emits its own provenance labels; M and the ablations toggle the
verifier and repair loop. The local model is Qwen3-8B at 4-bit, immutable revision
`545dc4251c05440727734bcd94334791f6ab0192`. Its use establishes integration,
not the still-open two-model selection decision.

Generation is greedy at temperature zero with thinking disabled, a 12,000-token
input limit, up to 700 tokens for baseline prose and 1,800 for extraction.
Retrieved conditions initially request eight passages and pack whole passages
within 16,000 characters. B1-R reranks the same first-stage top-50 candidates.
The prompt requests at most six links; the extraction schema permits twelve,
so extra model links are retained for review rather than silently discarded.
Graphs are bounded to four hops. The 12-call tool budget includes retrieval,
verification, graph updates and the stop tool; model calls are logged separately.

The executed controller uses deterministic shallow-edge priority; separate
synthetic probes test model tool selection. The six typed tools enforce the
query cutoff, trusted passage identity and a 12-call budget. A fresh-context
semantic verifier follows deterministic source, date, variable and quotation
checks. Graph updates recompute shortest BFS hops
and weakest-link paths. Actual model tokens, prompts, completions, tool outcomes,
latencies and stop states are logged. Baseline source errors remain visible for
review rather than being silently repaired before comparison.

Human correction, blinded support scoring, reference recall, agreement,
challenge generation, query-paired bootstrap and reviewed-only UER figures are
implemented. Missing labels and zero denominators cannot become successful
research scores. The guide and local review page are ready; the user-reported
completed review awaits its supporting records and attestations.

## Evidence available now

- Current checkout: 637 tests pass; Ruff and Black pass. Fresh-clone checks
  and their source commits are recorded in `reports/track_a_clean_reproduction_20261026.json`.
- Historical v3 retrieval comparison on 20 March–September questions:
  Recall@10 is 0.4333 BM25, 0.5167 alias BM25, 0.6000 dense, 0.5833 hybrid and
  0.7667 dense plus reranking. These incomplete machine seeds cannot settle
  D-02/D-03. Historical March results remain separate.
- A separate Codex source audit retained 37 of the 43 seeds as direct answers,
  rejected four background/outcome-only passages and left two uncertain. The
  rerun on the same 20 questions gave Recall@10 of 0.4333 BM25, 0.4917 alias,
  0.6000 dense, 0.5583 hybrid and 0.7667 dense plus reranking. This is a
  development sensitivity check, not independent human annotation or full-pool
  acceptance. The attempted local Qwen pool screen was rejected after source
  inspection; its labels were not used.
- The model chose the expected next tool on 5/40 scripted states (12.5%);
  34/40 calls (85%) passed schema/cutoff checks. This weak synthetic result
  keeps model/prompt selection open; it does not evaluate the executed
  deterministic controller or human-reviewed real-run states.
- Twenty executed synthetic tool faults preserve the graph and cutoff, count
  attempted calls and produce the expected typed boundary outcome. Model-led
  fault recovery has not been established by this test.
- All six series have 161 observations: CPI 7, FX 141, basket 2, Brent 4,
  benchmark yields 6 and FPI 1. The new latter three use precise dated archived
  news vintages, not complete official histories. Units, timing and benchmark
  identities are recorded; no missing value is filled. Unverified dynamic CDSL
  and undated FBIL candidates remain excluded.
- A separate retrospective snapshot contains 317 observations: original CPI 7
  and FX 141, Brent vendor continuous financial-futures daily closes 148, and
  monthly PPAC basket, OECD/FRED main ten-year yield and CDSL FPI seven each.
  The new histories cover March–September but have verified October capture
  dates, not invented historical release dates. An offline replay reproduces
  all six CSV hashes; the read layer excludes every new backfill at September
  cutoffs. Monthly values and different Brent/yield definitions limit episode
  confirmation. `reports/series_coverage_20261025.png` visualizes both stores.

The seven-condition run completed all 42 graphs and 227 edges. It logged 87
model calls and 188 tool calls; graph and recorded-trace checks pass. Fifteen
asserted spans in the unverified baselines/ablation fail exact quotation
matching. M retains eight model-verified assertions, with 18 inferred edges
without a verifier verdict. These are structural/model counts, not support
accuracy. The 25-prompt safety screen found no regex advice/own-forecast flags;
all responses await human adjudication. A full fresh-clone-source sweep completed
B0/B1/B2/M across all six candidates with 24/24 matching canonical graphs,
reusing the local heavy runtime, v1 corpus and original three series. Compute and diagnostic audits are separate artifacts. None supplies
human UER, strength inflation, recall or a hypothesis result. The qualitative graph is explicitly marked as
awaiting independent review.

## Deviations and current limits

The six current queries are source-backed development candidates spanning six
months. Their episode dates are unconfirmed and they do not substitute for the
planned 30-query split or reviewer gold. This run cannot be presented as the
frozen six-query development experiment. Earlier direct-graph baseline runs
were excluded after the prose protocol mismatch was found. The included
baseline phase and corrected controller phase retain separate source hashes;
this development assembly is not a single-version frozen sweep.

OEA supplies some official coverage as a recorded source-list deviation. The
Indian basket is monthly and partial; it cannot confirm every daily episode.
Brent, identified benchmark 10-year yields and one FPI observation are now
present as sparse news vintages. Later-captured daily/monthly snapshots are now
available separately; complete original-vintage histories and episode confirmation
remain missing. Business Standard remains inaccessible under its robots policy,
and the RBI Bulletin alternative returned a bot challenge rather than source
content. These checks add no publisher/official coverage. The local MLX run replaces no claimed Kaggle execution: the notebook is
an unexecuted handoff template and no Kaggle GPU hours are claimed. The HTTP
adapters are implemented but not exercised as a model-comparison result. No paid
API request was made.

Human support judgments, baseline extraction corrections, independent reference
graphs, double annotation, the public-data strength/direction pilot and the
two-model five-task selection pilot are incomplete. D-05/D-06/D-07 need actual
TA decisions. This draft leaves those decisions open.

## Revised risk register

| Risk | Current evidence | Next action and acceptance criterion |
|---|---|---|
| Review records pending | User reports both reviews complete; saved decisions and attestations await reconciliation | Import actual records, reconcile versions and corrections, and verify required blinded support/reference labels and double annotation |
| Incomplete temporal/financial grounding | Original vintages remain sparse; separate retrospective histories have October availability and some definition/frequency differences | Validate exact episode measurements and original availability, then confirm or drop/redate each anchor |
| Selection bias | All-month machine-curated pilot; concentrated sources | Broaden reviewed pairs and source/extraction checks before accepting model/retriever settings |
| Verifier abstention hides lost coverage | Some edges can remain inferred or unchecked at budget | Review reference graphs and report recall guard alongside UER; retain null denominators |
| Quotation errors in baselines | Exact-span failures in actual generated outputs | Preserve them in review and report structural counts separately from semantic judgments |
| Reproduction/environment differences | Fresh core check passes; optional runtime and payload are separate | Full local v1 sweep matches; repeat on team machines/Kaggle before acceptance |
| Synthetic benchmarks overstate capability | Repeated scripted scenarios; heuristic safety screen | Report them as diagnostics; add reviewed real states and adjudicate full safety responses |

## Remaining four-week plan (proposed, not assigned)

| Week | Work | Exit condition |
|---|---|---|
| 2–6 November | Resolve data/episode gaps, complete model and retrieval pilots, finish annotation and TA decisions | Accepted inputs/settings, complete reviewed reference graphs, recorded agreement |
| 9–13 November | Freeze the intended test inputs and run all conditions with immutable settings | Complete logged sweep; no tuning on test outcomes; structural audit passes |
| 16–20 November | Blind score, adjudicate, evaluate challenge/safety, calculate paired intervals and recall guard | Complete independent judgments and traceable evaluation artifacts |
| 23–27 November | Replicate, check stability and failure cases, finish figures/report and archive | Reviewed results, reproduction evidence and team-approved final deliverables |

The team must accept or revise these dates and ownership. No test-set annotation
or result is fabricated to fill the schedule.
