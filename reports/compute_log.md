# Compute log — Track C closeout, 30 October 2026

No paid API request was made. The two local model pilots ran sequentially on
Apple M4 / 16 GB under pinned MLX affine 4-bit. The frozen raw outputs include
actual backend-reported token counts and measured model-call wall times.
These local durations exclude setup/model loading and are not GPU-active or
total allocated device hours.

| Work | Completed calls | Prompt tokens | Completion tokens | Model-call seconds |
|---|---:|---:|---:|---:|
| Project-schema C2 qwen3-8b | 100 | 156,889 | 7,661 | 2035.586 |
| Project-schema C2 qwen3.5-9b | 100 | 156,999 | 10,480 | 2661.630 |
| Selected-model C10 safety | 25 | 2,375 | 1,365 | 252.964 |
| Excluded prompt-ambiguity attempt | 13 | 19,116 | 1,832 | 253.519 |

The excluded attempt and its interrupted in-flight call remain separate. The
unfinished call has no complete usage measurement and no invented token/time
entry. Included C2 cases/rules were frozen before the two included runs. Model
bytes, source hashes and runtime packages are in
`reports/project_model_pilot_inputs_20261030.json` and the safety input receipt.

The private two-T4 C11 execution at source `245e0fd` measured **2,179.985 wall
seconds including setup**, or **1.211103 visible allocated GPU-hours**. The
inner run interval was 1,641.941 seconds / 0.912189 GPU-hours and is a subset,
not additional usage. All 14 graphs and their bound logs passed the remote and
local audits; all 14 were cached on unchanged resume. The two-GPU/two-hour limit
was respected. Provider startup/teardown outside the entrypoint, GPU-active
time and exact billed hours are not measured. See
`reports/kaggle_verification_evidence_20261030/` and
`reports/kaggle_live_verification_20261030.json`.

The account quota observation after completion was 2,186.168 seconds (0.607269
hours) out of 30 hours. This provider quota is recorded separately from the
two-device allocation measure; it is not labelled GPU-active time or a billing
receipt. See `reports/kaggle_quota_observation_20261030.json`.

The older 28 October Kaggle C1/C2 notebook execution intervals sum to 501.008
and 1,006.978 cell-wall seconds. Their GPU-active/allocation/billed hours were
not captured and remain unknown. See
`reports/kaggle_compute_evidence_20261030.json`. Earlier local-only statements
below keep their original scope and do not deny the subsequent Kaggle runs.

---

# Compute log — updated 25 October 2026

Actual completed-call usage from validated local logs. All generation used pinned
Qwen3-8B 4-bit revision `545dc4251c05440727734bcd94334791f6ab0192` under MLX.
No paid API requests were made. No Kaggle job was executed and no Kaggle GPU
hours are claimed. Token counts are backend-reported; times below are measured
model-call wall times, **not GPU-active hours or total device/runtime expense**.

## Included seven-condition development assembly

| Condition | Graphs | Model calls | Prompt tokens | Completion tokens | Model-call seconds | Tool calls |
|---|---:|---:|---:|---:|---:|---:|
| A-NoLoop | 6 | 8 | 29,909 | 4,458 | 554.21 | 72 |
| A-NoVerify | 6 | 14 | 55,904 | 9,705 | 1035.32 | 27 |
| B0 | 6 | 12 | 16,680 | 1,986 | 312.78 | 0 |
| B1 | 6 | 12 | 45,255 | 5,360 | 674.65 | 6 |
| B1-R | 6 | 12 | 45,907 | 5,805 | 765.88 | 6 |
| B2 | 6 | 6 | 28,847 | 4,209 | 692.36 | 6 |
| M | 6 | 23 | 37,823 | 5,781 | 710.48 | 71 |
| **Total** | **42** | **87** | **260,325** | **37,304** | **4745.68** | **188** |

The baseline phase and corrected controller phase retain different source hashes
and identical shared input hashes in `runs/development_complete_20261023/phases.json`.
The assembly is unreviewed development work. B1-R cross-encoder work runs in a
separate cached CPU worker; it is not included in generator/verifier token or
model-call totals. Summed case wall times include retrieval/worker overhead:

- A-NoLoop: 554.71 case wall seconds.
- A-NoVerify: 1039.28 case wall seconds.
- B0: 313.42 case wall seconds.
- B1: 675.70 case wall seconds.
- B1-R: 851.90 case wall seconds.
- B2: 692.93 case wall seconds.
- M: 714.76 case wall seconds.

These sums exclude model/index loading and idle time between cases/phases; they
must not be treated as GPU-active time. Original timestamps remain in the logs.

## Additional measured local work

