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
