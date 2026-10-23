# Review handoff — 23 October 2026

Reviewer: **not assigned**. The user has not yet decided who will review the
packets. All judgment fields and reviewer attestations remain blank. Model
verification is an experimental component and cannot supply independent truth.

## Required order

1. **Correct prose extraction.** Review the 18 B0/B1/B1-R prose answers and
   their mechanically extracted graphs. Include omitted links; remove links
   absent from the actual answer; preserve the answer's uncertainty, citation
   errors and substantive mistakes. Do not improve the answer. Export corrected
   artifacts using `eval.prose_review export`.
   In particular, three current B0 graphs are empty even though their answers
   contain explanatory prose; an empty graph is not evidence of no claims.
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

Retrieval review is a separate task. Its existing blinded pool contains 1,988
items across 20 March-only pilot queries at
`data/interim/retrieval_review_v1/`. Follow
`reports/retrieval_review_workflow.md`; broader temporal coverage still needs
reviewed pairs before D-02/D-03 can be accepted.

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
