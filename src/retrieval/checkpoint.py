"""Resumable embeddings keyed by model/preprocessing identity and input-text hash."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from schema import Passage

from .dense import Embedder, _embedding_identity, normalise_vectors


def embed_checkpointed(
    passages: list[Passage],
    *,
    embedder: Embedder,
    path: Path,
    checkpoint_every: int = 100,
) -> list[tuple[float, ...]]:
    """Reuse unchanged passage inputs even when the corpus expands or reorders.

    A completed block is committed atomically. A crash loses at most one block;
    a model/revision/token-length change requires a separate checkpoint path.
    """
    if checkpoint_every < 1:
        raise ValueError("checkpoint_every must be positive")
    if len({p.passage_id for p in passages}) != len(passages):
        raise ValueError("passage ids must be unique")
    identity = _embedding_identity(embedder)
    entries = {}
    dimension = None
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("version") != 2 or raw.get("embedding_id") != identity:
            raise ValueError("embedding checkpoint model/revision/preprocessing mismatch")
        for entry in raw["entries"]:
            pid = entry["passage_id"]
            if pid in entries:
                raise ValueError("duplicate passage id in embedding checkpoint")
            rows = normalise_vectors([entry["vector"]], count=1, dimension=dimension)
            dimension = len(rows[0])
            entries[pid] = {**entry, "vector": rows[0]}
    inputs = {p.passage_id: p.title + "\n" + p.text for p in passages}
    hashes = {pid: hashlib.sha256(text.encode()).hexdigest() for pid, text in inputs.items()}
    by_text = {entry["text_sha256"]: entry["vector"] for entry in entries.values()}
    remapped = False
    for pid, digest in hashes.items():
        if (pid not in entries or entries[pid]["text_sha256"] != digest) and digest in by_text:
            # Removing navigation can renumber unchanged paragraphs. The full
            # title+text input and model identity, rather than its ordinal, define
            # the embedding. Current passages still supply dates and provenance.
            entries[pid] = {
                "passage_id": pid,
                "text_sha256": digest,
                "vector": by_text[digest],
            }
            remapped = True
    pending = [
        pid for pid in inputs if pid not in entries or entries[pid]["text_sha256"] != hashes[pid]
    ]

    def save():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(
            json.dumps(
                {
                    "version": 2,
                    "embedding_id": identity,
                    "entries": [entries[pid] for pid in sorted(entries)],
                },
                allow_nan=False,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)

    for start in range(0, len(pending), checkpoint_every):
        ids = pending[start : start + checkpoint_every]
        vectors = normalise_vectors(
            embedder.encode([inputs[pid] for pid in ids]),
            count=len(ids),
            dimension=dimension,
        )
        if vectors:
            dimension = len(vectors[0])
        for pid, vector in zip(ids, vectors, strict=True):
            entries[pid] = {
                "passage_id": pid,
                "text_sha256": hashes[pid],
                "vector": vector,
            }
        save()
    if remapped or not path.exists():
        save()
    return [entries[p.passage_id]["vector"] for p in passages]
