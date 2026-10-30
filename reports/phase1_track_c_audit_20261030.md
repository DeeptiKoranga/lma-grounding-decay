> Historical audit at `b76f6b1`. Completion fixes and new verification are being recorded in `phase1_track_c_closeout_20261030.md`; the findings below retain their original scope.

# Phase 1 Track C audit — 30 October 2026

Audited branch: `varun`, commit `b76f6b1` (includes `c/agent-controller` at
`bb66877`). Scope: the eleven C1–C11 requirements in `PLAN_MIDSUB.md:96`.

**Verdict: Phase 1 Track C is not entirely complete.** Its main components are
implemented, but two reproducible integration defects and three evaluation or
recording gaps prevent a complete sign-off. Passing tests alone do not establish
completion of these requirements.

## Task-by-task assessment

“Implemented” below means the required component exists, was traced through its
callers, and is exercised by the current checks; it is not a proof of every
possible runtime path.

| Task | Assessment | Evidence and remaining work |
|---|---|---|
| C1 — unified generation | Partial | MLX, compatible vLLM/llama.cpp and native Anthropic adapters exist. Saved MLX execution and a successful Kaggle vLLM smoke exist. The actual Claude condition pipeline fails when logging its first completion: F1. A paid live Claude call is not necessary to reproduce or fix this defect. |
| C2 — two-model, five-task pilot | Partial | Both models completed 100 cases, with raw outputs and a hash-matching case file. The strength task uses a different label system, extraction does not test the project's graph schema, and D-01 remains unresolved: F3. |
| C3 — six validated tools | Partial | All six tools have argument/result schemas, trusted-source checks, pinned cutoffs and a maximum 12-call budget. However, a strength-only graph relabel bypasses the verifier's approved strength: F2. |
| C4 — bounded controller | Implemented | Open-edge state, search counts and remaining budget are maintained; shallow edges have priority; the three stop conditions and failed-call bounds are exercised by fixture integration tests. The executed controller uses deterministic priority. |
| C5 — seven conditions, one pipeline | Implemented | B0, B1, B1-R, B2, A-NoVerify, A-NoLoop and M use `conditions.config.SETTINGS` and the same `Pipeline.run`. The YAML mirrors those settings. Fixture tests exercise all seven conditions. The Claude-specific defect is recorded under C1/C6. |
| C6 — run logging | Partial | Full prompts, completions, token counts, latency, typed tool calls/results, states and stop/error records are implemented. Claude completion records are rejected by the shared schema: F1. |
| C7 — hop-sliced metrics | Implemented | UER, strength inflation, reference-edge recall, provenance accuracy and strict path validity are computed for hop 1, 2 and 3+, plus overall. Query-level aggregation, null denominators and reference-recall guards are exercised. Human-scored research results are a later-phase obligation. |
| C8 — paired bootstrap | Implemented | Seeded query-paired bootstrap returns 95% intervals and excludes missing-denominator pairs explicitly. The two declared contrasts are B1 deep minus shallow, and M minus B1 overall, for the permitted metrics. |
| C9 — frozen states and tool faults | Complete for the Phase 1 fixture deliverable | There are 40 uniquely identified scripted states with expected tool names and 20 scripted tool faults. All 20 faults passed a fresh execution. The fixtures are explicitly synthetic; their five variants of eight state scenarios are not independent human gold. The plan places the tool-calling metrics run in Phase 2.7. |
| C10 — safety evaluation | Partial | There are 25 adversarial prompts, structural source/date/span checks and screening functions for all four required risks. The recorded evaluation summarizes only advice and own-forecast flags, leaves human adjudication pending, and does not provide completed outcome counts for the other two risks: F4. |
| C11 — Kaggle notebook, setup and GPU-hour log | Partial | The separate live-verification notebook demonstrates successful vLLM generation. `kaggle_run.ipynb` is an unexecuted five-cell handoff, and the compute log still says no Kaggle execution occurred despite the newer Kaggle pilot and smoke: F5. A full development sweep belongs to later phases. |

## F1 — Claude generation cannot pass through the run logger

**Tasks affected: C1 and C6. Reproduced offline.**

- `src/llm/generate.py:282` constructs a completion with `backend="claude"`.
- `src/schema/runlog.py:38` accepts only `mlx`, `llama.cpp`, `vllm` and `api`.
- `Pipeline.run` passes completed generations to `RunLogger.model`, which
  validates against that schema.

An offline B0 pipeline run using the real `AnthropicGenerator` with a mocked
Messages API response fails with a Pydantic `literal_error` at
`model_call.backend`. Its input is `claude`. No API key or real network call was
used. The current tests verify the Anthropic adapter in isolation but miss this
adapter-to-pipeline integration.

Required closeout: reconcile the backend identifiers in the generator and run
schema, regenerate the exported schema if changed, and exercise a logged
condition run with the Anthropic adapter using a mocked response.

## F2 — an asserted edge can be strengthened without fresh verification

**Task affected: C3. Reproduced using the real tool runtime and verifier.**

`src/tools/runtime.py:313` checks the approved verification result only when
`args.provenance` explicitly equals `source_asserted`. A request containing only
`strength` goes through the alternate branch at line 325, and line 343 applies
the requested strength to an already asserted edge.

Reproduction:

