# C1 — Live generation backend verification

Date: 30 October 2026

## Scope
Verify the unified generation interface against the Kaggle vLLM backend.
Claude live API verification is not part of this acceptance check.

## Kaggle vLLM evidence
- Notebook: `notebooks/c1_live_verification.ipynb`
- Executed cells: 11/11
- Cells with saved outputs: 11/11
- Model: `JunHowie/Qwen3-8B-GPTQ-Int4`
- Runtime: vLLM on Kaggle, with two GPUs detected
- Server: OpenAI-compatible endpoint on port 8000
- Live API request: HTTP 200
- JSON generation: passed
- Project `ChatCompletionsGenerator` integration: passed
- Generator contract tests in notebook: 17/17 passed

## Windows checkout verification
Command: `python -m pytest tests/unit/test_generator_contract.py -v`
Result: 17 passed in 0.08 seconds.

## Existing backend implementation
- `MLXGenerator`
- `ChatCompletionsGenerator` (vLLM / llama.cpp)
- `AnthropicGenerator`

## Acceptance limits
This verifies the generator interface and live vLLM integration. It does not
claim a complete end-to-end agent episode acceptance or a live Claude API call.
MLX evidence is based on the previously recorded local Mac execution.

## Evidence
The executed Kaggle notebook and its saved cell outputs are retained at
`notebooks/c1_live_verification.ipynb`.