| Work | Model calls | Prompt tokens | Completion tokens | Model-call seconds |
|---|---:|---:|---:|---:|
| 40 action and 25 safety synthetic probes | 65 | 160,470 | 4,234 | 1765.61 |
| Fresh-clone four-condition, one-query probe | 9 | 21,409 | 3,406 | 415.28 |
| Excluded first integration probe | 1 | 4,731 | 764 | 70.21 |
| Excluded preliminary direct-graph sweep | 5 | 12,269 | 1,763 | 172.60 |
| Excluded interrupted old agent attempt | 0 | 0 | 0 | 0.00 |

An interrupted in-flight generation has no completed response/usage record. Its
unmeasured work is not filled with an estimate, so these are not all-device totals.
Excluded runs never enter support comparisons. Synthetic probes have no human
support labels and no synthetic safety certification is claimed.

## Retrieval and downloaded artifacts

The earlier BGE-M3 precomputation phase recorded 977.67 seconds; the corrected
full-corpus comparison recorded 327.29 seconds, with cached work reused. Their
sum, 1,304.96 seconds, excludes downloads, previous checks and the saved-index
reload. See `reports/retrieval_run_provenance.json` for exact scope and hashes.

The local generator/tokenizer files total 4,623,782,544 bytes; file hashes and
runtime versions are in `reports/generator_provenance.json`. Raw weights, corpus,
vectors and full logs remain ignored. Heavy dependency versions are pinned in
`configs/requirements-local-llm.txt` and `configs/requirements-retrieval.txt`.

The 20 synthetic faults are boundary tests, not GPU model-recovery runs. The
fresh probe reuses the local model runtime and corpus with fresh-clone source
code; it does not establish an all-laptop/Kaggle or full frozen-gold sweep.

## Full fresh-source reproduction and repaired-corpus retrieval

A separate complete B0/B1/B2/M sweep over all six candidates produced 24 graphs,
all identical to their earlier v1 canonical graphs after dropping only `run_id`.
Source commit: `bbc9288`. It reused the local MLX environment/weights, archived
v1 corpus and original three series; it did not execute on other team machines
or Kaggle. Validated logs record **53 model calls, 128,605 prompt tokens, 17,336
completion tokens, 2,436.34 model-call wall seconds and 83 tool calls**. These
are additional to the original 42-graph assembly, not substituted totals.
See `reports/fresh_full_development_validation.json` and
`reports/fresh_full_development_logs.json`.

The repaired v3 corpus's real CPU retrieval/reranking comparison took **357.87
wall seconds**, reusing a text/model-checked embedding checkpoint; this excludes
earlier encoding, downloads and checks. A separate fresh-process saved-index
reload plus two real query embeddings/searches took **16.50 wall seconds**.
All 28,391 saved passages match the v3 corpus. These durations are phase wall
times, not GPU-active time. No independent relevance scores are claimed.

## 25 October seed audit and rejected relevance screen

The real 20-question retrieval/reranker rerun with 37 source-audited seeds took
**146.30 phase wall seconds** initially; the replay after deterministic pair-file
serialization took **145.04 seconds** and produced identical metrics. Both reused
the saved v3 dense index and local pinned
BGE models. It excludes earlier encoding/downloads. Its source audit is Codex
development curation, not independent human annotation. See
`reports/pilot_retriever_v3_audited_seeds_20261025.md`.

The separate local Qwen relevance classifier was stopped after source inspection
found background false positives. All outputs are excluded from labels and
research decisions. Eleven completed batches covered 313 items, recording
**46,463 prompt tokens, 5,574 completion tokens and 812.83 model-call wall
seconds**. Its interrupted in-flight call has no completed usage record and is
not filled with an estimate. Two earlier formatting-failure attempts also remain
excluded: three completed calls in total; their actual usage is recorded in
`reports/relevance_screen_failure_audit_20261025.json`. No paid API or Kaggle
work occurred.

## Completed source and pooled relevance review

The 25 October Codex source review covers 73 sampled documents and all 2,062
pooled judgments over 20 questions, using cached originals and full passage
text. It retains 182 relevant judgments, rejects 1,874, and leaves six uncertain.
No additional local classifier output was used and no paid API was called.
This is development review with prior exposure to project results, not
independent human annotation. No retrieval experiment or final research scores
were run from these labels.

The offline HTML reparse staged a separate 1,159-document/29,595-passage
candidate, changing 643 retained documents and excluding 18. Both input orders
produce the same archive and every passage offset is exact. Active v3 and its
index remain unchanged. Source-review checks pass 623 tests with Ruff/Black
clean; the original 83 reviewer-delivery files retain their hashes. The final
local check log is `/private/tmp/lma-source-review-final-checks-20261025.log`.
Review and extraction phase wall times were not instrumented and are not
invented here. Findings and limits: `reports/track_a_source_review_20261025.md`.

## 26 October final Track A development delivery

