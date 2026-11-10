# Decisions log

Every `[needs pilot]` and `[needs TA decision]` item from the proposal, plus the
calls we made while scaffolding, as open rows. **Close a row in the same PR as
the evidence that closes it**: write the number, link the report, and date it.

Status is one of `open` · `resolved` · `deferred`.

Last reviewed: **30 Oct 2026** (Track A mid-submission scope closed with deviations;
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

The original whole-project integration findings were subsequently fixed. The
30 October Phase 1 Track C closeout adds the project-schema model decision,
complete four-risk safety review, native Windows/Linux/macOS checks and fresh
private Kaggle execution. See `reports/phase1_track_c_closeout_20261030.md`.

---

## Decisions from the proposal

### D-01 — Which model?

| | |
|---|---|
| **Status** | `resolved` · 30 Oct 2026 |
| **Question** | Qwen3-8B at 4-bit (the prior choice) or Qwen3.5-9B, for every condition? |
| **Where** | Proposal §8, "Model and retrieval" |
| **How it gets decided** | C2: 20 examples × 5 tasks — extraction, strength labelling, JSON validity, tool choice, rejecting unsupported edges. Run on the laptop under MLX at 4-bit. |
| **Owner / due** | C · by Sat 24 Oct |
| **Evidence** | `reports/pilot_model_project_20261030.md`; `reports/project_model_pilot_20261030.json`; `configs/model_selection.json` |
| **Blocks** | Everything downstream of `src/llm/`. One model is used for *all seven* conditions, so this cannot be split per condition. |
| **Locked** | 8 Nov 2026 (#36) as the recorded selection, **but the tie-break is under active challenge in #57 and the switch is still cheap**. #57 and §5.2 show the selected model fails on exactly the two fields the rule layer checks: 17/20 wrong passage IDs and 10/20 nonverbatim quotes, against 0 and 0 for Qwen3.5-9B. The usual reason to refuse a late swap — that it changes the instrument mid-experiment — **does not apply yet**: `runs/` is empty, no sweep has been run, and no reported number depends on the choice. The real cost of switching is 30% more latency per generation (26.6 s against 20.4 s) across seven conditions. The real cost of not switching is that UER may measure extraction failure rather than grounding decay, which is RQ1's validity. This row is deliberately not written as settled; see #57. |
| **Resolution** | `mlx-community/Qwen3-8B-4bit` at `545dc4251c05440727734bcd94334791f6ab0192`, MLX affine 4-bit. Both models completed the same 100 project-schema cases. Highest mean task accuracy; within 0.03, choose lower mean generation latency. Selected mean 61.0%. This is synthetic development selection; weak extraction/tool outputs remain limitations. All seven conditions must use the same pinned model within a sweep. Different backend weight formats are recorded separately. |

### D-02 — Which first-stage retriever?

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

### D-03 — Does the cross-encoder reranker earn its place?

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

### D-04 — Are the eight anchor episodes real?

| | |
|---|---|
| **Status** | `resolved` · answered by D-18 on 27 Oct 2026; closed 8 Nov 2026 (#36) |
| **Question** | Do the eight episodes found in news reports (March oil shock, April ATF increase, May rupee low, June and August RBI meetings, September bond sell-off, …) show up in the official series? |
| **Where** | Proposal §10, "Custom evaluation set" |
| **How it gets decided** | B2, against the macro series from A10. An episode that the series does not confirm is dropped or re-dated. |
| **Owner / due** | B · depends on A10 · by Sat 24 Oct |
| **Evidence** | `data/eval/episodes.md` |
| **Blocks** | All 30 anchored queries hang off these episodes. |
| **Resolution** | **Answered by D-18** · 27 Oct 2026, and closed here on 8 Nov (#36). The answer is no, not as declared: `scripts/confirm_episodes.py` confirms **3 of 8 as declared, and only 2 against official data**. The September bond sell-off is dropped, the March oil shock is redated to an as-of of 1 April or later, and the April ATF increase and both RBI meetings are retained as document-confirmed only. Four anchors survive, which is what D-19's eight-query set is built on. The question was not closed earlier because D-18 was written as its own row; it is the same question and this is its answer. |

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
| **Status** | `resolved` · 8 Nov 2026 — adjudicated, see D-26 |
| **Decision** | The four dev gold graphs exist and are span-exact, but they are **machine-drafted, not human-annotated**, and each file says so in its `notes` field. `scripts/draft_gold_graphs.py` slices every span out of the real passage text between two markers, so no span is retyped, and runs the B6 rule layer on every edge before writing — a draft that cannot be confirmed verbatim never reaches disk. `data/eval/gold/dev/ADJUDICATION.md` is the reviewer's sheet, generated from the graphs so it cannot drift. Until a sign-off row is filled in, every Phase 3 number measured against these is provisional and the mid report says so. |
| **Why** | The corpus arrived on 28 October, two days before the submission, and B4 blocks #42, #43, #44, #37, #38 and #40 — the whole remaining research result. The alternative to drafting was six issues left untouched. The alternative to **labelling** the drafts honestly was presenting a generated standard as reviewed evidence, which would make every UER number unfalsifiable. Doing the mechanical half and naming it is the only version of this that is both useful and true. |
| **Consequence** | The rule layer is not a substitute for judgment and must not be read as one: it confirms a span is verbatim and that the passage mentions both variables, and that is all. Three candidates passed every rule and were dropped by hand — two cited passages that mention both variables while asserting no relation between them, and one whose causation ran backwards (portfolio outflows pressuring the rupee, read as the rupee driving outflows). A reviewer should expect to find more. Twenty edges across four graphs, reaching hop 2; the dropped September anchor (D-18) is still why nothing reaches hop 3, so RQ1's deepest slice stays empty. **Cohen's κ (#37) is not addressable by drafting at all** — it needs two people who have not compared notes. |
| **Outcome** | Adjudication happened on 8 Nov 2026 (D-26). The `MACHINE-DRAFTED, NOT YET ADJUDICATED` string is gone from all four files and the test that asserted it now asserts the adjudication line instead, so the change is a deliberate act with a diff. Four of the twenty drafted edges did not survive. |

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

### D-25 — Alias coverage caps reference-edge recall, and we are not widening the table to fit

| | |
|---|---|
| **Status** | `resolved` · superseded by **D-29**, 10 Nov 2026 — Track A's review is `reports/alias_review_20261110.md`; the table stays frozen for this submission |
| **Decision** | Do **not** extend `data/aliases.yaml` to make gold edges pass. Measure the coverage, report it as a bound on reference-edge recall, and put the evidence in an issue for the file's owner. |
| **Why** | Rule 3 requires both variables named in the cited passage via the alias table, so a variable the corpus never names **cannot carry a source-asserted edge at all**. `scripts/audit_alias_coverage.py` over all 16,472 passages finds **3 of 46 variables never named** (`AIRLINE_SHARES`, `CORPORATE_BOND_SPREAD`, `CPI_FUEL_LIGHT`) and 5 more under ten passages. This was found while drafting the test gold graphs: candidate edges kept failing rule 3 on wording the sources plainly use — "an immediate rate hike" where the table lists "rate hike expectations", "fuel inflation" where it lists "fuel and light". |
| **Consequence** | The proposal's own worked example — crude → ATF price → airline costs → airline shares — has two unevidenceable links at its deep end: `AIRLINE_COSTS` appears in 2 passages, `AIRLINE_SHARES` in none. **The chain used to motivate the study cannot be built from the corpus it froze**, and since it is the deep-hop chain this compounds the hop-2 ceiling rather than being separate from it. `test-cpi-why` targets `RATE_HIKE_EXPECTATIONS`, for which no India-scoped passage carries a recognised surface form, so that query's target may be unreachable as written. |
| **Why not just widen it** | Two causes need opposite fixes. If the corpus does not discuss a quantity, queries touching it must be rescoped; if the sources use wording the table lacks, the table is incomplete and extending it is a correctness fix. Telling them apart means reading the corpus. Widening the table while holding a specific failing gold edge is fitting the instrument to the data, and it would silently change the verifier for every condition, the dev results and the challenge set alike. |
| **Revisit if** | Track A reviews the absent and thin forms against the corpus and extends the table on that evidence, recorded as its own row. Re-run the audit afterwards; `reports/alias_coverage.md` is generated. |

### D-26 — A span must state the direction, not just the relation, to back a gold edge

| | |
|---|---|
| **Status** | `resolved` · 8 Nov 2026 — applied; gold set is 16 edges and the review receipt is signed |
| **Decision** | A gold edge carries a `direction`, so the cited span has to **state which way the destination moves**. A span that asserts a relation, or describes a pricing mechanism, while leaving the sign to the reader does not back a gold edge and is dropped. Four of the twenty drafted dev edges go: `re4` IMPORT_BILL→FISCAL_DEFICIT ("fuelling worries about" the deficit), `oe5` BRENT→ATF_PRICE (the monthly ATF revision formula), `oe3` BRENT→OMC_MARGINS ("fluctuating margins absorbing price shocks"), `ow4` BRENT→INR_USD ("the rupee ... felt the impact of rising crude oil prices"). |
| **Why** | Two annotators labelled all twenty edges independently, blind to the draft and to each other. They agreed on 16 of 20 (`reports/adjudication_kappa.md`), and **all four disagreements were the same case**: a span with a relation but no sign. The reconciliation rule is not a compromise between two readings, it is the one `docs/reproduction.md` already states — reference graphs hold "exact eligible source citations" and gold provenance is `source_asserted` only, with no `model_inferred` edge permitted in a reference graph. Supplying the sign from the anchor's direction is inference, which is the very thing the reference set exists to measure against. Applying the rule drops three edges on one annotator's reading and one on the other's, so neither annotator "won". |
| **Consequence** | Gold falls **20 → 16 edges, exactly 4 per graph**, which is `MIN_EDGES`: one further drop breaks a graph and forces re-drafting. Hop distribution 12 hop-1, 4 hop-2; still nothing at hop 3 (D-18). The **only `correlational` edge is gone**, so strength-inflation corruptions can now only go conditional→direct and the challenge set falls 104 → **89 items** (16 controls, 16 each for four corruption types, 9 inflated_strength). Dropping `oe5` orphans the head of the one crude→ATF→airfares chain: `oe10` (ATF_PRICE→AIRFARES) is kept, because both annotators kept it, but **AIRFARES is no longer reachable from the anchor through gold edges** and its `hop: 2` now records the chain the source describes rather than a path through the gold set. A model producing crude→ATF→airfares is therefore marked wrong on the first link and right on the second; hop-2 figures must say so. This is the **second independent reason** that same chain fails — D-25 already found its deep end unevidenceable on alias coverage — and it is the chain the proposal used to motivate the study. `ATF_PRICE` keeps a node with no inbound edge, so its direction is read from `oe10`'s own span ("the steep increase in jet fuel prices") via `SRC_ONLY_DIRECTIONS` in the drafting script rather than inferred from the anchor. |
| **Also settled** | The duplicate one annotator flagged, INR_USD→IMPORTED_INFLATION on the same passage twice, is **not** a defect: the two copies sit in `dev-rupee-why` and `dev-rupee-effects`, which are separate query graphs that may legitimately cite the same passage. |
| **Receipt** | Both annotators signed `data/eval/gold/dev/review_receipt.json` the same day, which is a separate attestation from the labelling: it binds a SHA-256 of every reference file and of the corpus, so editing a gold graph afterwards invalidates the signature instead of passing under it. `make challenge` no longer passes `--allow-unreviewed`, so the manifest now records `gold_adjudicated: true` with the receipt hash and **the challenge set's false-alarm rate becomes quotable** — a clean control is only clean if its gold edge was right. The guard is still tested: `test_unsigned_gold_needs_the_flag` builds an unsigned set in a temp directory rather than relying on the repository being unsigned, so signing could not quietly delete the test. |
| **Revisit if** | Someone argues the rule is too strict. It is the strictest defensible reading and it costs 4 of 20 edges; the looser reading would have to say where a direction may come from if not the span, and that answer is `model_inferred`, which a reference graph cannot hold. If re-drafting adds edges, prefer candidates whose spans state a sign, and note that the dev set's hop-2 slice is down to four edges. |

### D-27 — "Annotate 10 of the 24 test queries" is unreachable; rescope B-2.6

| | |
|---|---|
| **Status** | `resolved` · 8 Nov 2026 — rescoped to 4 queries; the drafting half is not started |
| **Decision** | #38 asks for 10 annotated queries out of 24 on the test half. **There are four.** `data/eval/queries_test.jsonl` holds `test-cpi-why`, `test-cpi-effects`, `test-fpi-why`, `test-fpi-effects`, and no more are expressible. Annotate **all four**, and report the test figures as descriptive with no confidence intervals, exactly as D-19 already requires. |
| **Why** | The same stale premise that D-21 found in B9. "10 of 24" was written against the original 30-query design; D-18 cut eight candidate anchors to four confirmed, and D-19 split those four by anchor into four dev and four test queries. Neither issue was re-costed afterwards, so two task specs still quote numbers from a design that no longer exists. Finding the second one is a reason to distrust any remaining headline count in `PLAN_MIDSUB.md` that predates 27 October. |
| **Consequence** | No test gold graphs exist at all: `data/eval/gold/` holds `dev` only. Drafting them is the prerequisite for annotating them, and D-25 already found that half-finished attempt failing — `test-cpi-why` targets `RATE_HIKE_EXPECTATIONS`, for which no India-scoped passage carries a recognised surface form, so that query's target may be unreachable as written and its gold graph may not reach `MIN_EDGES` at all. Budget for the test half being thinner than the dev half, or for one of its four queries having no usable gold. |
| **Audited 9 Nov** | `scripts/audit_test_gold_feasibility.py` answers the cheap question before anyone drafts: does the corpus contain passages that *could* carry each query's edges under rule 3 and as-of discipline, counting D-17's preceding paragraph. Result in `reports/test_gold_feasibility.md`. **Three of the four are feasible; `test-cpi-why` is not.** Its target `RATE_HIKE_EXPECTATIONS` is paired with `CPI_HEADLINE` in **exactly one** passage on or before the as-of date, that passage belongs to a Federal Reserve article rather than Indian coverage, and it runs the wrong way — "following the softer-than-expected CPI report, financial markets significantly reduced expectations of an imminent rate increase", where the anchor is CPI **up**. So the query cannot be answered from this corpus as written. The other three have 12 and 28 co-occurring partner variables, comfortably above `MIN_EDGES`. |
| **Correction to D-25** | D-25 says no India-scoped passage carries a recognised surface form for `RATE_HIKE_EXPECTATIONS`. That is too strong: the table's forms match **33 passages**. The real constraint is narrower and worse for this query — the variable is named, but never alongside `CPI_HEADLINE` in Indian coverage. Widening the alias table would therefore not fix `test-cpi-why`, so D-25's "revisit if Track A extends the table" does not apply to it. |
| **Revisit if** | Someone rewrites `test-cpi-why` to a target the corpus connects to CPI — `REPO_RATE` (17 passages), `GDP_GROWTH` (29) and `CPI_FOOD` (36) are all reachable. That is a change to the frozen test set and needs its own row. Otherwise the test half is **three queries, not four**, and the report says so. |

### D-27a — Reading the passages cuts the test half from three queries to two

| | |
|---|---|
| **Status** | `resolved` · 11 Nov 2026 — drafted; **not adjudicated** |
| **Decision** | Draft gold graphs for **`test-fpi-why` and `test-fpi-effects` only**. `test-cpi-effects` joins `test-cpi-why` as undraftable. Both drafted graphs carry five edges across hops 1 and 2, pass the B6 rule layer, and are written by `scripts/draft_test_gold_graphs.py` into `data/eval/gold/test`. |
| **Why** | The feasibility audit (D-27) reported 28 variables co-occurring with `CPI_HEADLINE` and concluded there were "enough distinct partners to reach 4 edges, **if the passages assert relations**". That audit counts co-occurrence and says so. Reading the passages shows the condition fails, and fails structurally rather than marginally: in this corpus Indian headline CPI is almost always the **destination** of the oil shock, not its source. `BRENT`, `FUEL_PRICES`, `CPI_FOOD`, `CPI_CORE` and `WPI` all run *into* CPI, and an effects graph rooted at CPI cannot use an inbound edge. What survives pointing outward is CPI → `REPO_RATE` up, stated conditionally in `mint-74467ebbc52e72308935#p5` and `businessline-eb43f44f9ee97cd0dd7b#p1`, plus a possible hop-2 `REPO_RATE` → `GDP_GROWTH` whose destination the alias table does not match on the bare word "growth". One or two edges against `MIN_EDGES` of 4. |
| **Consequence** | The test half is **two** queries, both anchored on `FPI_FLOWS`. That is below `MIN_QUERIES_FOR_INFERENCE` (10) by a factor of five, so the test half was never going to produce an inferential result and nothing is lost by its size — but it is now small enough that a test table would also be a thin *descriptive* result, and the two graphs overlap heavily because they share an anchor and cutoff. Four of five edges in each cite the same two passages. |
| **Why draft it at all** | A drafted, rule-checked, honestly-labelled test set is worth more than an empty directory even when it cannot be scored: it makes the adjudication step cheap for whoever picks this up, and it converts "the test half does not exist" into a measured statement about what this corpus can and cannot support. `scripts/draft_test_gold_graphs.py` is a separate file from the dev drafter on purpose — the dev gold is receipt-bound and nothing regenerating the test half should be able to touch it. |
| **Guarded** | `tests/unit/test_test_gold.py` fails if a graph appears for either undraftable query, if a drafted graph loses its `DRAFT, NOT ADJUDICATED` provenance, if a `review_receipt.json` appears in `gold/test`, or if the drafted set stops reaching past hop 1. |
| **Revisit if** | A reader wants a test number. The answer is adjudication first: `make adjudicate-test`, two annotators blind under D-26, then a signed receipt. Until then `--references` against `gold/test` must stay refused. |

### D-28 — Run the dev sweep on both models as a declared sensitivity check

| | |
|---|---|
| **Status** | `resolved` · 9 Nov 2026 — pre-registered; neither arm has been run |
| **Decision** | Run the dev sweep twice, once per model, changing **only the generator weights**. `configs/model_selection.json` (Qwen3-8B-4bit) is the **primary arm and supplies every headline number**; `configs/model_selection_qwen35_9b.json` (Qwen3.5-9B-4bit) is a **sensitivity arm reported beside it, never in place of it**. The comparison, and what each outcome is allowed to mean, are written down in `docs/preregistration_model_sensitivity.md` **before any sweep has been run**. D-01 is not reopened and no model is re-selected. |
| **Why** | #57. The C2 pilot tied the two models at 61.0% mean accuracy and the pre-declared rule broke the tie on latency, but the error analysis shows they fail in different places: Qwen3-8B names the wrong passage in 17/20 extractions and quotes nonverbatim in 10/20, where Qwen3.5-9B does neither. Those are the two fields `in_corpus` and `span_verbatim` check. A UER rise with hop therefore has two possible sources — grounding genuinely decaying, or a generator that cites worse where evidence is thinner — and **one arm cannot separate them**. Switching models instead would not remove the problem: Qwen3.5-9B is 20 points worse at strength labelling and 35 points worse at rejecting unsupported edges, which feed strength inflation and the verifier's own job. |
| **Consequence** | Two sweeps, roughly 2.3× the single-arm wall-clock. **Both must finish before either is read**, so neither is interpreted alone. The claim under test is a *shape* claim: a level difference between arms is expected and is not evidence against H1; only a shape difference is. With `MIN_QUERIES_FOR_INFERENCE` at 10 and four dev queries, that gate fires in both arms by construction, so nothing here is inferential, and with no gold edge at hop 3 the `3+` bucket may leave `MIN_BUCKETS_FOR_TREND` unmet — in which case the declared output is `insufficient_data` and a rejection-rate diagnostic, not a trend. That outcome is accepted in advance. |
| **Found while implementing** | `run-dev` and `run-all-dev` sweep `data/eval/development_candidates.jsonl`, whose six ids (`dev-candidate-01..06`) match **no gold graph**. Scoring that output with `--references` raises `reference graph query/cutoff/anchor mismatch` — after the entire sweep has been paid for. No target swept `data/eval/queries_dev.jsonl`, the four queries the gold set is actually built for, so **the sweep as configured could never have produced reference-edge recall or answered H2d**. The new `sweep-dev-primary` / `sweep-dev-sensitivity` / `sweep-dev-both` targets sweep the gold-backed queries, and `test_the_gold_backed_sweep_targets_sweep_queries_that_have_gold` fails if that link is ever broken again. |
| **Revisit if** | The arms disagree on shape. The pre-registered table already says what that means and the answer is to report the confound, not to pick the nicer arm. |

---

### D-29 — Keep the frozen alias table for this submission, and report the ceiling with its cause

| | |
|---|---|
| **Status** | `resolved` · 10 Nov 2026 — closes #58 and the open branch of D-25 |
| **Decision** | Retain `data/aliases.yaml` exactly as pinned for the reported runs (SHA-256 `826f0e59…`). Do **not** apply the two correctness candidates before the 15 November submission. Report reference-edge recall as bounded by a **measured** alias ceiling, naming the two forms that would have been added and the three variables the corpus never names. |
| **Why** | D-25 left the fix to Track A on the condition that the absent and thin forms be read against the corpus. `reports/alias_review_20261110.md` is that review. It finds exactly two forms that genuinely name ontology variables and are missing — "IndiGo and SpiceJet shares" for `AIRLINE_SHARES` (`economic_times-889e909048d7632ba919#p4`) and "fuel component of CPI" for `CPI_FUEL_LIGHT` (`businessline-9109f06a4b23de7ed137#p4`) — and rejects the rest on evidence: "fuel inflation" and "airline stocks" overmatch generic and European coverage, "InterGlobe Aviation" can name a company or a financing, and every corporate-bond-spread candidate turned out to be a sovereign or repo spread. |
| **Why not apply the two** | The alias table is an input to the verifier, so changing it changes rule 3 for every condition at once. The 56-graph development sweep, its 247 support judgements, the challenge set and every score in Section 4 were produced under the pinned table. Applying two forms now would require a fresh versioned sweep **and** a fresh review of any edge whose eligibility changed, inside two days, and would leave the reported numbers describing a configuration that no longer exists. The instrument stays fixed and the limitation is stated. |
| **Consequence** | 3 of 46 variables remain unnameable from this corpus and reference-edge recall keeps its measured ceiling. This is now a known, located bound rather than an unexplained floor: the proposal's worked chain still breaks at `AIRLINE_SHARES`, and `test-cpi-why` stays unanswerable for the separate reason recorded in D-27 — its target is never paired with headline CPI in Indian coverage, which no alias change would repair. |
| **Revisit if** | Any work continues past this submission. The two forms are correctness fixes and belong in the next versioned table, applied together with a re-run and a re-review, not retrofitted to these results. |

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
  (`src/eval/figures.py`, `reports/figures/`) and is what ships. Interactivity is not reachable in
  12 days alongside the experiments, and neither research question needs it.
- **Blind scoring at scale** beyond the 4 dev and 4 test queries.
- **B1-R end-to-end benefit**, deferred since D-03. The retrieval-side
  comparison stands (Recall@10 0.5296 against 0.4259); the end-to-end claim is
  not made.
