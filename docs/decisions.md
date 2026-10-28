# Decisions log

Every `[needs pilot]` and `[needs TA decision]` item from the proposal, plus the
calls we made while scaffolding, as open rows. **Close a row in the same PR as
the evidence that closes it**: write the number, link the report, and date it.

Status is one of `open` · `resolved` · `deferred`.

Last reviewed: **27 Oct 2026** (Track A mid-submission scope closed with deviations;
development selections complete; subsequent user-attested Track A review records
pass acceptance validation, with procedure-verification limits retained).

The [Track A closeout](../reports/track_a_mid_submission_scope_20261027.md)
adopts the acquired source mix, narrative-only PDF extraction and sparse
original-vintage six-series store for the development handoff. This is an
implementation disposition under the user's instruction to finish Track A;
it is not TA/team acceptance, a publisher licence or a research-review receipt.
The original proposal and export gates remain unchanged. Varun subsequently
supplied reviewer/date and independent/blinded review attestations. Both exports
pass, with original label provenance preserved; procedure and exposure timing
are not independently verified. See
`reports/track_a_reviewer_identity_20261027.json`.

The subsequent whole-project audit confirms that D-02's selected BGE-M3 is not
yet wired into the conditions command. A resolved pilot choice does not mean
its integration is complete. See `reports/whole_project_audit_20261027.md` for
that gap and four other integration/reproduction findings.

---

## Decisions from the proposal

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
| **Status** | `resolved` for the scoped Track A retrieval pilot on user-attested review |
| **Question** | BM25, BM25 + alias expansion, bge-m3, or hybrid with reciprocal rank fusion? |
| **Where** | Proposal §7 Table 1 and §8 |
| **How it gets decided** | A8: 20 query–evidence pairs × 4 configs; Recall@5, Recall@10, MRR. **Decision rule is pre-declared: take the simplest config within 0.03 Recall@10 of the best.** |
| **Owner / due** | A · by Sat 24 Oct |
| **Evidence** | `reports/pilot_retriever_v7_attested_20261027.md`; `reports/track_a_retrieval_selection_20261027.json` |
| **Blocks** | B1, B1-R and every agent condition share one first-stage retriever (proposal §11). |
| **Development selection — 26 Oct** | BGE-M3: Recall@10 0.4259 versus 0.3518 plain BM25, 0.3551 alias BM25 and 0.4161 hybrid. Selected by the declared 0.03 rule on 20 queries/2,035 pooled judgments (195 relevant). Single Codex review with previous results exposure; no independent receipt. See `reports/track_a_retrieval_selection_20261026.json`. Archived v1 run settings stay unchanged. |
| **Resolution** | BGE-M3 selected; the 27 October receipt-bound pilot reproduces Recall@10 0.4259. Track A review records pass on Varun's independent/blinded review attestations. Original label provenance and limits of self-reported procedure remain disclosed. See `reports/track_a_retrieval_selection_20261027.json`. Record validation does not accept experiment outcomes. |

### D-03 — Does the cross-encoder reranker earn its place? `[needs pilot]`

