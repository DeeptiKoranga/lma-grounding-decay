# Decisions log

Every `[needs pilot]` and `[needs TA decision]` item from the proposal, plus the
calls we made while scaffolding, as open rows. **Close a row in the same PR as
the evidence that closes it**: write the number, link the report, and date it.

Status is one of `open` · `resolved` · `deferred`.

Last reviewed: **19 Oct 2026** (Phase 0).

---

## Open from the proposal

### D-01 — Which model? `[needs pilot]`

| | |
|---|---|
| **Status** | `open` |
| **Question** | Qwen3-8B at 4-bit (the prior choice) or Qwen3.5-9B, for every condition? |
| **Where** | Proposal §8, "Model and retrieval" |
| **How it gets decided** | C2: 20 examples × 5 tasks — extraction, strength labelling, JSON validity, tool choice, rejecting unsupported edges. Run on the laptop under MLX at 4-bit. |
| **Owner / due** | C · by Sat 24 Oct |
| **Evidence** | `reports/pilot_model.md` |
| **Blocks** | Everything downstream of `src/llm/`. One model is used for *all seven* conditions, so this cannot be split per condition. |
| **Resolution** | *(unresolved)* |

### D-02 — Which first-stage retriever? `[needs pilot]`

| | |
|---|---|
| **Status** | `open` |
| **Question** | BM25, BM25 + alias expansion, bge-m3, or hybrid with reciprocal rank fusion? |
| **Where** | Proposal §7 Table 1 and §8 |
| **How it gets decided** | A8: 20 query–evidence pairs × 4 configs; Recall@5, Recall@10, MRR. **Decision rule is pre-declared: take the simplest config within 0.03 Recall@10 of the best.** |
| **Owner / due** | A · by Sat 24 Oct |
| **Evidence** | `reports/pilot_retriever.md` |
| **Blocks** | B1, B1-R and every agent condition share one first-stage retriever (proposal §11). |
| **Resolution** | *(unresolved)* |

### D-03 — Does the cross-encoder reranker earn its place? `[needs pilot]`

| | |
|---|---|
| **Status** | `open` |
| **Question** | Does bge-reranker-v2-m3 over the top 50 improve retrieval enough to keep B1-R as a condition, and does better ranking alone close the gap to M? |
| **Where** | Proposal §8, §11 |
| **How it gets decided** | A9: same metrics as D-02, on top of whichever retriever D-02 picks; then end-to-end as B1-R. |
| **Owner / due** | A · retrieval numbers by Sat 24 Oct; end-to-end deferred past 30 Oct |
| **Evidence** | `reports/pilot_retriever.md` |
| **Note** | B1-R at full scale is explicitly deferred past the mid-submission (PLAN_MIDSUB.md §3). |
| **Resolution** | *(unresolved)* |

### D-04 — Are the eight anchor episodes real? `[needs pilot]`

| | |
|---|---|
| **Status** | `open` |
| **Question** | Do the eight episodes found in news reports (March oil shock, April ATF increase, May rupee low, June and August RBI meetings, September bond sell-off, …) show up in the official series? |
| **Where** | Proposal §10, "Custom evaluation set" |
| **How it gets decided** | B2, against the macro series from A10. An episode that the series does not confirm is dropped or re-dated. |
| **Owner / due** | B · depends on A10 · by Sat 24 Oct |
| **Evidence** | `data/eval/episodes.md` |
| **Blocks** | All 30 anchored queries hang off these episodes. |
| **Resolution** | *(unresolved)* |

### D-05 — May we use the Claude Haiku 4.5 API fallback? `[needs TA decision]`

| | |
|---|---|
| **Status** | `open` |
| **Question** | If no local model passes the D-01 pilot, may we run the conditions against a paid API model instead? |
| **Where** | Proposal §8 and §13 |
| **Context** | The adapter is already behind the same `generate()` interface (C1), so switching costs no engineering time. Estimated USD 50, cap USD 100. |
| **Owner / due** | ask the TA in week 1; needed only if D-01 fails |
| **Resolution** | *(unresolved)* |

### D-06 — Paid-API budget cap `[needs TA decision]`

| | |
|---|---|
| **Status** | `open` |
| **Question** | Is USD 100 an acceptable cap, and does any API spend need prior approval? |
| **Where** | Proposal §13 Table 5 |
| **Note** | Tracked separately from D-05 because permission to use the API and the size of the budget are different answers. Current plan spends ₹0. |
| **Owner / due** | ask the TA in week 1 |
| **Resolution** | *(unresolved)* |

### D-07 — Is an LLM judge acceptable for B1-R and the ablations? `[needs TA decision]`

| | |
|---|---|
| **Status** | `open` |
| **Question** | Human labels cover B1, B2 and M. May an LLM judge score B1-R and the two ablations, gated on agreeing with humans at κ ≥ 0.6? |
| **Where** | Proposal §12, "Statistics" |
| **How it gets decided** | TA call on the principle; the κ ≥ 0.6 gate is measured on the doubly annotated subset from Phase 2.5. |
| **Owner / due** | ask the TA by Mon 26 Oct, before the Phase 3 sweep |
| **Evidence** | `reports/agreement.md` |
| **Resolution** | *(unresolved)* |

