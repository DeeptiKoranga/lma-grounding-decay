# Integration fixes — 27 October 2026

All five engineering findings from the preserved
[original audit](whole_project_audit_20261027.md) are repaired. This record covers
implementation and execution checks; it does not accept research outcomes.

| Finding | Result |
|---|---|
| F1: selected retrieval disconnected | The conditions command defaults to pinned BGE-M3/FAISS. All retrieved conditions share one configured first stage; B1-R reranks its top 50 eligible candidates. The Makefile supplies the separate offline retrieval environment. BM25 remains an explicit option. |
| F2: unproven anchor flags | Input confirmation flags are discarded. The shared preflight calls `get_series` within the 12-call budget. Only a declared window with visible exact endpoints, matching direction and configured change thresholds can confirm a numerical move. Source URLs, units and availability dates are retained. Unmapped, missing or delayed evidence stays unconfirmed. |
| F3: stale resume | Inputs bind all ten runtime packages and YAML resources, exact local generator files, Python/dependency identities, retrieval configuration/index, corpus, aliases, queries, series and model settings. Output and successful log checksums are checked before reuse. Legacy/unbound or changed runs require a new directory. |
| F4: incomplete runs accepted | The auditor checks the recorded condition/query matrix and artifact/log identities. Empty, missing, unexpected, malformed or modified results fail and the command exits nonzero. Explicit partial inspection cannot certify completion. Retry logs are listed separately and do not inflate completed-run compute. |
| F5: installed aliases missing | The wheel includes the tracked alias YAML as package data; isolated default loading and a real rule check pass outside the repository. The CLI also passes its configured alias table into the pipeline verifier. |

## Validation

The full working-checkout suite passes **663 tests**, including **22 new
regression cases**. Ruff and Black pass. A clean source checkout also passes
663 tests with the existing optional runtime. Installing the locked core/dev
dependencies in its own fresh environment gives 659 passes and four optional
PDF checks skipped. A separate wheel installation
with core dependencies loads all 68 runtime modules, covers all 46 ontology
variables and loads alias bytes identical to the repository table.

The actual conditions command is exercised on two existing development
candidates with the real local Qwen3-8B generator, selected pinned BGE-M3/FAISS
index and pinned top-50 cross-encoder. All **14 graphs** completed and passed the full recorded-matrix audit, with
**zero audit failures**. Unchanged resume returned **14 cached results** and
made no new model calls. The machine-readable record contains graph/log hashes
and measured compute. Its
in-progress audit correctly rejected missing cases. An empty-directory audit
exits 1 and lists both undeclared expectations and absent results.

A separate connector check uses the canonical, original-vintage USD/INR
observations for 18–19 May. All seven conditions confirm that declared numerical
window, using an explicit empty fixture generator. This check establishes the
series connection, not explanation quality. Regression cases separately cover
late observations, empty stores, opposite moves, thresholds and missing endpoints.

Exact evidence and limits: [integration_fixes_20261027.json](integration_fixes_20261027.json).
Run payloads, model weights, vectors and corpus text remain outside git.

## Reproduction and remaining scope

Use the updated [reproduction instructions](../docs/reproduction.md). The
four-condition and seven-condition Makefile targets have different default
output directories. A changed source/runtime/input fingerprint deliberately
refuses resume; historical v1 outputs retain their original provenance.

The two live queries retain their development status and unconfirmed episode
flags. A diagnostic series lookup cannot establish an undeclared event, and a
series move cannot support a causal edge. The original Track A review records,
accepted receipts, corpus/archive/index and both series stores are unchanged.
The delivery integrity replay verifies all 16,472 offsets and 2,035 retrieval
judgments; its historical template date/blank-packet status is distinguished
from the current accepted-review records in the JSON wrapper.

Separate model-selection, episode/query/reference review, baseline correction,
blinded support judgments, agreement, public-dataset checks and final result
figures remain study prerequisites. Final-report prose and a pull request are
outside these five fixes.
