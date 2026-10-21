"""A7: cosine dense retrieval with optional BGE-M3 and exact FAISS search.

The default exact scorer uses the standard library. Heavy imports and model
downloads happen only when the explicitly selected backend is first used.
FAISS indexes contain only date/source/mention-eligible candidates, so a future
document cannot consume a result slot or influence an approximate index.
"""

from __future__ import annotations

import json
import math
from collections import OrderedDict
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from schema import Passage

from .bm25 import Aliases, Hit
from .filters import eligible, validate_query


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> Sequence[Sequence[float]]: ...


class BGEEmbedder:
    """Lazy sentence-transformers adapter for BAAI/bge-m3; no query instruction.

    A model directory may replace the model id for a fully offline run. Pin a
    Hugging Face revision when producing experimental results and record it in
    the pilot report. Model usage follows https://huggingface.co/BAAI/bge-m3.
    """

    def __init__(
        self,
        model: str = "BAAI/bge-m3",
        *,
        device: str = "cpu",
        batch_size: int = 8,
        max_length: int = 1024,
        revision: str | None = None,
        local_files_only: bool = False,
    ):
        if batch_size < 1 or not 1 <= max_length <= 8192:
            raise ValueError("batch_size must be positive and max_length within 1..8192")
        self.model_name, self.device = model, device
        self.batch_size, self.revision = batch_size, revision
        self.max_length = max_length
        self.local_files_only = local_files_only
        self._model = None
        self._query_cache: OrderedDict[str, tuple[float, ...]] = OrderedDict()

    def encode(self, texts: list[str]):
        if not texts:
            return []
        if len(texts) == 1 and texts[0] in self._query_cache:
            self._query_cache.move_to_end(texts[0])
            return [self._query_cache[texts[0]]]
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError("dense BGE retrieval requires sentence-transformers") from exc
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
                revision=self.revision,
                local_files_only=self.local_files_only,
                trust_remote_code=False,
            )
            self._model.max_seq_length = self.max_length
        rows = self._model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        if len(texts) == 1:
            vector = normalise_vectors(rows, count=1)[0]
            self._query_cache[texts[0]] = vector
            if len(self._query_cache) > 128:
                self._query_cache.popitem(last=False)
            return [vector]
        return rows

    def unload(self) -> None:
        """Release model memory while keeping at most 128 reusable query vectors."""
        self._model = None
        release_accelerator_memory()


def normalise_vectors(rows, *, count: int, dimension: int | None = None) -> list[tuple[float, ...]]:
    if len(rows) != count:
        raise ValueError("embedding count does not match input count")
    result = []
    for row in rows:
        values = tuple(float(value) for value in row)
        if not values or (dimension is not None and len(values) != dimension):
            raise ValueError("embedding dimension mismatch or empty vector")
        if not all(math.isfinite(value) for value in values):
            raise ValueError("embeddings must contain finite numbers")
        # hypot avoids overflow for otherwise finite vectors.
        norm = math.hypot(*values)
        if norm == 0 or not math.isfinite(norm):
            raise ValueError("embeddings must have a finite, nonzero norm")
        dimension = len(values)
        result.append(tuple(value / norm for value in values))
    return result


class DenseRetriever:
    def __init__(
        self,
        passages: list[Passage],
        *,
        embedder: Embedder,
        aliases: Aliases | None = None,
        vectors=None,
        backend: str = "exact",
        embedding_id: str | None = None,
    ):
        if backend not in {"exact", "faiss"}:
            raise ValueError("dense backend must be exact or faiss")
        if len({p.passage_id for p in passages}) != len(passages):
            raise ValueError("passage ids must be unique")
        self.passages = tuple(passages)
        self.embedder, self.aliases, self.backend = embedder, aliases or Aliases({}), backend
        self.embedding_id = embedding_id or _embedding_identity(embedder)
        if vectors is None:
            vectors = (
                embedder.encode([p.title + "\n" + p.text for p in passages]) if passages else []
            )
        self.vectors = normalise_vectors(vectors, count=len(passages))
        self.dimension = len(self.vectors[0]) if self.vectors else None

    def search(self, query, *, as_of, k=10, source_kind="any", must_mention=None) -> list[Hit]:
        args = validate_query(
            query,
            as_of=as_of,
            k=k,
            source_kind=source_kind,
            must_mention=must_mention,
            aliases=self.aliases,
        )
        indices = [i for i, p in enumerate(self.passages) if eligible(p, args, self.aliases)]
        if not indices:
            return []
        vector = normalise_vectors(
            self.embedder.encode([args.query]), count=1, dimension=self.dimension
        )[0]
        if self.backend == "faiss":
            scores = self._faiss_scores(indices, vector)
        else:
            scores = {
                i: math.fsum(a * b for a, b in zip(vector, self.vectors[i], strict=True))
                for i in indices
            }
        ranked = sorted(indices, key=lambda i: (-scores[i], self.passages[i].passage_id))
        return [Hit(self.passages[i], scores[i]) for i in ranked[: args.k]]

    def _faiss_scores(self, indices, vector):
        try:
            import faiss
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("FAISS retrieval requires faiss-cpu and numpy") from exc
        matrix = np.asarray([self.vectors[i] for i in indices], dtype="float32")
        index = faiss.IndexFlatIP(self.dimension)
        index.add(matrix)
        scores, positions = index.search(np.asarray([vector], dtype="float32"), len(indices))
        # Read all eligible scores to make tied results stable across backends.
        if any(int(j) < 0 or int(j) >= len(indices) for j in positions[0]):
            raise ValueError("FAISS returned invalid indices")
        result = {
            indices[int(j)]: float(score) for j, score in zip(positions[0], scores[0], strict=True)
        }
        if set(result) != set(indices) or not all(math.isfinite(s) for s in result.values()):
            raise ValueError("FAISS returned invalid indices or scores")
        return result

    def save(self, path: str | Path) -> None:
        """Safe portable vectors + exact corpus snapshot; no pickle/deserialised code."""
        Path(path).write_text(
            json.dumps(
                {
                    "version": 2,
                    "embedding_id": self.embedding_id,
                    "passages": [p.model_dump(mode="json") for p in self.passages],
                    "vectors": self.vectors,
                },
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        embedder: Embedder,
        aliases=None,
        backend="exact",
        embedding_id: str | None = None,
    ):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if raw.get("version") != 2:
            raise ValueError("unsupported dense index version")
        expected_id = embedding_id or _embedding_identity(embedder)
        if raw.get("embedding_id") != expected_id:
            raise ValueError("query embedder does not match saved embedding model/revision")
        return cls(
            [Passage.model_validate(p) for p in raw["passages"]],
            embedder=embedder,
            aliases=aliases,
            vectors=raw["vectors"],
            backend=backend,
            embedding_id=expected_id,
        )


def _embedding_identity(embedder: Embedder) -> str:
    """Custom adapters can provide model_id or callers can pass embedding_id.

    Explicit revision and id are important for real pilot reproducibility;
    adapters without model metadata use their Python class for offline tests.
    """
    kind = f"{type(embedder).__module__}.{type(embedder).__qualname__}"
    return json.dumps(
        [
            kind,
            getattr(embedder, "model_id", getattr(embedder, "model_name", None)),
            getattr(embedder, "revision", None),
            getattr(embedder, "max_length", None),
            "title-newline-paragraph;unit-cosine;v2",
        ],
        separators=(",", ":"),
    )


def release_accelerator_memory() -> None:
    """Avoid importing Torch solely for cleanup of a never-loaded adapter."""
    import gc
    import sys

    gc.collect()
    torch = sys.modules.get("torch")
    if torch is not None:
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
