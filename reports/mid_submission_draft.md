# Mid-submission working draft — updated 28 October 2026

> **This is the working log, not the submission.** The document submitted on
> 30 October is [`reports/mid_submission.md`](mid_submission.md), which is
> organised against the eight elements the brief requires. This file is kept
> because it records what was found when, which the submission summarises.

**Status: implementation checkpoint; research results and team acceptance pending.**
**As of 28 October the v7 corpus is installed on both machines and Track B's
anchors, query set, gold graphs and public-data diagnostics are in. What is still
missing is not data: it is one human adjudication step and one model run.** See
"Track B" below for both, and `docs/decisions.md` D-17 to D-21.
This is a working draft for the 30 October submission, not a finished report or
an accepted experimental freeze. The study asks whether unsupported established
edges increase with distance from an anchor, and whether targeted verification
and retrieval reduce that rate without losing supported reference edges.

The subsequent whole-project audit found five integration/reproduction gaps,
including selected-retriever wiring and anchor confirmation. It repaired two
Track A code defects and raised the local passing suite to 641 tests. Track A's
scoped standalone handoff does not complete its shared integration, annotation,
result-figure or full reproduction obligations. See
`reports/whole_project_audit_20261027.md` for the full plan comparison.

Track A's scoped development handoff is complete under the 27 October closeout
in `reports/track_a_mid_submission_scope_20261027.md`. For the mid-submission it
delivers the acquired source mix, narrative-only PDF index and sparse six-series
store with explicit deviations. Separate completed review records now carry
Varun's independence/blinding attestations and pass both exporters. This does
not grant publisher permission or anchor acceptance.

Track A's current delivery is recorded in `reports/track_a_progress.md`: an
active v7 narrative development corpus of 1,156 documents and 16,472 passages,
a rebuilt dense index, and complete source judgments for the 2,035-item new
retrieval pool (195 relevant, 1,840 irrelevant). The 20-question development
comparison selects dense retrieval: Recall@10 0.4259, or 0.5296 with reranking.
The original labels come from automated development review with prior results
exposure. They remain unchanged after Varun's user-attested review; the accepted
records validate declared review conditions, not independently observed conduct.
The original blank workspace remains preserved separately.

The current checkout passes 641 tests. The earlier clean environment with
optional PDF/extraction dependencies passed 637; that evidence is preserved.
The earlier committed-source reparse reproduces all corpus
and archive hashes. All six series retain 161 original observations; the
317-observation October snapshot is available only for retrospective checks.
Original-vintage gaps, inaccessible publishers and source permissions are
explicit limitations. Existing 42-graph outputs and the 24-graph reproduction
retain archived v1; they are not v7 experiments. Final support/UER figures
still require the separate experiment-review work and supporting records.

The subsequent official-source audit checks all 61 retained PDF file versions
and seven SEBI annexures. Five dated total-FPI candidates remain separate
because they include mutual-fund investment beyond the existing series. Dated
primary announcements now support April's domestic ATF announcement and the
August RBI meeting; this supplies Track B evidence, not independent anchor
acceptance. See `reports/track_a_followup_20261026.json`.

## Human review report — 27 October

The user reports completing Track A review only, identifies the reviewer as
Varun and the date as 27 October 2026, and explicitly attests independent review
and blinding to results. These declarations are recorded in the intended files.
Both actual acceptance exports pass final-v7 bindings, 73 corpus rows, 20
questions and 2,035 candidates, with 195 exact positive spans. All decisions
remain identical to the original automated development assessment. That origin
and the originally supplied versions remain preserved. The software validates
records and declarations, not reviewer identity, procedure or exposure timing.

The user's completion report is retained separately from this artifact finding.
The reduced source/PDF scope and sparse original-date coverage are now adopted
for the scoped mid-submission handoff. Publisher permissions, fuller histories
where needed for anchors, and experiment support review remain separate
requirements. No main hypothesis result follows from these files. See
`reports/track_a_reviewer_identity_20261027.json`, the historical initial check
`reports/track_a_submitted_review_validation_20261027.json`, and
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
research scores. The guide and local review page are ready. The user-reported
completed review covers Track A; experiment support review remains separate.

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

## Track B — ontology, verifier, anchors, queries, gold, diagnostics

Updated 28 October 2026, after the v7 corpus arrived. Decision rows D-17 to D-21
in `docs/decisions.md` carry the reasoning; this is the summary a reader needs.

### What Track B delivers

