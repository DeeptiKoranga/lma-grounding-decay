# Development support assessment — attribution correction, 10 November 2026

The [final project report](final_project_report.pdf) records the later
30-case prose review and the 291 revised support judgments authored by Varun
Patil. The records below concern the original development assessment.

**Varun's correction:** Varun states that he created all of this review work
himself and that the earlier Codex attribution was a mistake. He also confirmed
that he checked and approved the prefilled files. This statement is recorded in
`assessment_manifest.json` as his authorship attestation.

**Audit status:** The task-local preparation and scoring scripts explicitly
recorded the 24 correction graphs and 247 support labels as assistant-produced
drafts. Those scripts, their original outputs and their checksums are retained;
Varun's statement does not by itself establish that the edge labels were
independently made from blank packets. The previous scores below remain
provisional and are not the official #42 review result.

Varun's approval of the prose corrections is now recorded in the correction
JSONs, and both 12-item correction exports passed `eval.prose_review.export`.
Fresh blank support packets were prepared from those exported graphs at
`data/interim/varun_support_review_packet_01` and `_02`. The earlier filled
judgment files were reclassified as approved prefilled labels, with
`independent_review: false`; their edge labels were not changed.

## Historical draft record

The material below records the earlier assessment and its calculations. Its
assistant attribution is what the preserved scripts and generated files said
at creation time; Varun disputes that attribution as stated above.

Both 28-graph sweeps are covered. The assistant read all 24 complete prose answers, corrected their extracted edges without adding sources absent from the answers, and then completed every edge judgment in both arms before computing scores. The resulting packets contain 128 primary-arm and 119 sensitivity-arm edge items. These counts differ from raw extraction because extractor-only claims/citations were removed and omitted answer-stated links were restored.

## Files

Local working directory: `data/interim/assistant_dev_review_20261110/` (gitignored because packets contain corpus text).

| File | Purpose |
|---|---|
| `support_review_packet_01/judgments.json` | 128 completed primary-arm assistant judgments |
| `support_review_packet_02/judgments.json` | 119 completed sensitivity-arm assistant judgments |
| Each packet's `judgments.blank.json` | Formerly blank copy, now filled with the same provisional assistant judgments at the user's request |
| Each packet's `packet.json` / `templates/judgments.blank.json` | Evidence and preserved pristine blank review template |
| Each packet's `private_mapping.json` | Curator-only mapping back to exact derived graph artifacts |
| `prose_corrections_qwen3-8b.json` / `prose_corrections_qwen35-9b.json` | Assistant corrections, exact answer wording, citations and original source hashes; human correction remains false |
| `scores_qwen3-8b.json` / `scores_qwen35-9b.json` | Full per-query, per-hop provisional metrics and descriptive contrasts |
| `edge_audit_qwen3-8b.csv` / `edge_audit_qwen35-9b.csv` | One traceable row per labeled edge with reason |
| `assessment_manifest.json`, `semantic_decisions.json`, `summary.json` | Inputs, protocol, exact source-reading decisions, validation and combined summary |
| `prepare_assessment.py` / `score_assessment.py` | Task-local preparation and metric calculation; metric code in `src/eval/` is unchanged |

## Method and limits

- Assistant assessment requested by the user on 2026-11-10; no independent human review or blinding is claimed.
- All 24 complete baseline prose answers were read before edge support was scored. Original runs and human correction templates are preserved.
- Corrected graphs retain only directed, anchor-reachable claims stated by the answer and representable in the frozen ontology. Upstream explanations with no anchor-reachable cause, non-directional impacts, REER, corporate earnings, total government spending, dollar demand and other out-of-ontology concepts are not invented as new variables.
- Generic inflation is not expanded into CPI/WPI subindices. Imported-inflation questions allow the explicitly discussed import-price pass-through. Trade-balance strain is mapped to a wider trade deficit; qualitative adverse growth effects are mapped to lower GDP growth. These are assistant interpretation choices for human review.
- Established means an explicit answer passage citation or an unhedged directed assertion. Hedged uncited claims are not established. General unhedged mechanisms can be established even when the answer disclaims historical verification; their missing sources still make them unsupported.
- No citation may be added unless that exact passage ID occurs in the answer. A generic reference to sources or a named commentator does not invent a passage identity. For cited prose without an exact quote, use that same saved paragraph verbatim; never substitute another paragraph or source.
- Repeated identical source/destination/direction triples collapse to one claim, preserving the strongest explicit answer wording. Summary links and explicitly stated mediated links are distinct triples.
- Structured B2/A-NoVerify/A-NoLoop/M outputs and their establishment membership remain unchanged. Support is assessed from the attached eligible saved paragraph, verbatim span, relation and destination direction; missing evidence fails. Rejected candidate evidence is not attached support.
- Source strength was read independently of the emitted edge strength. All labels were completed for both arms before calculating any metric. At the time of assistant scoring, the independent/blinded declarations were false; the user-provided metadata update is recorded above. Human prose-correction gates remain unchanged.

Support decisions are made from the attached saved paragraph and its exact quotation, not a live web page, a rejected candidate, another paragraph or general economic plausibility. Explicit contemporaneous co-movement can receive correlational strength; reversed causal attribution and unrelated parallel forecasts are unsupported. All 93 items with an eligible verbatim quotation were read in 59 unique claim/source/quotation/cutoff groups. The other 154 items fail attached-source or verbatim-span eligibility. Duplicate evidence groups receive the same decision in both arms. The assistant had access to model identities and performed both extraction correction and support labeling; neither independence nor blinding is claimed.

