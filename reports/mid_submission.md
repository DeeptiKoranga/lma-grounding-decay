# Mid-submission — Does Grounding Decay with Distance?

**Language Models & Agents (LMA) Group Project 2026**

Mid-submission: **30 October 2026**. Final submission: **15 November 2026**.

Varun Patil (2025204013) · Harshal Bhansali (2026909007) · Deepti Koranga (2025204033)

Repository: `https://github.com/DeeptiKoranga/lma-grounding-decay` (branch `main`)

> **What this document claims and does not.** Everything below is implemented,
> runnable and reproducible from the repository. The **primary metric (UER) has
> no value yet**: it requires blind human support judgements that are scheduled,
> not done. Where a number exists we give it; where it does not we say so and
> give the date. No result in this document has been estimated, extrapolated or
> filled in to complete a table.

---

## 1. Progress

The study asks whether evidential support weakens and causal language hardens as
an LLM builds longer causal explanations (RQ1), and whether an agent that
verifies each link and searches for evidence on weak links repairs it (RQ2).

Work is split by directory so three people can commit in parallel:

| Track | Owner | Scope | State |
|---|---|---|---|
| **A** | Varun | corpus acquisition, chunking, retrieval, macro series | delivered with documented deviations |
| **B** | Deepti | ontology, verifier, anchors, query set, gold graphs, diagnostics | delivered; one human step outstanding |
| **C** | Harshal | model interface, agent loop, tools, metrics | delivered; full sweep outstanding |

**Built and tested:** a frozen 1,156-document corpus with exact character
offsets; BM25, alias-expanded BM25, BGE-M3 and reciprocal-rank-fusion retrieval
with a cross-encoder reranker; a closed 44-variable ontology; a four-rule
deterministic verifier plus an LLM verifier downstream of it; six read-only,
schema-validated tools under a 12-call budget; all seven experimental conditions
sharing one code path; and the scoring harness for both research questions.

**Scale:** 73 source modules, 53 test files, **799 tests passing**, Ruff and
Black clean. 23 decision rows in `docs/decisions.md`, each recording what was
decided, why, and what it costs. 38 of 51 issues closed.

**Not done:** the hypothesis results. Section 5 says exactly which numbers exist
and which do not, and Section 8 dates the rest.

---

## 2. Datasets being used

### 2.1 Frozen news and official corpus

`data/processed/`, manifest and hashes in `data/processed/MANIFEST.md`.
Publication window **1 March – 30 September 2026**, inclusive. Retained **1,156
documents** (1,095 news, 61 official) and **16,472 passages**. Zero duplicates
survived deduplication (exact full-text hashing for all sources; news
additionally MinHash on title + first-paragraph word trigrams, 128 permutations,
32 bands × 4 rows, exact Jaccard ≥ 0.85).

| Source | Documents | Planned? |
|---|---:|---|
| Economic Times | 870 | yes |
| BusinessLine | 213 | yes |
| MOSPI (CPI releases) | 37 | yes |
| PPAC | 14 | yes |
| Mint | 12 | yes, under-delivered |
| eaindustry (WPI) | 10 | yes |
| **Business Standard** | **0** | **not acquired** |
| **RBI** | **0** | **not acquired** |
| **PIB** | **0** | **not acquired** |

Target counts were **met** (≥900 news, ≥60 official). **Source mix was not**:
870 of 1,095 news documents — 79% — are Economic Times. Section 6.4 explains
why, and why we stopped rather than working around it.

Passages carry exact character offsets into the parent document text, which is
what makes verbatim span checking possible at all. The 61 official PDFs
contribute 949 narrative paragraphs; numeric tables, charts and image-only
content are outside the declared extraction scope and recorded as such.

### 2.2 Macro series — confirmation only, never evidence

`data/series/`. Six series, **161 original-vintage observations**. Each carries
an `available_on` date, so an observation confirms a move only if it was
published on or before the query's as-of date.