| | |
|---|---|
| **Status** | `deferred` for end-to-end benefit; retrieval-pilot component complete |
| **Question** | Does bge-reranker-v2-m3 over the top 50 improve retrieval enough to keep B1-R as a condition, and does better ranking alone close the gap to M? |
| **Where** | Proposal §8, §11 |
| **How it gets decided** | A9: same metrics as D-02, on top of whichever retriever D-02 picks; then end-to-end as B1-R. |
| **Owner / due** | A · retrieval numbers by Sat 24 Oct; end-to-end deferred past 30 Oct |
| **Evidence** | `reports/pilot_retriever_v7_attested_20261027.md`; `reports/track_a_retrieval_selection_20261027.json` |
| **Note** | B1-R at full scale is explicitly deferred past the mid-submission (PLAN_MIDSUB.md §3). |
| **Development selection — 26 Oct** | Retain the pinned top-50 cross-encoder for B1-R development: Recall@10 0.5296 versus dense 0.4259, a 0.1037 gain. Same complete development pool as D-02; no independent receipt or end-to-end benefit established. |
| **Resolution** | Receipt-bound retrieval comparison reproduces Recall@10 0.5296, a 0.1037 gain; retain the reranker for B1-R. Review records pass on Varun's declared conditions. Full end-to-end comparison remains deferred as planned; no end-to-end benefit is claimed. |

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
| **Status** | `superseded by D-17` · 19 Oct 2026, superseded 27 Oct 2026 |
| **Decision** | Rule 3 of the verifier (`check_variables_mentioned`) requires both variables of an edge to be named **in the single passage** that is offered as evidence. An edge whose two variables sit in different paragraphs of the same document fails, even though the document as a whole mentions both. |
| **Why** | The unit of evidence in this project is the paragraph: it is what `Passage` models, what retrieval returns and what the span is quoted from. A document-scoped rule would let an edge be "supported" by a document that mentions A in its lede and B eleven paragraphs later with no relation between them asserted anywhere — which is precisely the unsupported established edge UER is meant to catch. Paragraph scope keeps the rule layer's guarantee legible: whatever the LLM verifier later reads, both endpoints were in front of it. |
| **Consequence** | A genuine relation stated across a paragraph break is not expressible as one source-asserted edge. The honest options are to cite the paragraph that states the relation, or to leave the edge `model_inferred`. It also found a fixture inconsistency: `tests/fixtures/graph_brent_hormuz.json` labels edge `e6` (ATF_PRICE → AIRLINE_COSTS) `source_asserted` / `supported`, but the passage it cites (`mint-2026-03-16-atf#p1`) names ATF only as the bare word "Fuel", which is not an ATF_PRICE alias; paragraph 0 has the ATF mention. `tests/unit/test_verify_rules.py` pins the current behaviour and the B6 PR raises the fixture for Track B review. |
| **Revisit if** | B1 annotation finds that reviewers routinely want to cite a two-paragraph span. That would be a change to the chunking unit (A5), not a relaxation of this rule. |
| **Outcome** | Revisited after four days, not after annotation: the `e6` case below turned out to be the normal shape of the copy rather than a fixture slip. See D-17. |

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

### D-17 — Rule 3 searches the cited paragraph plus the one before it

| | |
|---|---|
| **Status** | `resolved` · 27 Oct 2026. Supersedes D-14. |
| **Decision** | `check_variables_mentioned` looks for the two variables across a **two-paragraph window**: the cited paragraph and the paragraph immediately preceding it in the same document. The window reaches backwards only, stops at one paragraph, and never crosses a document boundary. **Rule 4 does not move** — the quoted span must still be verbatim in the cited passage. `preceding_window()` derives the window; the entry points take a `document` argument and default to the strict, passage-only behaviour when it is not supplied, so a caller that forgets cannot get a falsely permissive result. |
| **Why** | D-14 was measuring the rule's strictness instead of the thing the project is about. Indian macro copy states a relation across a paragraph break constantly — paragraph 0 names aviation turbine fuel, paragraph 1 says "the increase feeds straight through to airline operating costs". Rejecting those edges under-labels `source_asserted`, which pushes reference-edge recall down (the H2d guard) while flattering UER: the system would look well grounded largely because it had declined to claim anything. One paragraph back is the span an anaphor actually reaches across; two or more starts admitting the "A in the lede, B eleven paragraphs later" case D-14 was right to exclude. |
| **Consequence** | `MentionMatch.scope` records whether both variables were in the cited paragraph (`cited`) or the window was needed (`window`), and `src_passage_id` / `dst_passage_id` name where each was found. **The eval harness (C7) must report UER for the two scopes separately**, or a headline figure can rest on cross-break edges without saying so. Fixture edge `e6` (ATF_PRICE → AIRLINE_COSTS) now clears all four rules with `scope: window`; it was never a fixture bug. |
| **Carries a cost** | Two things must follow or the comparison tilts: the window has to be expressible over Track A's chunks (A5), and the same window must apply when B1/B2 prose is converted to edges — if M gets the window and the baselines do not, M's UER advantage is partly an artefact of the scoring rule. |
| **Revisit if** | Blind scoring (3.2) finds reviewers disagree with `scope: window` edges materially more often than with `scope: cited` ones. The fix would be to report them as a separate stratum rather than to narrow the window again. |