---

## Opened during Phase 0

### D-08 — Which variables may take `stable`?

| | |
|---|---|
| **Status** | `open` |
| **Question** | `allowed_directions` in `src/schema/ontology.yaml` currently withholds `stable` from seven latent constructs (IMPORTED_INFLATION, RATE_HIKE_EXPECTATIONS, INFLATION_EXPECTATIONS, RBI_FX_INTERVENTION, AIRLINE_COSTS, OMC_MARGINS, FUEL_SUBSIDY) on the grounds that press reports only ever describe them rising or easing. Is that right? |
| **Why it matters** | The `Edge` model rejects a disallowed direction outright, so if an annotator genuinely wants "unchanged" for one of these, extraction fails rather than degrading. |
| **How it gets decided** | Revisit during B1 annotation; if any of the six attracts a `stable` judgement in the dev gold graphs, widen it. |
| **Owner / due** | B · by Phase 2 (Tue 27 Oct) |
| **Resolution** | *(unresolved)* |

### D-09 — Collapse strength to direct-vs-hedged if κ is low?

| | |
|---|---|
| **Status** | `open` (contingency, pre-declared) |
| **Question** | If Cohen's κ on the three strength levels comes in below 0.5, do we collapse to a two-level direct-vs-hedged scheme? |
| **Where** | Proposal §14 risk table; PLAN_MIDSUB.md §2 task 2.5 |
| **Note** | Pre-declaring the rule now is what keeps it from looking like a post-hoc rescue. The `Strength` enum and `strength_rank()` already make the collapse a one-line mapping. |
| **Owner / due** | B · decided by the Phase 2 agreement run (Tue 27 Oct) |
| **Evidence** | `reports/agreement.md` |
| **Resolution** | *(unresolved)* |

### D-10 — `model_inferred` edges may not carry an evidence span

| | |
|---|---|
| **Status** | `resolved` · 19 Oct 2026 |
| **Decision** | The `Edge` model rejects a `model_inferred` edge that carries `evidence_span`. A passage the verifier looked at and rejected goes in `candidate_evidence` instead. |
| **Why** | `evidence_span` is what UER counts against. Letting an inferred edge hold one would make "supported" ambiguous at exactly the point the metric is read. Keeping rejected candidates in a separate field preserves them for failure analysis without ever letting them count as support. |
| **Risk** | If B2's self-labelling turns out to emit spans alongside inferred labels, Track C maps them into `candidate_evidence` at the adapter rather than relaxing the model. |

### D-11 — The frozen corpus window is enforced in the schema

| | |
|---|---|
| **Status** | `resolved` · 19 Oct 2026 |
| **Decision** | `Passage` rejects anything published outside 1 Mar – 30 Sep 2026. |
| **Why** | The as-of filter (A11) guards the *query* side; this guards the *ingest* side, so a parser bug cannot quietly widen the corpus after the freeze. |
| **Revisit if** | Track A needs to ingest a pre-window document for context. It would need its own record type, not a relaxed `Passage`. |

### D-12 — `hop` is breadth-first distance from the anchor

| | |
|---|---|
| **Status** | `resolved` · 19 Oct 2026 |
| **Decision** | `Graph` validates that each edge's `hop` equals one more than the BFS depth of its source from the anchor. Edges whose source is not yet reachable are left unchecked, so a partly built graph still validates mid-loop. |
| **Why** | Every headline number is sliced by hop. If hop labels drift, the central RQ1 claim is unmeasurable, and a shortest-path definition is the only one that is well defined when a node has two incoming chains. |
| **Consequence** | Where two chains reach the same variable at different lengths, the shorter one sets the hop. Worth a sentence in the mid report. |

### D-24 — `main` is protected client-side, not server-side

| | |
|---|---|
| **Status** | `resolved` · 19 Oct 2026 |
| **Decision** | A tracked `pre-push` hook (`scripts/git-hooks/pre-push`, installed by `make hooks`) refuses direct pushes to `main`. Override with `PUSH_TO_MAIN=1` for a genuine emergency. |
| **Why** | GitHub requires Pro for branch protection and rulesets on a *private* repository, and the repo stays private until submission. The hook catches the accidental push, which is the failure that actually happens; it is not a security boundary and anyone can bypass it. |
| **Revisit if** | The repo moves to GitHub Pro — free via the Student Developer Pack. Then add real branch protection (PR + 1 approval, no force-push, no deletion) and keep the hook as a local fast-fail. |
| **Renumbered** | Taken as D-13 on this branch on 19 Oct, the same number `b/verifier-rules` took that day for the span-tolerance row. That branch has since merged into the Track B line, so this row moves to **D-24**. Nothing else referred to it by number. |

---

## Deferred past 30 October

Recorded here so they are not mistaken for oversights (PLAN_MIDSUB.md §3):
all 24 test queries annotated · frozen test runs · B1-R and the two ablations at
full scale · interactive graph UI · blind scoring at scale · repeated-sampling
stability check.