The measurements below use the existing project's `score_graph`, query-macro aggregation, paired-query bootstrap, recall guard and RQ denominator gates. Reference recall uses the unchanged, hash-validated signed development gold set. A zero denominator remains n/a; it is not scored as zero error. UER contrasts count only queries with a nonzero established-edge denominator on both sides; the recall guard separately covers all four reference-graph pairs. Four development queries cannot support an inferential claim. Prose extraction choices and assistant support judgments still need independent human checking.

## Provisional overall scores

UER is the unsupported fraction of established edges; lower is better. Displayed percentages are macro averages over queries with nonzero denominators. The UER query column exposes excluded zero-denominator cases.

| Arm | Condition | UER | Strength inflation | Reference recall | UER queries | Established / supported established edges |
|---|---|---:|---:|---:|---:|---:|
| qwen3-8b | B0 | 100.0% | n/a | 0.0% | 3/4 | 6 / 0 |
| qwen3-8b | B1 | 100.0% | n/a | 0.0% | 3/4 | 8 / 0 |
| qwen3-8b | B1-R | 75.0% | 50.0% | 6.2% | 4/4 | 8 / 2 |
| qwen3-8b | B2 | 100.0% | n/a | 0.0% | 4/4 | 22 / 0 |
| qwen3-8b | A-NoVerify | 95.8% | 0.0% | 6.2% | 4/4 | 22 / 1 |
| qwen3-8b | A-NoLoop | 0.0% | 0.0% | 6.2% | 1/4 | 1 / 1 |
| qwen3-8b | M | 75.0% | 0.0% | 6.2% | 4/4 | 8 / 2 |
| qwen35-9b | B0 | 100.0% | n/a | 0.0% | 2/4 | 3 / 0 |
| qwen35-9b | B1 | 52.9% | 37.5% | 18.8% | 4/4 | 14 / 7 |
| qwen35-9b | B1-R | 43.8% | 11.1% | 25.0% | 4/4 | 14 / 10 |
| qwen35-9b | B2 | 89.6% | 100.0% | 6.2% | 4/4 | 21 / 2 |
| qwen35-9b | A-NoVerify | 89.6% | 100.0% | 6.2% | 4/4 | 21 / 2 |
| qwen35-9b | A-NoLoop | n/a | n/a | 0.0% | 0/4 | 0 / 0 |
| qwen35-9b | M | 25.0% | 50.0% | 12.5% | 2/4 | 3 / 2 |

## Provisional hop slices for B1 and M

| Arm | Condition | Hop | UER | Established edges | Queries with denominator | Clears 10-edge gate |
|---|---|---|---:|---:|---:|---|
| qwen3-8b | B1 | 1 | 100.0% | 5 | 3 | no |
| qwen3-8b | B1 | 2 | 100.0% | 2 | 2 | no |
| qwen3-8b | B1 | 3+ | 100.0% | 1 | 1 | no |
| qwen3-8b | M | 1 | 75.0% | 8 | 4 | no |
| qwen3-8b | M | 2 | n/a | 0 | 0 | no |
| qwen3-8b | M | 3+ | n/a | 0 | 0 | no |
| qwen35-9b | B1 | 1 | 47.9% | 13 | 4 | yes |
| qwen35-9b | B1 | 2 | 100.0% | 1 | 1 | no |
| qwen35-9b | B1 | 3+ | n/a | 0 | 0 | no |
| qwen35-9b | M | 1 | 25.0% | 3 | 2 | no |
| qwen35-9b | M | 2 | n/a | 0 | 0 | no |
| qwen35-9b | M | 3+ | n/a | 0 | 0 | no |

## Descriptive B1 versus M comparison

- **qwen3-8b:** paired-query M minus B1 UER = -16.7 percentage points over 3 usable UER pairs; reference-recall difference = +6.2 percentage points over 4 reference pairs. The descriptive recall guard passes. B1 hop-trend verdict: `insufficient_data`.
- **qwen35-9b:** paired-query M minus B1 UER = -10.0 percentage points over 2 usable UER pairs; reference-recall difference = -6.2 percentage points over 4 reference pairs. The descriptive recall guard passes. B1 hop-trend verdict: `insufficient_data`.

These provisional differences do not close #42 or establish a research conclusion. In particular, any apparent UER improvement must be read alongside reference recall, missing denominators and the incomplete hop-depth gates. The primary arm stays primary under D-28 regardless of the sensitivity-arm figures.

## Verification

- All 56 graphs validate against the frozen schema; all 247 item IDs have exactly one completed judgment.
- Packet, private mapping, derived artifact, original artifact, original template, corpus and signed reference hashes are checked.
- Supported items have an evidence-strength judgment; every judgment has an eligibility or source-reading rationale.
- At the time of assistant scoring, both official scoring attempts failed with `complete independent blinded review attestation is required`. That check predates the user-provided reviewer declarations recorded above; official scores have not been regenerated.
- Prose corrections retain false human attestations and separately identify the assistant's work.

For independent human review, use the preserved blank judgments and recheck the assistant's extraction corrections. A reviewer exposed to the corrections/model identities cannot truthfully claim blinded support review of those same items. Do not convert assistant labels to human labels by changing flags.
