# Review handoff — 23 October 2026

Reviewer: **not assigned**. The user has not yet decided who will review the
packets. All judgment fields and reviewer attestations remain blank. Model
verification is an experimental component and cannot supply independent truth.

## Corpus acceptance before final review


Before final relevance or support judgments, read `reports/track_a_progress.md`.
The current v3 development corpus has 1,177 documents and 28,391 passages. Its
73-document extraction review and 2,062-item temporal retrieval packet are blank.
The latter is at `data/interim/retrieval_review_temporal_v4/`; hashes and readiness
checks are in `reports/retrieval_v3_review_readiness.json`. Independent corpus
acceptance must precede final relevance selection.

The existing 42 development graphs, prose/support packets and fresh 24-graph
reproduction use archived **v1**, not the current root corpus. For their audit or
review preparation always supply
`--corpus data/interim/frozen_v1_20261023/articles.jsonl`.
The tools now reject a corpus that differs from recorded run provenance.
A new v3 experiment requires new logs and review packets; old human work must
never be relabelled as a different corpus version.

## Start the Track A review

The self-contained local workspace is
`data/interim/track_a_review_delivery_20261023/START_HERE.md`. Open its corpus
review page first; all 73 originals are attached. After independent corpus
sample acceptance, open its separate relevance page. Save the downloaded
`corpus_judgments.json` and `relevance_judgments.json`; each can be reloaded into
the matching page. The browser save/resume check used entirely blank judgments.
Do not infer acceptance from the presence of a prepared folder or saved file.

The curator validates corpus sample review with `corpus.review export` and
retrieval judgments with `retrieval.review export`. Both refuse incomplete
acceptance. Exact commands and the scope of each receipt are in
`docs/reproduction.md`. No ratings, reviewer identity or attestations have been
filled. A reviewer who has seen comparison results cannot claim blinding to them.

## Required order

1. **Correct prose extraction.** Review the 18 B0/B1/B1-R prose answers and
   their mechanically extracted graphs. Include omitted links; remove links
   absent from the actual answer; preserve the answer's uncertainty, citation
   errors and substantive mistakes. Do not improve the answer. Export corrected
   artifacts using `eval.prose_review export`.
   In particular, three current B0 graphs are empty even though their answers
   contain explanatory prose; an empty graph is not evidence of no claims.
   The packet attaches trusted cited paragraphs. When prose cites a passage
   without quoting it, correct the extractor's quotation from that same
   paragraph. Preserve the answer's claim and passage identity; do not substitute
   a new source to improve support.
   If the prose has no citation, remove citations the extractor added. Attached
   context does not authorize supplying a missing citation to improve grounding.
2. **Prepare the final blinded support packet from those corrected artifacts.**
   The curator retains `private_mapping.json`. The reviewer gets only
   `packet.json`, blank `judgments.json`, the annotation guide and the local
   `notebooks/review_edges.html` page. Condition names, model labels and
   established-edge membership are withheld. Review every item before filling
   the reviewer's own identity/date/independence/blinding attestations.
   The prose-correction packet exposes condition names. Anyone who has seen
   those names or the run outputs must not attest to blinded support review of
   the same items; use a different support reviewer in that case.
3. **Prepare reference graphs separately.** Confirm episode dates from accepted
   series; freeze the intended queries; build independently reviewed evidence
   graphs with eligible exact spans. References are needed for the recall guard.
   `eval.references` prepares a blank hash-bound review receipt; an independent
   reviewer must complete it before reference recall can be scored.
   The six current source-backed candidates are not accepted development gold.
4. **Double-annotate a shared subset independently.** Record both original
   judgments, calculate agreement and adjudicate disagreements. Apply the
   predeclared strength-collapse rule only when its measured trigger is met.
5. **Score and plot.** Export UER/strength results only after complete support
   review and prose correction. Missing references mean missing recall; missing
   hop denominators remain null. No hypothesis acceptance follows from this
   unreviewed development run.

Retrieval review is a separate task. Use the current v3 20-question,
March–September packet above. The older March-only 1,988-item and v2 2,057-item
packets remain historical records. Follow `reports/retrieval_review_workflow.md`;
D-02/D-03 remain open until accepted independent review.

The synthetic action/safety probes also need their own interpretation. Tool
selection against scripted expectations is not accuracy on real human-labelled
states, and regex safety flags need human adjudication of the full responses.

## Local handoff locations

The final locations and hashes are recorded in `reports/review_readiness.json`
once the completed development assembly has been audited. Packets under
`data/interim/` contain corpus text and remain local. Do not commit them, copy
the curator mapping into reviewer files or prefill attestations.

Commands, dependencies and correction/scoring gates are documented in
`docs/reproduction.md`. This handoff records prepared work; it does not claim
that a person has completed any of these reviews.