1. Verify an inferred fixture edge. The semantic fixture returns supported,
   direction up, strength conditional.
2. Apply that approved edge as `source_asserted`, strength conditional.
3. Call `update_graph(op="relabel_edge", edge_id="e", strength="direct")`,
   omitting the provenance argument.

Observed outcome: the update succeeds; the final edge is `source_asserted`,
strength `direct`, and still labelled `verified_by="rules+llm"`. Its stored
verification approval remains conditional, and there are zero additional
verifier calls. The normal deterministic controller does not currently issue
this strength-only request, but the public validated tool interface accepts it.

Required closeout: enforce the verification approval for changes to any
already asserted edge, including requests that omit provenance, and cover this
case with a regression check.

## F3 — the recorded model pilot does not resolve the project model choice

**Task affected: C2. Pilot artifacts were verified, not dismissed as missing.**

The case file has 100 unique cases, 20 per task. Its SHA-256 matches the summary,
and all 200 model/case outputs are unique. Recorded exact-match flags reproduce
from the raw JSON outputs and corresponding gold values.

However:

- The “strength” labels are `direct_support`, `partial_support`, `contradicted`
  and `insufficient_evidence`. The project's actual strength vocabulary is
  `direct`, `conditional` and `correlational` (`src/schema/enums.py`). This pilot
  therefore does not measure the required causal-strength classification.
- Extraction uses subject/relation/object/time fields. It does not establish
  that a model can generate the closed-ontology graph candidates accepted by
  `extract.candidates.Extraction`.
- `docs/decisions.md:37` still marks D-01 open, and its resolution is unresolved.
- The execution used Kaggle NF4 quantization, whereas the plan names a laptop
  MLX pilot. Model revisions are not recorded as immutable commits in the pilot
  summary. The chosen runtime and any deviation need an explicit disposition.

Required closeout: validate the relevant tasks against the project labels and
schema, pin the model/runtime identity, then record the model decision and its
evidence. Existing synthetic pilot numbers should retain their original scope.
The 15%/20% generic extraction exact-match rates alone do not establish the
quality of the project's extractor.

## F4 — safety screening is not a completed four-risk evaluation

**Task affected: C10.**

`src/eval/safety.py` contains the four risk flags plus a mutation flag and a
coverage-aware summarizer. However,
`scripts/run_capability_diagnostics.py:86` still summarizes only advice and
own-forecast flags. `reports/capability_diagnostics.json` likewise reports only
those two counts and labels human adjudication pending.

There is no completed recorded outcome table covering advice leakage,
own-forecast leakage, post-date evidence use and asserted-label-without-span
for all 25 responses. Regex matches are explicitly screening flags, not reviewed
leakage judgments; flags can match a refusal or miss a paraphrase.

Required closeout: summarize and adjudicate all four risks across the 25 actual
responses, preserving response and model provenance. Existing saved responses
can be reused where appropriate; a model rerun is needed only if the desired
configuration or missing evidence requires one.

## F5 — Kaggle execution and compute records are inconsistent

**Task affected: C11.**

- `notebooks/c1_live_verification.ipynb` has 11 executed code cells and a saved
  successful project-generator response. It also preserves an earlier failed
  setup attempt; later successful output does establish the limited smoke.
- `notebooks/c2_model_pilot.ipynb` has 14 executed code cells and retained pilot
  outputs.
- `notebooks/kaggle_run.ipynb` has five code cells, none executed. Its handoff
  also does not wait for the vLLM server to become ready before the conditions
  command is run; it assumes project/runtime/model/index assets are supplied.
- `reports/compute_log.md:5` still says no Kaggle job was executed and records no
  GPU-hour accounting for the newer jobs.
- The successful vLLM smoke sets `enable_thinking=False` and JSON response
  format explicitly. The conditions command does not expose or forward those
  settings. Its behavior should be verified with the intended server setup.

Required closeout: reconcile the handoff and actual successful setup, record
Kaggle job/device usage with its measured scope, and update the compute log.
Unmeasured GPU-active time must remain unmeasured. Phase 1 does not require
claiming a completed full development sweep.

## Verification and scope limits

- Current full suite: **701 passed in 3.68 seconds**, no skips reported.
- Ruff: all checks pass, including the tracked notebooks.
- Black: 154 Python files unchanged. Its optional Jupyter support is absent,
  so this command does not certify notebook formatting.
- Fresh scripted fault execution: **20/20 passed**.
- Two new offline probes reproduce F1 and F2; they are separate from the
  passing existing test suite.
- A whole-repository syntax inventory parsed 69 source modules, 34 scripts and
  51 test files. Detailed inspection followed Track C's modules, shared
  schemas, extraction/verifier/retrieval/series interfaces, relevant tests,
  notebooks, pilot artifacts and execution reports.
- No source code was changed for this audit. No paid API call or new GPU
  inference was made. Saved notebook execution is evidence of the recorded
  runs, not a fresh reproduction of their heavy runtime.

The audit's raw probe outcomes are in
`phase1_track_c_audit_20261030_probes.json`. The original isolated probe logs are
at `/private/tmp/lma-phase1-track-c-01gepiup/`.

Full dev sweeps, blind support/reference annotation, headline UER figures,
merging current Track B work from main, and release tagging belong to later
phases or integration closeout. They are not used as additional reasons to
reject Phase 1 completion here.
