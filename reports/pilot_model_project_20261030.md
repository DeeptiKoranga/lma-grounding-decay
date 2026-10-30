# C2 project-specific model pilot — 30 October 2026

Both pinned MLX 4-bit models completed the same 100 frozen project-schema cases. These are synthetic development diagnostics, separate from research gold.

Selection rule, recorded before the included runs: Highest unweighted mean accuracy across the five project tasks; within 0.03 choose the model with lower mean generation latency. Report schema validity separately. Selection is for this development protocol, not a claim of general capability or accepted hypothesis results.

| Model | Extraction | Strength | JSON validity | Tool choice | Unsupported edges | Mean | Mean latency (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| mlx-community/Qwen3-8B-4bit | 5.0% | 95.0% | 100.0% | 10.0% | 95.0% | 61.0% | 20.356 |
| mlx-community/Qwen3.5-9B-4bit | 65.0% | 75.0% | 100.0% | 5.0% | 60.0% | 61.0% | 26.616 |

**D-01 selection: `mlx-community/Qwen3-8B-4bit`, revision `545dc4251c05440727734bcd94334791f6ab0192`.**

The extraction task requires closed-ontology variables, correct direction/strength and a verbatim quote from the supplied synthetic passage. Strength uses direct/conditional/correlational. JSON validity uses the actual Extraction schema; tool choice must parse under the actual tool schema and preserve the cutoff. Unsupported-edge cases distinguish absent relations from opposite directions.

Each task has 20 cases. Schema validity is recorded separately in the JSON report. Weak extraction or tool-choice scores remain limitations of the selected model; the deterministic controller and verification guards are still required. This pilot does not prove model accuracy on the corpus or an accepted research result.

Raw outputs, token counts, measured latency, model-file hashes and source/runtime identities are retained. The local MLX hardware was used as planned. The original Kaggle NF4 generic pilot is preserved in `reports/pilot_model.md`; its labels and scores are not relabelled as this pilot. An excluded preliminary prompt-ambiguity attempt is documented separately.

Reproduce: run `scripts/run_model_pilot.py --model qwen3-8b`, then `--model qwen3.5-9b` in the pinned local environment with `PYTHONPATH=src`, followed by `scripts/finalize_model_pilot.py`. Resume requires the identical recorded sources, runtime, cases and model bytes. Use a new output directory after a change.

The post-run field analysis preserves the frozen selection rule. For Qwen3-8B,
17/20 extraction responses used an incorrect passage ID, 10/20 supplied a
nonverbatim or missing quotation (some emitted character ranges such as `0-89`),
and 7/20 had incorrect strength; categories overlap. Qwen3.5-9B retained the
correct passage IDs and quotations but had 6/20 strength errors. Both had one
direction error. See `project_model_pilot_error_analysis_20261030.json`.
The selected 8B model is faster under the pre-recorded tie rule; it is not the
best model on every task. These observed extraction weaknesses are why a
verified source assertion cannot bypass the independent rule/semantic checks.