All durations below are measured CPU phase wall times, not GPU-active time.
They reuse checksummed raw data and locally cached pinned models; index/pilot
phases exclude earlier downloads, installation, parsing and review. No paid API
request or Kaggle run occurred. Failed/intermediate attempts remain preserved.
Uninstrumented parsing/review and interrupted encoding time is not estimated.

| Phase | Actual phase wall seconds | Inputs/result |
|---|---:|---|
| v5 scoped dense index | 298.34 | 16,473 passages; 13,664 exact title+text inputs reused, 2,809 new inputs encoded |
| v5 migrated-positive pilot | 147.33 | 178 distinct positive judgments on 20 queries; not the final relevance pool |
| v5 full-pool pilot | 148.91 | 2,035 reviewed items / 195 relevant judgments |
| v5 fresh-process index reload | 12.73 | Two real query embeddings with March/September cutoffs |
| v6 intermediate index | 36.21 | 16,472 passages; 16,434 reused, 38 newly encoded |
| v6 intermediate pilot | 140.21 | Same 195 positive judgments; preserved as intermediate evidence |
| v6 fresh-process index reload | 12.91 | Two real queries; intermediate corpus identity retained |
| Final v7 index | 38.55 | 16,472 passages; 16,440 exact inputs reused, 32 newly encoded |
| Final v7 four-way plus reranker pilot | 135.28 | Same 20-query/195-positive file; final corpus identity |
| Final v7 fresh-process index reload | 12.94 | Two real query embeddings; every saved passage matches v7 and hits satisfy cutoffs |

The full v5 source review transferred 1,626 judgments and read all 409 new full
passages, yielding 195 relevant and 1,840 irrelevant. All 2,035 judgments transfer
to the final v7 pool by source identity/full normalized text with no novel
candidates. Earlier six uncertain v3 items were explicitly adjudicated against
standalone evidence; they were not converted by default or imported from the
rejected Qwen classifier. Prior v3 reviews/labels and all 83 original reviewer
files remain unchanged. Review is by Codex with prior results exposure and
creates no independent human receipt.

A fresh clone at `c0324cd` used a newly created Python 3.12 environment, installing
core/dev and optional PyMuPDF/trafilatura dependencies offline from local package
cache. All 630 tests and Ruff/Black pass. Its committed source replays extraction
from archived v3 and local raw originals into a fresh output. This checks a new
core/PDF environment and source checkout; retrieval/MLX weights and their heavy
runtimes are reused, and other machines/Kaggle are not certified. Final corpus
and archive identity and the exact setup/replay logs are recorded in
`reports/track_a_clean_reproduction_20261026.json`.

## 26 October additional official-source audit

The follow-up acquired the public SEBI listing, September bulletin and seven
annexures. Four annexures pass checksum, table-identity and file-version checks;
three are excluded (one known later file version and two invalid downloaded ZIP
copies). Five April–August total-FPI candidates have native USD values and
conservative publication dates. They include a broader investment universe and
remain outside the canonical series; no FX conversion or missing value is
invented. The primary ATF and August RBI web checks provide episode facts but
no new raw originals or corpus additions. Robots HTTP 403/418 stopped those
collectors. All 61 retained official PDFs pass the known-later-metadata screen;
this does not establish unchanged historical bytes.

At source `645b999`, all **637 tests** pass locally and in the existing clean
checkout/environment, with Ruff/Black clean. The seven added tests check table
identity, native currency, publication/version timing, arithmetic, formula-error
values, future observations and incomplete ZIP downloads. A fresh-source replay
of the SEBI audit reproduces the report hash exactly. No new environment,
heavy model run, paid API, Kaggle execution or independent human review occurred.
Acquisition and review wall times were not instrumented; none are estimated.
See `reports/track_a_followup_validation_20261026.json`.

## 27 October receipt-bound Track A retrieval comparison

After the user supplied reviewer Varun, date 27 October and explicit
independence/blinding declarations, both acceptance exporters passed the
73-document sample and 20-query/2,035-candidate records. These are recorded user
attestations; review procedure and exposure timing were not independently
observed. Original item decisions and evidence spans remain unchanged.

The non-smoke comparison reused the pinned v7 FAISS index and local pinned model
cache. CPU phase wall time was **153.84 seconds**, including the top-50 reranker;
this excludes earlier acquisition, model download/index build and human review.
All five reported metric rows reproduce the prior development comparison. No
paid API or Kaggle execution occurred. Report:
`reports/pilot_retriever_v7_attested_20261027.md`; receipt, file and log hashes:
`reports/track_a_reviewer_identity_20261027.json`. The earlier 637-test code
validation remains historical; this metadata/report update adds no code changes.

## 27 October whole-project audit

A separate connector probe used the actual pinned BGE-M3/FAISS index and
cross-encoder with the shared seven-condition pipeline. CPU phase wall time:
**23.70 seconds**. The generator was an explicit empty-edge fixture, so this
is not a new language-model run or semantic evaluation. No paid API or Kaggle
execution occurred. See `reports/whole_project_real_retrieval_probe_20261027.json`.