### D-18 — Only two anchor episodes are confirmed against official data

| | |
|---|---|
| **Status** | `resolved` · 27 Oct 2026 |
| **Decision** | The eight candidate anchors are declared in `data/eval/episodes.yaml` and confirmed by `scripts/confirm_episodes.py` under as-of discipline; `data/eval/episodes.md` is generated, never hand-written. Outcome: **3 of 8 confirmed as declared, and only 2 of those against official data.** The September bond sell-off is **dropped** (the yield series ends 31 August and never reaches 7%). The March oil shock is **redated** to an as-of date of 1 April or later (Brent holds no March observation). The April ATF increase and both RBI meetings are retained as **document-confirmed only**, since no ATF or repo-rate series is held. |
| **Why** | The proposal says the episodes "will be confirmed against official data". Checking that claim against the store rather than asserting it leaves only USD/INR (FBIL) and headline CPI (MOSPI) meeting the standard. Brent, the benchmark yield and FPI are news-reported observations by Track A's own account (`data/series/README.md`), so they are dated but not official, and `EpisodeConfirmation.official_source` separates the two rather than letting the distinction vanish. |
| **Consequence** | The query set cannot be anchored on eight episodes as planned. Four anchors are usable (three confirmed plus the redated oil shock), which matches the proposal's own fallback of 4 dev queries — so B3 and B4 should be scoped to those four rather than six. **No anchor may use an as-of date earlier than its `earliest as-of` column**, or the anchor rests on a vintage published after the query date. The dropped September episode also removes the only bond-market anchor, so RQ1's deep-hop coverage loses its yield chain. |
| **Revisit if** | Track A extends the series store. The check is re-runnable and `--check` fails if `episodes.md` goes stale, so a later import can only improve this, never silently change it. |

### D-19 — Eight queries over four anchors, split by episode

| | |
|---|---|
| **Status** | `resolved` · 27 Oct 2026 |
| **Decision** | The query set is **8 queries, not 30**: one `why` and one `effects` question for each of the four anchors that survived D-18. Dev is the oil-shock and rupee anchors (`data/eval/queries_dev.jsonl`); test is the CPI and FPI anchors (`data/eval/queries_test.jsonl`). **The split is by anchor, not by question type**, so dev and test share no episode, no as-of date and therefore no retrieved passages. `effects` questions carry no `target_var` so they stay open-ended; `why` questions name one. |
| **Why** | D-18 left four usable anchors, so 30 queries were no longer expressible. Splitting by question type instead would have put both halves of the same event on both sides of the split: tuning the verifier on the dev oil question would then leak through shared passages into the test oil question, and the test result would be partly a measurement of the dev set. Splitting by anchor costs nothing and removes that. |
| **Consequence** | The test half is four queries, so no test-set claim will have a usable confidence interval. Treat the test numbers as descriptive and say so. Both dev anchors are confirmed under as-of discipline, but the oil anchor is the redated one and rests on a news-reported Brent observation, so the dev half is not uniformly official-grade evidence. |
| **Revisit if** | Track A extends the series store enough to revive the September bond anchor or add a repo-rate series. Either would restore a fifth and sixth anchor and let the test half grow. |

### D-20 — The dev gold graphs are machine-drafted and labelled as such