| Series | Observations | Source | Official? |
|---|---:|---|---|
| `inr_usd` | 141 | FBIL | yes |
| `cpi_headline_yoy` | 7 | MOSPI | yes |
| `gsec_10y_pct` | 6 | news-reported | no |
| `brent_usd_bbl` | 4 | news-reported | no |
| `indian_basket_usd_bbl` | 2 | PPAC | yes |
| `fpi_flows_usd_mn` | 1 | news-reported | no |

Per the proposal, series **confirm that a move happened and are never evidence
for a causal edge**. The sparsity has consequences, in Section 6.1.

### 2.3 Evaluation sets

| Set | Size | File |
|---|---:|---|
| Anchored queries | **8** over 4 anchors (4 dev / 4 test) | `data/eval/queries_{dev,test}.jsonl` |
| Reviewer evidence graphs | 4 graphs, **20 edges** | `data/eval/gold/dev/` |
| Challenge set | **104 items** (19 control + 85 corrupted) | `data/eval/challenge.jsonl` |
| Frozen agent states | 40 | `data/eval/synthetic/agent_states.jsonl` |
| Safety prompts | 25 | `data/eval/synthetic/safety_prompts.jsonl` |
| Tool-fault scenarios | 20 | `data/eval/synthetic/tool_faults.jsonl` |

The query set is 8 rather than the proposed 30, and the gold graphs are drafted
rather than adjudicated. Both are explained in Section 6.

### 2.4 Public datasets — diagnostics only, never training

**Yu et al. (2019)** causal-language data and **FinCausal 2020 task 1**, 200
sampled items each, seed 20261027. Source URLs, SHA-256 and the selected row ids
are in `data/eval/strength_benchmark_manifest.json`; third-party text is not
redistributed. **Neither dataset is used for training or tuning.**

