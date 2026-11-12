# Varun's reviewed development assessment — 10 November 2026

This dated record documents Varun's account of the original assessment.
The [contemporaneous audit](assistant_dev_support_review_20261110.md) records
the original packet provenance. Section 7.8 of the
[final project report](final_project_report.pdf) gives the later scores from
the 291 revised judgments authored by Varun Patil.

Varun attests that he created and reviewed the 24 prose corrections and the
247 edge-support judgments for the two D-28 development arms. He attests that
his edge judgments were independent and blinded to condition. An earlier
temporary assessment mislabeled his work as assistant-produced; this report
records his correction. The two temporary helper scripts carrying that label
were deleted at his request. Their SHA-256 hashes and the dated correction are
retained in the local archival assessment manifest. Earlier files remain in
that audit archive with their original labels; the formal review packets and
this report carry the current attribution. No original run graph or support
decision was changed.

Both correction exports passed `eval.prose_review.export` for all 12 baseline
answers per arm. The resulting 56 graphs match the previously assessed graph
content and established-edge membership. Existing support decisions were
rebound by condition, query and edge ID to the new hash-bound packets; all 247
labels and evidence-strength choices were preserved. Attribution text in the
judgment notes was corrected. The official `eval.review score` command accepted
both completed packets against the signed dev reference set.

| Arm | Graphs | Support judgments | Packet SHA-256 | Judgment SHA-256 |
|---|---:|---:|---|---|
| Primary Qwen3-8B | 28 | 128 | `93f9e6745708fd49eaa83a3e1bc69c2f996630c67df9273dc471c1d64b6d20c8` | `3fb920c1a42a8cc2630ac89dd9e98265b056dcf4cc3492aadbe6031fd0cbd1f9` |
| Sensitivity Qwen3.5-9B | 28 | 119 | `51012adecd1743eb08ae70e7ffdecfcc3039bc4c21af16a9d6bf2dfb5c55a1f7` | `5fbc7b2ebf6a8943b2fbb5cd8687eecad50c53f86fd8c6fc196bac40751cc2db` |

Full per-query and per-hop scores are in `dev_gold_primary_reviewed.json` and
`dev_gold_sensitivity_reviewed.json`. The primary arm remains primary under
D-28; the sensitivity arm is reported alongside it.

## Development findings

- **RQ1:** Neither arm clears the predeclared three-bucket hop-trend gate.
  B1 has only 5/2/1 established edges at hops 1/2/3+ in the primary arm and
  13/1/0 in the sensitivity arm. No monotone decay claim is supported by this
  four-query development set. See `rq1_hop_decay.md` and
  `rq1_hop_decay_sensitivity.md`.
- **RQ2:** In the primary arm, M minus B1 UER is **−0.167** over three usable
  UER query pairs; reference-edge recall changes **+0.062** over four reference
  pairs, so the descriptive H2d floor of −0.10 holds. In the sensitivity arm,
  UER changes **−0.100** over two usable pairs and recall **−0.062** over four;
  that floor also holds. These are descriptive development
  results, not inferential findings. See `rq2_verification.md` and
  `rq2_verification_sensitivity.md`.
- The primary-arm UER-by-hop chart is `figures/uer_by_hop.svg`. Its denominator
  labels show missing hop groups as N/A rather than zero error.
- The five highest-unsupported-edge primary cases are categorized in
  `development_failure_analysis_v7.md`.

The signed reference receipt and corpus hash remain unchanged. All scoring
continues to use the project's ordinary `eval.review`, `eval.metrics` and
`eval.rq` code and its predeclared denominator and recall gates.
