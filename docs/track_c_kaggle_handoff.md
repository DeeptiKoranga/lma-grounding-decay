# Track C Kaggle handoff — 30 October 2026

The dense index is deliberately outside Git: `.gitignore` excludes indexes and
corpus payloads. Download the separate frozen-data archive, not a fresh scrape
or a rebuilt index made with different weights.

## Frozen inputs

Archive: `data/processed/kaggle_data_v7_20261030.zip`.

Archive SHA-256:
`248cd59d731d8b056d99a5b0ae1819f9df8aba022eb92d312799e3f79c3f0da4`.

Required index: `data/interim/corpus_v7_index_20261026/bge_m3_vectors.json`.

Index size: **389,082,352 bytes**. Index SHA-256:
`5345b8a3384f759f73a7fee6c58ef544a4ad6ad47f04262fc81efafb5e038d2c`.

The archive contains the exact index, its matching v7 passages, aliases and six
series CSVs. File-level hashes and sizes are in
`reports/kaggle_data_manifest_20261030.json` and inside the archive as
`bundle_manifest.json`. It contains no model weights, credentials or run logs.
Existing corpus redistribution and source-scope notes still apply.

On Windows, the direct index checksum command is:

```powershell
(Get-FileHash data/interim/corpus_v7_index_20261026/bge_m3_vectors.json -Algorithm SHA256).Hash
```

## Kaggle execution

1. Attach the source snapshot and frozen-data archive as Kaggle datasets. Kaggle
   should unpack them so `pyproject.toml` and `bundle_manifest.json` are visible
   under `/kaggle/input`. The source snapshot should contain one project only.
2. Enable the two T4 GPUs and Internet, then open `notebooks/kaggle_run.ipynb`.
3. Run its cells. It copies the project/data into `/kaggle/working`, installs the
   recorded setup, fetches pinned retrieval weights, verifies every asset hash,
   starts vLLM, waits for readiness, and runs the declared condition matrix.
4. Inspect `audit.json` and `compute-*.json` under
   `/kaggle/working/track_c_run`, then download that directory. Failure attempts
   retain their server log and allocation receipt.

The vLLM repository/revision comes from `configs/model_selection.json` or the
explicit `LMA_VLLM_MODEL_ID` / `LMA_VLLM_MODEL_REVISION` overrides. A revision
must be a 40-character immutable commit. **Do not serve MLX-format weights in
vLLM.** The local and Kaggle formats must be recorded separately even when they
represent the same selected base-model family.

Both compatible request paths disable Qwen thinking for the measured protocol.
The prose baseline is still allowed to return prose; the runner does not impose
a global JSON-only response format on every condition.

## Windows and resume behavior

The persistent worker uses a background reader thread and a queue, not a socket
selector on a subprocess pipe. Use the updated checkout; older selector-based
copies cause WinError 10038. The tests exercise two sequential searches, timeout
cleanup and restarting a failed child.

MLX itself is a macOS inference backend. A Windows machine uses the same tools,
controller, retrieval and evaluation code with a local llama.cpp server or a
vLLM endpoint; it does not need Apple libraries for those components. In
PowerShell, use `.venv\Scripts\python.exe` for `--retrieval-python` and
`--reranker-python`, and set `$env:PYTHONPATH="src"`. Select
`--backend llama.cpp --base-url http://127.0.0.1:8000/v1` (or `--backend vllm`)
with the explicit server model and immutable revision. The runner now explains
this directly if MLX is selected on Windows/Linux. No automatic API fallback or
unreported model switch occurs.

New JSON artifacts use identical UTF-8/LF bytes on Windows and Unix. Artifact
receipt addresses use `/`; old Windows `\` keys are accepted and normalized
while duplicate addresses and changed bytes are still rejected. Source
identities normalize CRLF/LF differences and relative path separators.

**A checksum rejection after changing source, settings, model, data or runtime
is intentional.** Choose a new output directory after such a change. Resume is
for an unchanged run and must never silently reuse stale graphs. Copies of
historical runs remain preserved.

`reports/kaggle_compute_evidence_20261030.json` reconciles the saved C1/C2
notebook timestamps. Historical active/billed GPU hours were not measured and
remain unknown. New runs log the measured visible allocation interval and device
count; this is explicitly distinct from GPU-active time or the account's total
quota usage.

## Completed live verification

The private [30 October kernel](https://www.kaggle.com/code/varunpatil50/lma-track-c-verification-20261030)
completed from source `245e0fd` on two Tesla T4 GPUs: seven conditions × two
development candidates, 14 graphs, full checksum/matrix audit and 14 cached
results on unchanged resume. The independent local re-audit matches the remote
audit byte for byte. Measured setup-plus-run allocation was **1.211103 GPU-hours**
(2,179.985 wall seconds × two GPUs), below the authorized two-hour limit.
Provider startup/teardown outside the entrypoint and GPU-active time were not
measured. See `reports/kaggle_live_verification_20261030.json` and the complete
compute/audit/resume receipts in `reports/kaggle_verification_evidence_20261030/`.

Private attached datasets are `varunpatil50/lma-track-c-source-20261030` and
`varunpatil50/lma-track-c-frozen-v7-20261030`. Visibility stays private. This
engineering smoke uses the historically verified Qwen3-8B GPTQ revision recorded
in its receipts. It does not substitute for the local project-schema C2 pilot,
change its selection rule, or establish human-reviewed scientific results.
The B1-R baseline's nonverbatim quotations are retained and flagged in the audit;
no model output is silently repaired to improve an evaluation score.
