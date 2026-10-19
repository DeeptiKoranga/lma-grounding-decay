# Decisions log

Every `[needs pilot]` and `[needs TA decision]` item from the proposal, plus the
calls we made while scaffolding, as open rows. **Close a row in the same PR as
the evidence that closes it**: write the number, link the report, and date it.

Status is one of `open` · `resolved` · `deferred`.

Last reviewed: **19 Oct 2026** (Phase 0; D-13 to D-16 added with B6).

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

### D-13 — How much may a quoted evidence span differ from its passage?

| | |
|---|---|
| **Status** | `resolved` · 19 Oct 2026 |
| **Decision** | The rule layer (B6) tries **exact containment first**. Only on failure does it retry through `verify.normalise.normalise_presentation`, which folds presentation and nothing else: runs of any whitespace (including newlines, non-breaking and thin spaces) to one space with the ends stripped; curly quotes and apostrophes to straight ones; en, em and figure dashes, non-breaking hyphens and the Unicode minus to an ASCII hyphen; the ellipsis character to three dots; soft hyphens and zero-width characters deleted. `SpanMatch.kind` records which of the two matched, so a stricter caller can insist on `exact`. |
| **Explicitly NOT normalised** | Case · digits, units and magnitudes · hedging and modality (`could`, `may`, `is expected to`, `poses an upside risk`) · punctuation generally · no stemming, plural folding, stopword removal or accent stripping. |
| **Why** | A span is a *quotation*, and the two sides of the comparison travel through different pipelines: the passage comes out of a PDF or HTML parser that wraps lines where the source wrapped them, while the span comes back through a model's JSON and a CMS's smart quotes. Those differences are invisible to a human reviewer comparing the two, so refusing them would manufacture grounding failures that are really typography. Everything on the "not normalised" list is the opposite case: hedging words are the entire basis of the three strength levels, so a normaliser that equated `may` with `will` would let a conditional claim be quoted as a direct one — exactly the strength inflation RQ1 sets out to measure. Casing is withheld for a narrower reason: it is also how the ontology's proper nouns are written (Brent, RBI, CPI, ATF), and a case-folding verifier could accept a span that quietly renamed a variable. |
| **Consequence** | An exact match reports char offsets into the document text; a normalised match reports none, because collapsing whitespace moves every later character and any offset derived from it would be wrong. Callers that need offsets (B9's corrupted-edge generator) must require `kind == "exact"`. |
| **Revisit if** | Track A's parser turns out to drop or insert characters the list above does not cover — in which case the fix belongs in the parser (A3/A5), not in a wider normaliser here. |

### D-14 — "Mentions both variables" is scoped to the passage, not the document

| | |
|---|---|
| **Status** | `resolved` · 19 Oct 2026 |
| **Decision** | Rule 3 of the verifier (`check_variables_mentioned`) requires both variables of an edge to be named **in the single passage** that is offered as evidence. An edge whose two variables sit in different paragraphs of the same document fails, even though the document as a whole mentions both. |
| **Why** | The unit of evidence in this project is the paragraph: it is what `Passage` models, what retrieval returns and what the span is quoted from. A document-scoped rule would let an edge be "supported" by a document that mentions A in its lede and B eleven paragraphs later with no relation between them asserted anywhere — which is precisely the unsupported established edge UER is meant to catch. Paragraph scope keeps the rule layer's guarantee legible: whatever the LLM verifier later reads, both endpoints were in front of it. |
| **Consequence** | A genuine relation stated across a paragraph break is not expressible as one source-asserted edge. The honest options are to cite the paragraph that states the relation, or to leave the edge `model_inferred`. It also found a fixture inconsistency: `tests/fixtures/graph_brent_hormuz.json` labels edge `e6` (ATF_PRICE → AIRLINE_COSTS) `source_asserted` / `supported`, but the passage it cites (`mint-2026-03-16-atf#p1`) names ATF only as the bare word "Fuel", which is not an ATF_PRICE alias; paragraph 0 has the ATF mention. `tests/unit/test_verify_rules.py` pins the current behaviour and the B6 PR raises the fixture for Track B review. |
| **Revisit if** | B1 annotation finds that reviewers routinely want to cite a two-paragraph span. That would be a change to the chunking unit (A5), not a relaxation of this rule. |

### D-15 — Passing the rule layer means "eligible", never "supported"

| | |
|---|---|
| **Status** | `resolved` · 19 Oct 2026 |
| **Decision** | A clean `RuleReport` returns `verdict = None`, not `VerifyVerdict.SUPPORTED`. Only the LLM verifier (B7) may set `supported`. Rule *failures*, by contrast, are final and map to a verdict: a failed in-corpus check to `out_of_corpus`, a failed as-of check to `after_as_of`, anything else to `unsupported`, with `out_of_corpus` outranking `after_as_of` when both fail. |
| **Why** | Nothing in the rule layer reads the sentence. A passage can mention both variables and contain the span word for word and still not assert the relation, or assert the opposite direction. Returning `supported` from a layer that cannot tell would put rule-only agreement into the same field the UER numerator reads. Failures need no model: no LLM call can rescue evidence published after the as-of date. |
| **Consequence** | `ToolResult.rule_failures` carries the rule names, so C3's `verify_edge` can tell the model to re-read a passage (span miss) rather than search again (as-of miss), and the eval harness can slice leakage apart from weak grounding. The rule layer also never short-circuits: all four checks always run, so one call reports every reason. |

### D-16 — `data/aliases.yaml` was created by Track B, and is Track A's from A6

| | |
|---|---|
| **Status** | `resolved` · 19 Oct 2026 |
| **Decision** | B6 shipped the first `data/aliases.yaml` (starter surface forms for all 46 ontology variables) plus its loader at `src/verify/aliases.py`. Ownership of the **file** stays with Track A per PLAN_MIDSUB.md §1; ownership of the **loader** stays with Track B. The loader tolerates new variables, new forms, both entry shapes (a plain list, or a mapping with `surface_forms` plus A6's own keys) and unknown top-level keys, so A6 can extend it without a code change. It rejects a variable id outside the closed ontology, since with a closed list that is a typo rather than an extension. |
| **Why** | The mention rule cannot run without an alias layer — the ontology says `INR_USD` and `CPI_HEADLINE` while the copy says "the rupee" and "retail inflation" — and A6 is not due until Phase 1. Shipping a starter table unblocked B6 against the fixtures on day 2 without pre-empting A6's retrieval work. |
| **Note** | Alias matching is deliberately **case-insensitive**, which is not the relaxation D-13 refuses: whether a passage talks about the rupee at all is a different question from whether a quote attributed to it is faithful. Forms err towards recall, because a missing form silently loses real evidence while an over-matching one costs one wasted verifier call — the LLM verifier adjudicates ambiguity. Bare "fuel" is withheld from ATF_PRICE on purpose: it reads equally as FUEL_PRICES or CPI_FUEL_LIGHT. |

---

## Noted against the frozen contracts, not changed

`src/schema/` is shared, so B6 raised these rather than editing it. Neither
blocks anything today.

* **`VerifyVerdict` cannot distinguish a span miss from an unmentioned variable.** Both collapse to `unsupported`. The per-rule detail lives in `RuleReport.rule_failures`, which `ToolResult` already carries, so no enum change is proposed — but failure analysis must read `rule_failures`, not `verdict`, to separate the two.
* **`Edge.evidence_passage_id` is optional while `evidence_doc_id` is required.** The rule layer verifies a passage, so an edge that cites only a document cannot be re-checked at paragraph scope without a retrieval round trip. Worth tightening to required-on-`source_asserted` if B4's gold graphs always have a passage id; that is a shared-file change and would need announcing.
* **`Edge.evidence_published_at` is a copy of the passage's timestamp.** `check_on_or_before_as_of` reads the passage, never the edge, so a stale or wrong copy on the edge cannot widen the as-of window. `Graph` already validates the copy against `as_of` independently.

---

## Deferred past 30 October

Recorded here so they are not mistaken for oversights (PLAN_MIDSUB.md §3):
all 24 test queries annotated · frozen test runs · B1-R and the two ablations at
full scale · interactive graph UI · blind scoring at scale · repeated-sampling
stability check.