One mapping worth stating because getting it backwards would invert every
strength number: Yu et al.'s labels are `0 = none, 1 = Direct, 2 = Conditional,
3 = Correlational`. **1 is direct and 3 is correlational**, the reverse of the
intuitive order. The builder asserts the published class counts on load so a
re-release cannot silently change it.

---

## 3. Baseline experiments

All seven conditions are implemented and share one model, corpus, date filter,
retriever, query set and prompt-tuning budget.

| Condition | Description | Role |
|---|---|---|
| B0 | Query only, no retrieval | reference |
| **B1** | Standard RAG, top-*k* passages, one call, prose with citations | **main baseline** |
| B1-R | B1 plus a top-50 cross-encoder reranker | retrieval ablation |
| B2 | RAG, one call, model emits its own provenance and strength labels | prompting control |
| A-NoVerify | Full system with the verifier replaced by self-labels | verifier ablation |
| A-NoLoop | Full system retrieving once, no agent loop | agentic ablation |
| **M** | Graph, labels, verifier, agent loop, weakest-link paths | **proposed method** |

### 3.1 What has actually been run

**A complete 42-graph sweep: 7 conditions × 6 development candidates**, logged
end to end, structurally audited, 0 failures
(`reports/integration_validation.json`).

**Two honest qualifications, both of which limit what it supports:**

1. It ran on the **archived v1 corpus**, not the current v7 corpus.
2. It ran on six *development candidates*, not the anchored query set the
   hypotheses are defined over.

On the current v7 corpus, a selected-configuration smoke completed **14 graphs**
(2 queries × 7 conditions), reused all 14 on an unchanged resume, and passed the
complete-matrix audit. **There is therefore no full dev sweep on the corpus we
intend to report.** It is scheduled, not skipped — Section 8.

### 3.2 Structural outcome per condition

From the 42-graph sweep. These are structural counts, **not support scores**.

| Condition | Graphs | Edges | Established | Unverified inferred |
|---|---:|---:|---:|---:|
| B0 | 6 | 20 | 12 | 20 |
| B1 | 6 | 34 | 34 | 10 |
| B1-R | 6 | 31 | 31 | 12 |
| B2 | 6 | 36 | 36 | 18 |
| A-NoVerify | 6 | 36 | 36 | 16 |
| A-NoLoop | 6 | 35 | **0** | 5 |
| M | 6 | 35 | **8** | 18 |

Agent stop reasons across the 42 runs: `important_edges_resolved` 28,
`budget_exhausted` 10, `two_searches_added_nothing` 4.

---

## 4. Ablations

A-NoVerify and A-NoLoop ran in the same 42-graph sweep, under the same corpus,
retriever and budget as M, so the comparison is like for like.

**The ablations have already produced the project's most important observation,
and it is a negative one.**

Only the verifier may mark an edge `source_asserted`. Removing it (A-NoVerify)
leaves the generator's self-labels, and **36 of 36 edges are established**.
Keeping the verifier but removing the agent loop (A-NoLoop) leaves it with only
one retrieval pass, and **0 of 35 edges are established**. The full system M
establishes **8 of 35**.

Read together: the verifier is **extremely conservative**, and without the
edge-targeted search loop to bring it evidence, it establishes nothing at all.
This is exactly the failure mode the proposal's own risk table anticipated —
*"verifier labels nearly everything as inferred"* — and it is what hypothesis
H2d, the recall guard, exists to catch. A system that establishes few edges
posts an excellent UER while answering the question badly.

**What this does not yet tell us.** Whether M's 8 established edges are the
*right* 8 is a support judgement, and no human has made it. The ablation
therefore shows the mechanism is live and consequential; it does not yet show
whether verification helps or merely deletes. That is precisely the RQ2 contrast,
and the harness that decides it is built (Section 5.6).

---

## 5. Results from the experiments run

### 5.1 Retrieval pilot — resolved (D-02, D-03)

20 query–evidence pairs × 4 configurations, 2,035 pooled relevance judgements
(195 relevant). Decision rule pre-declared: take the simplest configuration
within 0.03 Recall@10 of the best.

| Configuration | Recall@10 |
|---|---:|
| BM25 | 0.3518 |
| BM25 + alias expansion | 0.3551 |
| Hybrid (RRF) | 0.4161 |
| **BGE-M3 (selected)** | **0.4259** |
| BGE-M3 + top-50 cross-encoder | **0.5296** |

**Caveat we will not bury:** the 2,035 relevance judgements are single automated
judgements made with prior exposure to results, not independent human scores.
This is sound as a *development* selection and cannot be presented as reviewed
evidence.

### 5.2 Causal strength and detection on public data

Cue-based baseline built from the proposal's own Table 2 cue lists, scored on
data nobody on this project wrote (`reports/pilot_strength.md`).

| Check | Result |
|---|---|
| Strength, 3-class (Yu et al.) | macro-F1 **0.414**, accuracy **0.350**, 81/200 abstentions |
| Detection, binary (FinCausal) | F1 **0.497**, accuracy **0.525** |

Per class: `conditional` recall 0.920 at precision 0.377; `correlational`
precision 0.886 at recall 0.333; `direct` F1 0.222. The word list over-fires on
hedging and under-detects plain causal language.

This exists so the model arm has a floor to clear. **A verifier that cannot beat
a word list on strength is not doing the work the design credits it with** — a
reportable finding, not an embarrassment. For scale, Yu et al. report macro-F1
≈ 0.86 with a fine-tuned BERT on their own task. The model arm is implemented and
has not been run; it needs the pinned weights.

### 5.3 Challenge set — corruption detection splits cleanly

104 items run against the deterministic rule layer **with no model at all**
(`reports/challenge_rules.md`).

| Corruption family | Items | Flagged | Rate |
|---|---:|---:|---:|
| `unsupported_intermediate` | 19 | 19 | 1.000 |
| `wrong_date` | 19 | 19 | 1.000 |
| `wrong_target` | 19 | 19 | 1.000 |
| `reversed_relation` | 19 | **0** | **0.000** |
| `inflated_strength` | 9 | **0** | **0.000** |
| Clean controls | 19 | 0 | — |

**57 of 57 citation corruptions caught, zero false alarms, zero of 28 semantic
ones.** The two misses are by construction: reversing an edge leaves the same two
variables in the same passage with the same verbatim span, so every rule still
passes, and no rule reads the strength field. The test suite asserts the misses,
so a rule cannot quietly acquire a capability it does not document.

This is the project's clearest evidence **on both sides of its own design
question**. A third of the corruptions — including the two a careless graph is
most likely to contain — cannot be caught by matching text, which argues for the
semantic verifier from data rather than from expectation. Equally, the three
families the rules do catch are caught deterministically and for free, so a
verifier spending calls re-checking citations spends them where a regex already
wins.

Per-family denominators are uneven by design (the gold set supplies 19 seeds but
only 9 hedged links), so every rate is quoted with its own and no macro average
over families is meaningful.

### 5.4 Capability, safety and tool-calling diagnostics

40 synthetic frozen agent states and 25 adversarial safety prompts
(`reports/capability_diagnostics.json`).

| Metric | Result |
|---|---|
| Tool-selection accuracy (standalone model choice) | **0.125** |
| Argument validity (schema + unchanged cutoff) | **0.850** |
| Jointly correct and schema/cutoff valid | 5 / 40 |
| Investment-advice leakage, 25 prompts | **0** |
| Own-forecast leakage, 25 prompts | **0** |
| Synthetic tool-fault recovery | **20 / 20** |

**Read 0.125 carefully.** It measures the model's *standalone* next-action choice
on scripted states. The executed controller uses deterministic priority, so this
is **not** the accuracy of the agent as it actually runs — it is evidence that
the model would choose poorly if the controller delegated the decision to it,
which is an argument for the deterministic controller rather than against the
system. Argument validity of 0.85 says that when it does emit a call, the
arguments are usually well-formed and never silently move the date cutoff.

The 40 states are five close variants of eight scenarios, so they are a
diagnostic, not a benchmark.

### 5.5 Measured compute

| Run | Model calls | Prompt tokens | Completion tokens | Wall (model calls) | Tool calls |
|---|---:|---:|---:|---:|---:|
| 42-graph sweep | 87 | 260,325 | 37,304 | 1.32 h | 188 |
| Capability diagnostics | 65 | 160,470 | 4,234 | 0.49 h | 0 |

All local, on an Apple M5 via MLX, pinned Qwen3-8B at 4-bit, revision
`545dc425`. **No paid API request was made. No Kaggle GPU hours were used or are
claimed.** Times are measured model-call wall times, not GPU-active hours.

### 5.6 What has no number yet

**UER, strength inflation and reference-edge recall — the primary metric and
both secondary metrics — have no values.** They require blind human support
judgements on the generated edges, which are scheduled for **4 November** on
the dev set and 10 November on the test set (Section 8).

The scoring is built and runs today. `scripts/report_rq.py` currently writes
nothing and names the three preconditions in dependency order, which is
deliberate: a missing result stays visible rather than becoming an empty section.
Its thresholds were fixed **before any result existed** (D-22, commit `5663458`):
a hop bucket needs 10 established edges to carry a claim, a trend needs all three
buckets, and an inferential claim needs 10 queries — which on a four-query dev
set fires by construction, so no dev figure will be presented as inferential
whatever it turns out to be.

---

## 6. Challenges faced

### 6.1 Only 3 of 8 anchor episodes confirmed, and only 2 officially (D-18)

The proposal says the eight anchor episodes "will be confirmed against official
data". Checking that claim rather than asserting it: **3 of 8 confirm as
declared, and only USD/INR and headline CPI meet the official-data standard.**
The March oil shock had to be **redated** — `brent_usd_bbl.csv` holds no March
observation, so the proposal's own worked example ("Brent crossed \$100 on 12
March") has no usable as-of date. The September bond sell-off was **dropped**:
the yield series ends 31 August and never reaches 7%.

### 6.2 The query set is 8, not 30 (D-19)

Four usable anchors × one *why* and one *what-effects* question = 8 queries,
split 4 dev / 4 test **by anchor**, so dev and test share no episode, no as-of
date and no passages. Splitting by question type would have put both halves of
one event on both sides and leaked dev tuning into the test set.

**Consequence:** the test half is four queries. No test-set claim will have a
usable confidence interval, and those numbers must be reported descriptively.

### 6.3 The gold set reaches hop 2 and stops

The 20 gold edges are 15 at hop 1 and 5 at hop 2; **none at hop 3 or deeper.**
This matters asymmetrically. UER is measured over *generated* edges, so it can
still be reported at hop ≥3 if the conditions produce edges that deep.
Reference-edge recall — the H2d guard against verification being rewarded for
deleting edges — is measured *against* gold, so it has **no denominator at hop
≥3**: unavailable in exactly the slice where H1 predicts grounding is worst.

The cause is traceable to 6.1: the dropped September anchor carried the only
yield chain deep enough to produce hop-3 edges.

### 6.4 Two publishers are closed to our client

Business Standard returns **HTTP 403** and the RBI **HTTP 418** on `robots.txt`
to the project's client, while serving both to browsers. Closing that gap means
presenting a browser user-agent to defeat the distinction, which is bot-check
circumvention. **We declined to do it.** Mint is reachable and permitted but
effectively unusable: a bounded probe found 887 archive URLs and admitted **0 of
6** candidates — landing pages carry no publication date and four had no
extractable body, which is what a paywalled article looks like to an extractor.
PIB's `robots.txt` returns 200 but serves an HTML error page rather than a policy.

This compounds 6.1 rather than being separate from it: both RBI anchors were
already `no_series`, so with no RBI documents either they have neither a
confirming series nor a primary document.

### 6.5 The verifier establishes almost nothing

Section 4. M establishes 8 of 35 edges; A-NoLoop, 0 of 35. Anticipated in the
proposal's risk table and now observed.

### 6.6 The challenge set could not be built at the specified size (D-21)

Issue #20 asked for 100 corruptions plus 25 controls. The generator gates on 25
eligible seeds and 20 hedged ones; the gold set supplies **19 and 9**. This is
arithmetic, not effort: `MAX_EDGES` is 6 and 6.2 left four dev queries, so the
dev gold set is capped at 24 edges and 25 eligible seeds is unreachable **by
construction**. The original figure was written against the 30-query design that
6.1 and 6.2 invalidated, and nobody re-costed it at the time.

### 6.7 Process: nothing merged for nine days

Four feature branches plus a parallel-history branch sat unmerged from 19 to 28
October. One consequence was real: B6's verifier was **copied** onto another
branch rather than forked, so the same module existed twice with one copy
holding the newer rule, and decision number **D-13 was issued twice** by two
branches that could not see each other.

### 6.8 Tooling and machine asymmetry

The pinned model weights, the dense index and the run outputs live on one
machine only. Track B development therefore proceeds without the ability to run
any condition end to end, which is why Section 5.6's results are blocked on a
machine rather than on code.

---

## 7. Mitigation plans

| # | Challenge | Done already | Planned |
|---|---|---|---|
| 6.1 | Anchors unconfirmed | `scripts/confirm_episodes.py` checks all eight under as-of discipline and **generates** `episodes.md`; `--check` fails if it goes stale. `official_source` is a first-class flag so a report cannot claim eight official confirmations. | Extend the series store (1 Nov). More series can only improve the count, never silently change it. Two more anchors would also restore the challenge set's original gate. |
| 6.2 | 8 queries, not 30 | Split by anchor, so no leakage. Both files validate against the runner's `Query` model. | Annotate the four test queries after the dev four are adjudicated, so the guide is exercised once first. Report test numbers descriptively. |
| 6.3 | No hop ≥3 gold | The RQ1 reporter **refuses** to print a trend from fewer than three usable buckets and names the empty slice as the finding (D-22). | Reviving the September anchor (6.1) restores the yield chain. Otherwise scope the H1 claim to hops 1–2 explicitly and say why. |
| 6.4 | Publishers closed | Re-checked 27 Oct; declined the circumvention; probe artefacts removed. Concentration quantified at 870/1,095. | PIB seed discovery is the one untested legitimate avenue. Otherwise this is a stated limitation, reported beside Recall@10. |
| 6.5 | Verifier too conservative | H2d recall guard implemented with a pre-declared floor of −0.10; RQ2 **will not report a UER drop as a repair** while the guard is undetermined. | Tune the verifier on **dev only** once support judgements exist — one round, on 6 Nov, recorded as a decision row. If recall cannot be held, report that verification trades recall for precision — a finding, not a failure. |
| 6.6 | Challenge set size | Gates rescoped to 12/5 with floors retained; built 104 items; `counts_by_kind` published so no rate is quoted without its denominator. | Rebuild at the original size if 6.1 adds anchors. |
| 6.7 | Branches unmerged | All branches merged by **real ancestry**, not a third copy. The duplicated D-13 is renumbered to D-24 on the branch that still carries it (PR #52, open for review). Every branch now merges cleanly into `main` in any order, verified pairwise. **`main` now carries all the code.** | Merge to `main` on completion of each issue rather than at phase end. |
| 6.8 | Machine asymmetry | Every blocked step fails loudly and names its missing precondition rather than producing a placeholder. | Run the sweep on the machine that holds the weights; Kaggle (2×T4) remains the documented fallback and is unused so far. |
| — | Un-adjudicated gold | Graphs are span-exact and each carries `MACHINE-DRAFTED, NOT YET ADJUDICATED` in `notes`, asserted by a test. `eval.references.validate` **refuses** the set until a receipt names a reviewer. Blind worksheets generated. | Two annotators, independently, 30 Oct. Cohen's κ via `scripts/score_adjudication.py`. |

---

## 8. Timeline to final submission

**Final submission: Sunday 15 November 2026. All work winds up Thursday 12
November**, leaving 13–14 November as deliberate buffer rather than schedule.

The window is 12 calendar days — 9 weekdays plus the weekends of 1, 7–8
November. Owners: **V** Varun (Track A; holds the pinned model weights and the
dense index), **D** Deepti (Track B), **H** Harshal (Track C).

### Before the window

**30 October — blind double annotation of the 20 dev gold edges (D + V).**
Already prepared; worksheets are generated and the scorer is built. **This is
the only step with no slack**, because every downstream number is measured
against the gold standard it produces.

### Week 1 — get a dev result, then decide what to change

| Date | Owner | Work | Exit condition |
|---|---|---|---|
| **Sun 1 Nov** | V · D | Extend the series store and re-run anchor confirmation · draft the four **test** gold graphs | `episodes.md` regenerated; test graphs span-exact |
| **Mon 2 Nov** | V · D+H | **Dev sweep on v7**: 7 conditions × 4 dev queries = 28 graphs · adjudicate the test gold graphs | Complete logged sweep, structural audit passes; test receipt signed |
| **Tue 3 Nov** | H | Prepare the blind support packet from the dev sweep | Packet hash-bound, condition hidden, edges shuffled |
| **Wed 4 Nov** | **all three** | **Blind support judgements on the dev edges** (~150–200 edges) | Every edge judged; no blanks |
| **Thu 5 Nov** | H | Score: first **UER, strength inflation, reference-edge recall**, RQ1 and RQ2 on dev | `rq1_hop_decay.md` and `rq2_verification.md` written |
| **Fri 6 Nov** | all three | **Decision day.** Read the dev result. Tune the verifier on **dev only**; record every change as a decision row | Settings agreed and written down, or explicitly unchanged |

### Week 2 — freeze, run test, report

| Date | Owner | Work | Exit condition |
|---|---|---|---|
| **Sat 7 – Sun 8 Nov** | V · H | Machine time, low human cost: challenge-set **model arm** (the 28 semantic corruptions the rules cannot see) · strength **model arm** (200 items) · repeated-sampling stability check on one query · re-run dev if 6 Nov changed anything | Model arms reported; dev numbers final |
| **Mon 9 Nov** | all three | **FREEZE.** Record settings and hashes; **no tuning after this point.** Then the test sweep: 7 × 4 = 28 graphs | Frozen settings recorded; test sweep logged |
| **Tue 10 Nov** | all three | Blind support judgements on the **test** edges | Every edge judged |
| **Wed 11 Nov** | H · D | Final scoring: RQ1, RQ2, paired bootstrap, recall guard · figures | Results with intervals and denominators |
| **Thu 12 Nov** | all three | **Wind up.** Failure analysis on the five worst cases · reproduction from a clean clone · final report · tag `v1.0` | Report complete, repository archived |
| **Fri 13 – Sat 14 Nov** | — | **Buffer. Deliberately empty.** | — |

### The dependency that governs everything

```
gold adjudicated (30 Oct)
    -> dev sweep (2 Nov)
        -> blind support judgements (4 Nov)
            -> dev UER / RQ1 / RQ2 (5 Nov)
                -> tuning decisions (6 Nov)
                    -> FREEZE (9 Nov)
                        -> test sweep -> test judgements -> final results
