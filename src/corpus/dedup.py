"""Deterministic MinHash candidates, confirmed by exact title-and-lede Jaccard.

Only retained documents become representatives, so a chain of near matches does
not silently discard documents that differ from the retained copy. Input order
does not affect the result. No optional indexing dependency is needed.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC
from zoneinfo import ZoneInfo

from .documents import Document

NUM_PERM = 128
ROWS_PER_BAND = 4
PRIME = (1 << 61) - 1


def _hash(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:8]) % PRIME


PERMUTATIONS = tuple(
    (_hash(f"lma-minhash-a-{index}") or 1, _hash(f"lma-minhash-b-{index}"))
    for index in range(NUM_PERM)
)


def title_lede_shingles(document: Document) -> frozenset[str]:
    """Case-folded word trigrams of the title plus the first paragraph."""
    lede = document.text.split("\n\n", 1)[0]
    text = unicodedata.normalize("NFKC", document.title + " " + lede).casefold()
    words = re.findall(r"\w+", text, flags=re.UNICODE)
    size = min(3, len(words))
    if not size:
        return frozenset({text})
    return frozenset(" ".join(words[i : i + size]) for i in range(len(words) - size + 1))


def minhash(shingles: frozenset[str]) -> tuple[int, ...]:
    values = tuple(_hash(shingle) for shingle in shingles)
    return tuple(min((a * value + b) % PRIME for value in values) for a, b in PERMUTATIONS)


@dataclass(frozen=True)
class Duplicate:
    removed_doc_id: str
    retained_doc_id: str
    similarity: float
    method: str


@dataclass(frozen=True)
class DeduplicationResult:
    documents: tuple[Document, ...]
    duplicates: tuple[Duplicate, ...]


def deduplicate(documents: Iterable[Document], *, threshold: float = 0.85) -> DeduplicationResult:
    """Keep an earliest stable representative of exact and near duplicate copy.

    The 128-permutation MinHash uses 32 bands of four rows. Candidate matches are
    verified using exact shingle Jaccard, so hash collisions cannot remove an
    unrelated document. As with other LSH schemes, candidate recall is approximate.
    Identical full text is always checked, independently of the headline.
    """
    if not 0 < threshold <= 1:
        raise ValueError("deduplication threshold must be in (0, 1]")
    rows = [Document.model_validate(document) for document in documents]
    ids = [document.doc_id for document in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate document ids in input; resolve them before freezing")

    def order(document: Document) -> tuple[str, str, str]:
        stamp = document.published_at
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        return stamp.astimezone(UTC).isoformat(), document.source, document.doc_id

    rows.sort(key=order)
    kept: list[Document] = []
    features: list[frozenset[str]] = []
    bands: dict[tuple[int, tuple[int, ...]], set[int]] = defaultdict(set)
    text_hashes: dict[str, int] = {}
    duplicates: list[Duplicate] = []
    for document in rows:
        text_hash = hashlib.sha256(document.text.encode("utf-8")).hexdigest()
        shingles = title_lede_shingles(document)
        signature = minhash(shingles)
        keys = [
            (start, signature[start : start + ROWS_PER_BAND])
            for start in range(0, NUM_PERM, ROWS_PER_BAND)
        ]
        exact = text_hashes.get(text_hash)
        if exact is not None:
            duplicates.append(Duplicate(document.doc_id, kept[exact].doc_id, 1.0, "exact-text"))
            continue
        candidates = set().union(*(bands.get(key, set()) for key in keys))
        match = None
        for index in sorted(candidates):
            similarity = len(shingles & features[index]) / len(shingles | features[index])
            if similarity >= threshold:
                match = (index, similarity)
                break
        if match is not None:
            index, similarity = match
            duplicates.append(
                Duplicate(document.doc_id, kept[index].doc_id, similarity, "title-lede-minhash")
            )
            continue
        index = len(kept)
        kept.append(document)
        features.append(shingles)
        text_hashes[text_hash] = index
        for key in keys:
            bands[key].add(index)
    return DeduplicationResult(tuple(kept), tuple(duplicates))