Two Track A fixes add four regression cases; the local suite now passes
**641 tests**, Ruff and Black. Current package installation was checked in a new
temporary environment with core dependencies only; default verifier alias
loading fails, while explicit-path rules work. No full new real-model v7 sweep,
all-laptop check or final result computation is claimed. The full audit and
hash-bound receipts are in `reports/whole_project_audit_20261027.md` and
`reports/whole_project_validation_20261027.json`.

## 27 October selected-configuration integration fixes

All five code findings are repaired under implementation commit `0ee617d`.
The actual conditions command ran two existing development candidates through
all seven conditions using pinned local Qwen3-8B, selected BGE-M3/FAISS and the
pinned top-50 cross-encoder for B1-R. All 14 graphs pass the expected-matrix,
artifact/log identity, source-safety and budget audit. Unchanged resume reused
all 14 artifacts without another model call.

| Condition | Graphs | Model calls | Prompt tokens | Completion tokens | Model-call seconds | Tool calls |
|---|---:|---:|---:|---:|---:|---:|
| A-NoLoop | 2 | 3 | 10,476 | 1,604 | 230.59 | 24 |
| A-NoVerify | 2 | 6 | 23,492 | 4,121 | 525.67 | 12 |
| B0 | 2 | 4 | 5,539 | 588 | 70.33 | 2 |
| B1 | 2 | 4 | 15,752 | 1,799 | 275.03 | 4 |
| B1-R | 2 | 4 | 15,678 | 2,144 | 314.67 | 4 |
| B2 | 2 | 2 | 9,943 | 1,433 | 208.60 | 4 |
| M | 2 | 6 | 12,152 | 1,898 | 284.70 | 24 |

Totals: **29 model calls**, **93,032 prompt tokens**, **13,587 completion tokens**, **1909.58 measured model-call wall seconds**, **74 tool calls**. Summed case wall time is **1992.20 seconds**, including retrieval/worker overhead within each case. These are not GPU-active hours or total setup/download time.

This is a development execution check, not a reviewed UER/recall or model-choice
result. Named episode flags remain unconfirmed. A separate explicitly synthetic
generator check confirms a declared canonical USD/INR numerical window across
all seven conditions. The suite passes 663 tests; the fresh core/dev checkout
passes 659 with four optional PDF checks skipped. Installed aliases now pass
isolated default loading. See `reports/integration_fixes_20261027.json`.

An optional Qwen3.5 candidate download was started during the broader preparation
and interrupted when work focused on these five fixes. Its partial ignored cache
is not a completed candidate installation or pilot result. No paid API or Kaggle
execution occurred.

## 28 October full current-v7 fresh-checkout reproduction

Task 4.3 used clean GitHub source `07f10f08870860388ec05207ecfd497f2ed8fad3`, a fresh core/dev
environment and the frozen current-v7 corpus/index. Cached pretrained weights,
native MLX/retrieval environments and verified unchanged PDF distribution files
were reused. The initial slow PDF download was deliberately stopped and the
old pruned cache missed; both attempts are retained separately from successful
installation and run timings. Setup, Ruff/Black and 663 tests pass.

The full planned `make run-dev` matrix produced 24 new graphs: six development
candidates × B0/B1/B2/M. Run phase wall time was **2666.02
seconds**. The full matrix audit and independent trace checks pass.
Unchanged resume reused all 24 without new model calls.

The baseline source screen retains four nonverbatim spans in three B1/B2
outputs. All M outputs pass source/date/span checks. These findings remain for
correction/support review and are not silently repaired or treated as accepted
evidence.

| Condition | Graphs | Model calls | Prompt tokens | Completion tokens | Model-call seconds | Tool calls |
|---|---:|---:|---:|---:|---:|---:|
| B0 | 6 | 12 | 16,680 | 1,986 | 366.85 | 6 |
| B1 | 6 | 12 | 46,830 | 5,369 | 870.77 | 12 |
| B2 | 6 | 6 | 29,546 | 4,136 | 585.00 | 12 |
| M | 6 | 15 | 34,741 | 5,129 | 744.12 | 68 |

Totals: **45 model calls**, **127,797
prompt tokens**, **16,620 completion tokens**,
**2566.74 measured model-call wall seconds**,
**98 tool calls** and **2657.26 summed case wall
seconds**. Invalid-JSON calls: **0**.
These are measured wall times, not GPU-active hours; run times exclude setup,
dependency downloads and review. No paid API or Kaggle execution occurred.

This completes local software reproduction, not independent edge support,
reviewed UER/recall, model selection or an all-machine check. Detailed source,
stage, input, graph and log hashes:
`reports/fresh_checkout_reproduction_20261028.json`.
