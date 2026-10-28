# C2 Model Pilot: Qwen3-8B vs Qwen3.5-9B

- Run time (UTC): 2026-10-28T16:59:40.590722+00:00
- GPU: Tesla T4
- Python: 3.13.15
- PyTorch: 2.11.0+cu128
- Transformers: 5.16.1
- Quantization: bitsandbytes NF4 4-bit; double quantization enabled
- Dataset: `pilot_cases_v2.jsonl`
- Dataset SHA-256: `910feb1905a3a9890c1ab0233f25c47e0cf26b94371b04740ff433a177221d69`
- Design: same frozen prompts, greedy decoding, max_new_tokens=160; models run sequentially.
- No fine-tuning was performed.

## Results

| Model | Task | N | Primary score | Strict JSON rate | Schema rate | Exact-match rate | Mean latency (s) | Errors |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen3-8B | extraction | 20 | 15.0% | 100.0% | 100.0% | 15.0% | 4.834 | 0 |
| Qwen/Qwen3-8B | strength | 20 | 70.0% | 100.0% | 100.0% | 70.0% | 1.634 | 0 |
| Qwen/Qwen3-8B | json_validity | 20 | 100.0% | 100.0% | 100.0% | 100.0% | 2.493 | 0 |
| Qwen/Qwen3-8B | tool_choice | 20 | 75.0% | 100.0% | 100.0% | 75.0% | 0.917 | 0 |
| Qwen/Qwen3-8B | unsupported_edges | 20 | 100.0% | 100.0% | 100.0% | 100.0% | 1.915 | 0 |
| Qwen/Qwen3.5-9B | extraction | 20 | 20.0% | 100.0% | 100.0% | 20.0% | 6.167 | 0 |
| Qwen/Qwen3.5-9B | strength | 20 | 65.0% | 100.0% | 100.0% | 65.0% | 2.774 | 0 |
| Qwen/Qwen3.5-9B | json_validity | 20 | 100.0% | 100.0% | 100.0% | 100.0% | 3.001 | 0 |
| Qwen/Qwen3.5-9B | tool_choice | 20 | 70.0% | 100.0% | 100.0% | 70.0% | 1.992 | 0 |
| Qwen/Qwen3.5-9B | unsupported_edges | 20 | 100.0% | 100.0% | 100.0% | 100.0% | 2.744 | 0 |

## Interpretation and limitations

- Scores are computed from the recorded raw model outputs using the fixed rules in the notebook.
- The JSON-validity task's primary score is strict schema validity; exact-value accuracy is reported separately.
- The dataset is synthetic and small (20 cases per task); results are exploratory, not a general capability claim.
- Extraction and strength scoring use exact gold labels and may penalize semantically equivalent wording.
- All unsupported-edge cases require rejection; this estimates rejection behavior on these cases, not general calibration.
- Latency depends on Kaggle GPU state, caching, and runtime load.
- A model comparison is incomplete if either model failed to run all 100 cases.

## Artifacts

- Frozen cases: `pilot_cases_v2.jsonl`
- Raw outputs and per-case scores: `pilot_results.jsonl`
- Machine-readable summary: `pilot_summary.json`