| task | state | evidence |
|---|---|---|
| **B6** deterministic verifier | 4 rules — in corpus, on-or-before as-of, both variables mentioned, span verbatim | `src/verify/rules.py`, integrated at `f788c7a` |
| **B2** anchor confirmation | **3 of 8 anchors confirmed as declared, 2 of those against official data** | `data/eval/episodes.md` (generated; `--check` fails if stale) |
| **B3** query set | **8 queries over 4 anchors**, 4 dev and 4 test, split by anchor | `data/eval/queries_dev.jsonl`, `queries_test.jsonl` |
| **B4** gold evidence graphs | 4 graphs, **20 edges**, span-exact, **machine-drafted and not adjudicated** | `data/eval/gold/dev/`, `ADJUDICATION.md` |
| **B9** challenge set | **not built — unreachable at 125 items** | `reports/b9_feasibility_20261028.md` |
| **B10** strength and detection checks | cue baseline run; the LLM arm is not | `reports/pilot_strength.md` |

### The anchors that survived

Of eight candidate episodes checked against the series store under as-of
discipline — an observation confirms a move only if its `available_on` is on or
before the episode's as-of date — three confirm as declared: the May rupee low
(FBIL, same day, 96.8441), the June CPI acceleration (MOSPI, 4.38) and the March
FPI outflow (−13,600, **news-reported, not official**). The March oil shock is
**redated**: `brent_usd_bbl.csv` holds no March observation, so the proposal's own
worked example — "Brent crossed \$100 on 12 March" — has no usable as-of date and
the anchor moves to 1 April. The September bond sell-off is **dropped**: the yield
series ends 31 August and never reaches 7%. April ATF and both RBI meetings are
document-confirmed only, with no series behind them.

So **only USD/INR and headline CPI meet the "confirmed against official data"
standard** the proposal claims for all eight. Brent, the benchmark yield and FPI
are news-reported by Track A's own `data/series/README.md`, and
`EpisodeConfirmation.official_source` makes that a first-class flag so the
distinction cannot quietly disappear from a results table.

### The gold set reaches hop 2, and that constrains what RQ1 can claim

The 20 dev gold edges are 10 `direct`, 9 `conditional`, 1 `correlational`; **15 at
hop 1, 5 at hop 2, none at hop 3 or beyond.**

This matters because every headline number is sliced by hop distance 1 / 2 / ≥3,
and the two primary metrics are affected differently:

* **UER** is measured over *generated* edges and needs support judgements, not
  gold, so it can still be reported at hop ≥3 — if the conditions produce edges
  that deep. Whether they do is an open empirical question, not an assumption.
* **Reference-edge recall**, the H2d guard that stops verification from being
  rewarded for simply deleting edges, is measured *against* gold. With no gold
  edge past hop 2 it **has no denominator at hop ≥3**, so the guard is unavailable
  in exactly the slice where H1 predicts grounding is worst.

The cause is traceable: D-18 dropped the September bond sell-off, which was the
only anchor with a yield chain, and that chain was the deep-hop coverage. The
honest statement for the report is that **H1 can be examined at hops 1 and 2, and
H2d only there**; a claim about hop ≥3 would rest on a slice with no reference
set behind it.

