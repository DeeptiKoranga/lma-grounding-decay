# Mid-submission working draft — 23 October 2026

**Status: implementation checkpoint; research results and team acceptance pending.**
This is a working draft for the 30 October submission, not a finished report or
an accepted experimental freeze. The study asks whether unsupported established
edges increase with distance from an anchor, and whether targeted verification
and retrieval reduce that rate without losing supported reference edges.

## What is built

The local corpus contains 1,173 documents (1,112 news, 61 official) and 27,286
passages spanning March–September 2026. Frozen passage offsets, corpus identity
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

The six typed tools enforce the query cutoff, trusted passage identity and a
12-call budget. A fresh-context semantic verifier follows deterministic source,
date, variable and quotation checks. Graph updates recompute shortest BFS hops
and weakest-link paths. Actual model tokens, prompts, completions, tool outcomes,
latencies and stop states are logged. Baseline source errors remain visible for
review rather than being silently repaired before comparison.

Human correction, blinded support scoring, reference recall, agreement,
challenge generation, query-paired bootstrap and reviewed-only UER figures are
implemented. Missing labels and zero denominators cannot become successful
research scores. The guide and local review page are ready; the independent
reviewer has not been selected.

## Evidence available now

- Current checkout: 547 tests pass; Ruff and Black pass. The core-only fresh
  clone passes 537 tests with two optional-library skips on Python 3.12.13.
- Retrieval smoke comparison on 20 unreviewed March-only convenience pairs:
  Recall@10 is 0.900 for plain BM25, 0.925 for hybrid and 0.975 for BM25 plus
  reranking. These incomplete labels cannot settle D-02/D-03.
- Twenty executed synthetic tool faults preserve the graph and cutoff, count
  attempted calls and produce the expected typed boundary outcome. Model-led
  fault recovery has not been established by this test.
- Three of six series have accepted observations: seven original provisional
  CPI releases, 141 FBIL exchange rates, and two Indian basket monthly averages
  available from 17 June. Five FPI candidates are staged outside the canonical
  store because historical vintages are unverified.

The seven-condition run, synthetic model diagnostics and compute totals have
separate machine-readable audits. None supplies human UER, strength inflation,
recall or a hypothesis result. The qualitative graph is explicitly marked as
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
Brent, identified benchmark 10-year yields and historically accepted FPI remain
missing. The local MLX run replaces no claimed Kaggle execution: the notebook is
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
| Annotation bottleneck | Reviewer not assigned; all packet attestations blank | Assign reviewers; correct prose, then complete blinded support labels and an independently double-annotated subset |
| Incomplete temporal/financial grounding | Three missing series; partial basket; unconfirmed episodes | Acquire the exact required definitions/vintages, then confirm or drop/redate each anchor |
| Selection bias | March-only retrieval pilot; concentrated sources | Broaden reviewed pairs and source/extraction checks before accepting model/retriever settings |
| Verifier abstention hides lost coverage | Some edges can remain inferred or unchecked at budget | Review reference graphs and report recall guard alongside UER; retain null denominators |
| Quotation errors in baselines | Exact-span failures in actual generated outputs | Preserve them in review and report structural counts separately from semantic judgments |
| Reproduction/environment differences | Fresh core check passes; optional runtime and payload are separate | Execute a recorded fresh model probe, then repeat on team machines/Kaggle before acceptance |
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
