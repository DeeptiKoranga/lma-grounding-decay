# Submission verification

The [original proposal](../proposal_lma.pdf) and [mid-submission plan](../PLAN_MIDSUB.md)
define the planned study. The [final report](../reports/final_project_report.pdf) records
what was actually implemented, run and scored. The [README](../README.md) links
to an offline synthetic demo and a model-backed reproduction command.

## Final submission requirements

| Requirement | Where to check it |
|---|---|
| Abstract, introduction and literature review | Front of the final report |
| Dataset, methodology, experiment runs, evaluations and ablations | Report §§3–7 |
| Qualitative examples, challenges and mitigation | Report §7.12 and [five-case failure analysis](../reports/development_failure_analysis_v7.md) |
| Limitations, progress, remaining work, conclusions and references | Report §§8–10 |
| GitHub and reproducibility | Clickable submission branch and README links in the PDF |
| Working demos | [Synthetic browser demo](../reports/demo_fixture.html), [portable pipeline entry point](../scripts/run_demo.py) and [local-model command](reproduction.md#run-the-model-backed-demo) |

## Proposal-to-code trace

| Proposal requirement | Connected implementation | Run evidence and scope |
|---|---|---|
| Freeze and normalize a dated Indian macro news corpus | [Corpus processing](../src/corpus), [cutoff filters](../src/retrieval/filters.py), [runner input hashes](../src/conditions/provenance.py) | [V7 manifest](../data/processed/MANIFEST.md) and [sweep audits](../reports/dev_gold_sweeps_20261110.md). Counts meet target. Business Standard, RBI and PIB coverage is absent. |
| Confirm anchors without using series as causal evidence | [Series store](../src/corpus/series.py), [runtime confirmation](../src/conditions/anchors.py), [versioned dev queries](../data/eval/queries_dev_anchored_v2.jsonl) | All six eligible versioned query preflights confirmed. The historical 56 development runs had no declared runtime criteria and remain unconfirmed. The original eight-episode target is unmet. |
| Retrieve evidence and isolate the reranker | [Selected retriever](../src/retrieval/factory.py), [top-50 reranker](../src/retrieval/rerank.py), [B1-R in the shared runner](../src/conditions/config.py) | [Dev retrieval pilot](../reports/pilot_retriever_v7_attested_20261027.md), [two-query test retrieval](../reports/test_retrieval_descriptive.md), and report §6.2 paired B1-R/B1 and M/B1-R dev results. |
| Extract directed links, verify citations and judge strength | [Extractor](../src/extract/candidates.py), [rule layer](../src/verify/rules.py), [fresh-context verifier](../src/verify/llm_verifier.py) | [Rules arm](../reports/challenge_rules.md), [model arm](../reports/challenge_model_arm.md), [reasoning diagnostics](../reports/reasoning_diagnostics.md) and [public benchmark](../reports/pilot_strength_model.md). 130 challenge items include 23 clean controls. |
| Show inferred vs asserted edges and weakest paths | [Graph schema](../src/schema/models.py), [path aggregation](../src/verify/paths.py), [viewer](../scripts/build_graph_explorer.py) | [Fixed path check](../reports/path_label_check.md), synthetic browser demo, and local export from generated graphs. Baseline assertions show their self-label verification status. |
| Use bounded agent control with ablations | [Controller](../src/agent/controller.py), [competing causes and repair](../src/conditions/pipeline.py), [seven condition flags](../src/conditions/config.py) | All seven ran in each research arm. [Primary controller metrics](../reports/agent_metrics.md), [sensitivity metrics](../reports/agent_metrics_sensitivity.md) and M–A-NoLoop/M–A-NoVerify comparisons. The 40-state next-action metric evaluates the standalone model. |
| Measure tool selection, arguments, faults and unsafe proposals | [Tools](../src/tools/runtime.py), [argument schemas](../src/schema/tools.py), [capability evaluator](../src/eval/capabilities.py) | [Capability report](../reports/capability_diagnostics.json), [20 fault scenarios](../reports/tool_faults_synthetic.json), and report §7.6. The report gives proposal and execution measures. |
| Use explicit baselines and measures at each hop | [UER, inflation and recall](../src/eval/metrics.py), [paired inference](../src/eval/stats.py), [denominator gates](../src/eval/rq.py) | [RQ1](../reports/rq1_hop_decay.md), [RQ2](../reports/rq2_verification.md) and the PDF. H1 and deep-hop H2b are untestable on the available sample. |
| Check research judgments against people | [Reference receipts](../src/eval/references.py), [blind review and scoring](../src/eval/review.py), [sample scorer](../scripts/sample_validate_support.py) | Varun Patil reviewed 30 prose cases, approved 27 revisions and authored 291 revised support judgments with blinding and independence attestations. Report §7.8 gives the revised scores. The separate [blind validation sample](../reports/support_sample_validation.md) records 21/27 informative agreement, κ = 0.560, on the historical labels. |
| Reproduce compute and stability evidence | [Pinned model settings](../configs/model_selection.json), [Kaggle notebook](../notebooks/kaggle_run.ipynb), [run audits](../src/eval/run_audit.py) | [Compute log](../reports/compute_log.md), [one-query stability](../reports/stability_check_20261110.md), and [historical Track C evidence gate](../scripts/validate_phase1_track_c.py). |

## Reproduction checks

- Clean checkout with locked dependencies and no licensed data or model files:
  all seven fixture conditions ran and the browser demo opened. Chrome verified
  condition selection, citation details and keyboard access to inferred edges.
- Live model-backed demo: [7/7 audited graphs](../reports/submission_live_demo.md),
  all with confirmed anchors and no post-cutoff retrieval. B1-R's two nonverbatim
  baseline quotes are recorded in the run summary.
- The two saved 28-graph sweeps, both reasoning summaries, challenge counts, the
  primary RQ tables and the blind sample scores were rechecked against their
  saved evidence. These rechecks retain the original scoring and sample limits.
- The two signed FPI queries completed [all 14 held-out runs](../reports/heldout_generation_20261112.md).
  The audit checks bound logs, completed artifacts, anchors and cutoffs.
- All 291 revised judgments passed packet and scoring checks. The held-out
  UER difference was 0.0 percentage points across two pairs and the recall
  difference was -12.5 points across the same pairs.

## Remaining original-proposal scope

The four signed development queries and two signed test queries fall below the
proposal's original 6/24 design and its 4/16 fallback. Both test queries have
descriptive support scores and fall below the ten-query inference gate.
The [review handoff](independent_review.md) covers additional reference review.
The TA decision on using a calibrated LLM judge remains open.
The novelty case is stated in the report. No TA sign-off on novelty was found
in the project records.
The final report makes no claim that the project met those parts of the
original study or that every model output is correct.