```

Each arrow is a hard dependency. Slipping 30 October by a day slips 15 November
by a day, which the buffer absorbs once and not twice.

### Contingency, pre-declared

The v1 sweep (Section 4) shows M establishing 8 of 35 edges and A-NoLoop 0 of
35. **We should expect 5 November to show a failing or undetermined recall
guard.** Deciding now what to do about it stops the decision being made under
time pressure with the result already visible:

- **If H2d fails on dev**, the verifier is loosened on dev only, once, with the
  change recorded as a decision row, and the dev set is re-run on 7–8 November.
  One tuning round, not an open-ended search.
- **If it still fails**, we report that verification trades reference recall for
  precision and that H2b/H2c cannot be separated from deletion. That is a
  finding and it gets reported as one. We do not tune until the guard passes;
  tuning to a target is how a result becomes an artefact of its own tuning.
- **No tuning happens after 9 November**, whatever the test numbers look like.

### Scope deliberately dropped for the 15 November date

Named here so they read as choices rather than omissions, and each is a stated
limitation in the final report:

- **The interactive event-impact graph.** Static SVG and PNG renderings exist
  (`src/eval/figures.py`, `reports/development_example.svg`) and are what we
  will ship. Interactivity is not reachable in 12 days alongside the experiments
  and is not needed for either research question.
- **Blind scoring at scale** beyond the 4 dev and 4 test queries.
- **B1-R end-to-end benefit**, deferred since D-03 and still deferred; the
  retrieval-side comparison stands (Recall@10 0.5296 against 0.4259).

## 9. Repository

`main` carries all code, data contracts, reports and decision rows.

```bash
git clone https://github.com/DeeptiKoranga/lma-grounding-decay
make setup && make test          # 799 tests
make hooks                       # pre-commit + the main-branch guard
```

The corpus payload is **not** in git — it is third-party publisher text with no
redistribution licence. `data/processed/MANIFEST.md` carries the SHA-256 of each
file so a reviewer can verify the exact bytes used.

Key entry points:

| Command | Produces |
|---|---|
| `make gold` | redraft and span-check the dev gold graphs |
| `make adjudicate` / `make kappa` | blind worksheets, then Cohen's κ |
| `make challenge` | the 104-item challenge set and the rules-only arm |
| `make run-dev` | the dev sweep (needs the pinned model) |
| `make rq` | RQ1 and RQ2 findings from a reviewed run |
| `scripts/confirm_episodes.py --check` | fails if anchor confirmations go stale |

Reasoning for every substantive choice is in `docs/decisions.md` (D-01 … D-23),
each row recording the decision, why it was taken, and what it costs.
