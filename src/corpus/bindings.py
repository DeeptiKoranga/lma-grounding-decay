"""Keep downstream review tied to the corpus actually used by a run."""

import hashlib
import json
import re
from pathlib import Path


def recorded_corpus_sha256(runs: Path) -> str | None:
    hashes = set()
    for name in ("inputs.json", "phases.json", "prose_correction_receipt.json"):
        path = runs / name
        if not path.exists():
            continue
        value = json.loads(path.read_text())
        if name == "phases.json":
            value = value.get("shared_inputs", {})
        digest = value.get("corpus_sha256")
        if name == "prose_correction_receipt.json" and digest is None:
            continue  # Legacy fixture receipts did not record a corpus binding.
        if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
            raise ValueError(f"invalid run corpus binding in {path}")
        hashes.add(digest)
    if len(hashes) > 1:
        raise ValueError("run provenance records disagree on the corpus")
    return next(iter(hashes), None)


def require_run_corpus(runs: Path, corpus: Path) -> None:
    expected = recorded_corpus_sha256(runs)
    if expected is not None and hashlib.sha256(corpus.read_bytes()).hexdigest() != expected:
        raise ValueError(
            "supplied corpus differs from run provenance; select the archived corpus used by this run"
        )