The scoring that produces both hypothesis results is built and pinned to
thresholds declared **before any v7 run was scored** (D-22, commit `5663458`): a
hop bucket needs 10 established edges to carry a claim about that hop, a
monotone trend needs all three buckets, and an inferential claim needs 10
queries — which on a four-query dev set fires by construction, so **no dev
figure will be presented as inferential whatever it turns out to be**.
`scripts/report_rq.py` runs today and currently writes nothing, naming the three
preconditions in dependency order: the dev sweep (#41), blind support
judgements (#42), and the signed reference receipt (#37). RQ2 will not describe
a UER drop as a repair while the recall guard is undetermined, because a
verifier deleting edges it cannot confirm produces the same headline number.

### The gold graphs are drafted, not reviewed

All four pass `scripts/check_gold_graphs.py` against the v7 corpus — spans
verbatim, citations exact, nothing published after the as-of date. They were
drafted mechanically by `scripts/draft_gold_graphs.py`, which slices each span
out of the real passage text and runs the rule layer before writing, and each
file carries `MACHINE-DRAFTED, NOT YET ADJUDICATED` in its `notes` field, asserted
by a test.

The rule layer is not a substitute for judgement and the report must not imply it
is. It confirms a span is verbatim and that the passage mentions both variables;
it cannot tell whether the passage **asserts** the relation, which way the
causation runs, or whether the strength label fits the language. Three candidates
passed every rule and were dropped by hand for exactly those reasons — two cited
passages that mention both variables while asserting nothing between them, and
one whose causation ran backwards (portfolio outflows pressuring the rupee, read
as the rupee driving outflows). A reviewer should expect to find more.

`eval.references.validate` enforces this independently of good intentions: it
refuses any reference set whose `review_receipt.json` lacks a reviewer, a date,
`independent_review` and `all_relations_and_strengths_reviewed`. The receipt is
prepared and hash-bound to the v7 corpus and to each graph file, with those four
fields blank. **That single human step, not the corpus, is what blocks the
challenge set, blind scoring and both hypothesis results.** Cohen's κ needs two
people who have not compared notes, and no amount of tooling substitutes.

### What a word list achieves on strength, and why it is in the report

`reports/pilot_strength.md` scores a deterministic cue classifier built from the
proposal's own Table 2 cue lists on two public datasets nobody here wrote: Yu et
al. (2019) for 3-class strength and FinCausal 2020 task 1 for binary detection,
200 items each, diagnostics only and never training.

| check | result |
|---|---|
| strength, 3-class | macro-F1 **0.414**, accuracy **0.350**, 81/200 abstentions |
| detection, binary | F1 **0.497**, accuracy **0.525** |

Per class the baseline is lopsided: `conditional` recall 0.920 at precision
0.377, `correlational` precision 0.886 at recall 0.333, `direct` F1 0.222. It
over-fires on hedging and under-detects plain causal language.

This exists so the LLM verifier has a floor to clear. **A verifier that cannot
beat a word list on strength is not doing the work the design credits it with,
and that is a reportable finding rather than an embarrassment.** The comparison
has not been run: the same 200 items against the B7 verifier need the pinned
local model, which is not on the Track B machine, so the project cannot yet
claim the verifier earns its place on strength. For scale, Yu et al. report
macro-F1 about 0.86 with a fine-tuned BERT on their own four-class task; the
word list below and that ceiling bracket where the verifier should land.

One mapping worth carrying forward: Yu et al.'s labels are `0 = none, 1 = Direct,
2 = Conditional, 3 = Correlational`. **1 is direct and 3 is correlational, the
reverse of the intuitive order.** The builder asserts the published class counts
on load so a re-release cannot silently invert every strength number.

### What a word list catches, and what it cannot

The challenge set (#20) is **104 items**: 19 clean controls plus 85 corruptions
of the five families, derived mechanically from the dev gold edges. It is 104
rather than the planned 125 because D-18 and D-19 capped the gold set at 24
edges, which made the original target unreachable by construction — the
arithmetic is in `reports/b9_feasibility_20261028.md`.

Run against the **deterministic rule layer with no model at all**:

| corruption family | items | flagged | can the rules see it? |
|---|---:|---:|---|
| `unsupported_intermediate` | 19 | 19 | yes |
| `wrong_date` | 19 | 19 | yes |
| `wrong_target` | 19 | 19 | yes |
| `reversed_relation` | 19 | **0** | **no, by construction** |
| `inflated_strength` | 9 | **0** | **no, by construction** |
| clean controls | 19 | **0** | these are the false alarms |

**57 of 57 citation corruptions caught, 0 false alarms, 0 of 28 semantic ones.**

This is the project's clearest evidence on both sides of its own design
question. Reversing an edge leaves the same two variables in the same passage
with the same verbatim span, and no rule reads the `strength` field, so a third
of the corruptions — including the two a careless graph is most likely to
contain — **cannot be caught by matching text at all.** That is the argument for
the semantic verifier, and it is an argument from data rather than from
expectation. It cuts the other way too: the three families the rules do catch are
caught deterministically, cheaply, with no model, so a verifier spending calls
re-checking citations is spending them where a regex already wins.

The per-family denominators are uneven on purpose (D-21) — the gold set supplies
19 seeds but only 9 hedged links — so every rate is quoted with its own and no
macro average over families is meaningful. One asymmetry to carry into the
report: corruption detection is sound even on un-adjudicated gold, because each
corruption was applied mechanically and is known by construction, but **the
0.000 false-alarm figure is not** — a control is clean only if its gold edge was
right. Recorded as D-23.

### Source access: two publishers are closed to us

`reports/source_access_recheck_20261027.md`. Business Standard (403) and the RBI
(418) still refuse `robots.txt` to the project's client while serving it to
browsers. Closing that gap means presenting a browser user-agent to defeat the
distinction, which is bot-check circumvention, and was declined. Mint is
reachable and permitted but effectively unusable: a bounded probe found 887
archive URLs and admitted **0 of 6** candidates — landing pages carry no
publication date and four had no extractable body, which is what a paywalled
article looks like to an extractor. PIB's `robots.txt` returns 200 but serves an
HTML error page rather than a policy, and remains the one untested avenue.

The consequence for the corpus is concentration: **870 of 1,095 news documents
are Economic Times**, with Business Standard, RBI and PIB at zero and Mint at 12.
That belongs in the limitations section beside Recall@10 0.4259. It also
compounds the anchor gap rather than being separate from it — both RBI anchors
were already `no_series` under D-18, so with no RBI documents either they have
neither a confirming series nor a primary document.

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
| Scoped data delivery | Track A adopts the acquired sources, narrative PDFs and sparse six-series store for the mid-submission | Report these deviations; retain redistribution limits and require dated evidence before accepting an unsupported anchor |
| Review procedure and experiment acceptance | Track A records validate on Varun's 27 October independent/blinded review attestations; original labels and prior results availability remain disclosed | Do not equate receipt validation with independently observed conduct; experiment support/reference review and double annotation remain separate |
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