| | |
|---|---|
| **Status** | `open` — drafted 28 Oct 2026, awaiting adjudication |
| **Decision** | The four dev gold graphs exist and are span-exact, but they are **machine-drafted, not human-annotated**, and each file says so in its `notes` field. `scripts/draft_gold_graphs.py` slices every span out of the real passage text between two markers, so no span is retyped, and runs the B6 rule layer on every edge before writing — a draft that cannot be confirmed verbatim never reaches disk. `data/eval/gold/dev/ADJUDICATION.md` is the reviewer's sheet, generated from the graphs so it cannot drift. Until a sign-off row is filled in, every Phase 3 number measured against these is provisional and the mid report says so. |
| **Why** | The corpus arrived on 28 October, two days before the submission, and B4 blocks #42, #43, #44, #37, #38 and #40 — the whole remaining research result. The alternative to drafting was six issues left untouched. The alternative to **labelling** the drafts honestly was presenting a generated standard as reviewed evidence, which would make every UER number unfalsifiable. Doing the mechanical half and naming it is the only version of this that is both useful and true. |
| **Consequence** | The rule layer is not a substitute for judgment and must not be read as one: it confirms a span is verbatim and that the passage mentions both variables, and that is all. Three candidates passed every rule and were dropped by hand — two cited passages that mention both variables while asserting no relation between them, and one whose causation ran backwards (portfolio outflows pressuring the rupee, read as the rupee driving outflows). A reviewer should expect to find more. Twenty edges across four graphs, reaching hop 2; the dropped September anchor (D-18) is still why nothing reaches hop 3, so RQ1's deepest slice stays empty. **Cohen's κ (#37) is not addressable by drafting at all** — it needs two people who have not compared notes. |
| **Revisit if** | Adjudication happens. The `MACHINE-DRAFTED, NOT YET ADJUDICATED` string is asserted by a test, so removing it is a deliberate act with a diff, not a quiet edit. |

### D-21 — The 125-item challenge set is unreachable; rescope B9

| | |
|---|---|
| **Status** | `resolved` · 29 Oct 2026 — rescope applied. B9 is a Track B task in PLAN_MIDSUB.md, so the gates are Track B's to move; `reports/challenge_rules.md` is the result. |
| **Decision** | Do not build B9 at 125 items, and do not lower the gates in `src/eval/challenge.py` to make it fit. Report the achievable size with per-type denominators instead. See `reports/b9_feasibility_20261028.md`. |
| **Why** | The generator gates on 25 eligible seeds and 20 hedged seeds. The dev gold set supplies **19 and 9**. This is not a shortfall that annotation closes: `MAX_EDGES` is 6 and D-19 left four dev queries, so the dev gold set has a ceiling of 24 edges, and eligibility also discards every `correlational` edge. 25 eligible seeds is therefore unreachable by construction. Issue #20's "100 + 25" was written against the original 30-query design, where the dev half alone would have carried roughly 150 gold edges; D-18 and D-19 invalidated that premise without anyone re-costing B9. |
| **Consequence** | Corruption-detection and false-alarm rates will rest on 85 items at uneven per-type counts (19 each for reversed relation, unsupported intermediate, wrong date and wrong target; 9 for inflated strength), so **every rate must be printed with its denominator** and no macro average over types is meaningful. Padding the seed pool from the test gold graphs is ruled out: it would leak the test set into a diagnostic the system is tuned against, which is exactly what D-19's split-by-anchor exists to prevent. |
| **Outcome** | `MIN_SEEDS` lowered 25 → **12** and `MIN_INFLATABLE_SEEDS` 20 → **5** in `src/eval/challenge.py`, keeping a floor so a set too small to quote is still refused. Built: **104 items** — 19 controls plus 85 corruptions at 19/19/19/19 and **9** for `inflated_strength`, exactly the uneven split predicted. `data/eval/challenge_manifest.json` carries `counts_by_kind`, so no rate can be quoted without its denominator. |
| **Revisit if** | The series store grows enough to revive a fifth or sixth anchor (D-18's revisit condition). Two more anchors would add up to 12 gold edges and restore the original 25-seed gate honestly. |

### D-22 — The RQ1/RQ2 reporting gates, declared before any results exist

| | |
|---|---|
| **Status** | `resolved` · 28 Oct 2026, in commit `5663458`, **before any v7 run has been scored** |
| **Decision** | Four thresholds govern what the RQ1 and RQ2 reports are allowed to claim. They live in `src/eval/rq.py` and `src/eval/metrics.py`, not in the reporting script, and this row dates them. **`MIN_ESTABLISHED_PER_BUCKET = 10`** — a hop bucket with fewer established edges is printed but cannot support a claim about that hop. **`MIN_BUCKETS_FOR_TREND = 3`** — a monotone trend needs all three buckets usable. **`MIN_QUERIES_FOR_INFERENCE = 10`** — below that, every figure is marked descriptive only. **`minimum_M_minus_B1 = -0.10`** — the H2d recall floor, from the proposal. |
| **Why** | A threshold chosen after seeing the data is not a threshold. The dev set is four queries (D-19) and the hop ≥3 bucket is expected to be thin or empty (D-18 dropped the September bond sell-off, the only anchor with a yield chain), so the temptation on 30 October will be to report a two-point "trend" over hops 1 and 2 macro-averaged over four queries. That would look exactly like a result while supporting nothing. Fixing the numbers now, with a date and a commit, is what makes the word *pre-declared* true in the report. |
| **Consequence** | On the dev set `MIN_QUERIES_FOR_INFERENCE` fires **by construction**: no dev figure can be presented as inferential, whatever it turns out to be. If the deep bucket is empty the report states that as the finding and names D-18 as the cause, rather than printing a trend across what remains. RQ2 will not describe a UER drop as a repair while the recall guard is undetermined, because a verifier deleting edges it cannot confirm produces the same headline number. |
| **Revisit if** | The test half is annotated (#38) or the series store grows enough to revive an anchor (D-18), either of which raises the query count. **Lowering any of these four after a result is seen is not a revisit, it is a different study** — a change here must be dated and justified on its own, with the superseded value kept visible. |

### D-23 — Corruption detection splits cleanly between rules and the model

| | |
|---|---|
| **Status** | `resolved` · 29 Oct 2026 · `reports/challenge_rules.md` |
| **Decision** | Report the challenge set as two arms with a stated division of labour, not as one detection rate. The B6 rule layer owns the three **citation** corruptions; the semantic verifier owns the two that change meaning without changing text. |
| **Why** | Run on the 104-item set with no model at all, the rules flag **57 of 57** `unsupported_intermediate`, `wrong_date` and `wrong_target` items, with **0 false alarms on 19 clean controls**. They flag **0 of 19** reversed relations and **0 of 9** inflated strength labels. That is not a shortfall: reversing an edge leaves the same two variables in the same passage with the same verbatim span, so all four rules still pass, and no rule reads the `strength` field at all. The split is by construction, and the tests assert the misses so a rule cannot quietly grow a capability it does not document. |
| **Consequence** | Two claims the mid report can make, in opposite directions. **For the verifier:** 28 of 85 corruptions — a third, and the two families a careless graph is most likely to contain — cannot be caught by matching text, which is the project's clearest evidence that the semantic step earns its budget. **Against spending budget badly:** the other three families are caught deterministically, for free, with no model, so a verifier re-checking citations is spending calls where a regex already wins. The per-type denominators are uneven (D-21) so every rate is quoted with its own; a macro average over families would be meaningless. |
| **Caveat** | Corruption detection is sound on un-adjudicated gold because each corruption is applied mechanically and known by construction. **The 0.000 false-alarm rate is not**: a control is clean only if its gold edge was right, so that figure inherits whatever adjudication changes. `gold_adjudicated: false` is recorded on every row. |

---

## Deferred past 30 October — revised 29 Oct for a 15 November final

The original list was written against a four-week run-out. The final submission
is **15 November** with work winding up **12 November**, so it splits in two.

**Scheduled inside 1–12 November** (see `reports/mid_submission.md` §8):

| Item | When |
|---|---|
| Test-query annotation — **four** queries, not 24 (D-19) | 1–2 Nov |
| Frozen test runs | 9 Nov |
| Both ablations at full scale (A-NoVerify, A-NoLoop) | in the 2 Nov and 9 Nov sweeps |
| Repeated-sampling stability check | 7–8 Nov, one query |
| Challenge-set and strength **model** arms | 7–8 Nov |

**Dropped for the 15 November date**, and reported as limitations rather than
left to look like oversights:

- **The interactive event-impact graph.** Static SVG/PNG rendering exists
  (`src/eval/figures.py`) and is what ships. Interactivity is not reachable in
  12 days alongside the experiments, and neither research question needs it.
- **Blind scoring at scale** beyond the 4 dev and 4 test queries.
- **B1-R end-to-end benefit**, deferred since D-03. The retrieval-side
  comparison stands (Recall@10 0.5296 against 0.4259); the end-to-end claim is
  not made.
