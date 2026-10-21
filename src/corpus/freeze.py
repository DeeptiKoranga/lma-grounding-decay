"""Build an auditable corpus snapshot and reproducible zip (Track A, A4).

Run ``python -m corpus.freeze --documents data/interim/documents.jsonl``.
Small snapshots are explicitly provisional: this command never invents articles
or declares the research corpus complete based on a successful software run.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

from schema import CORPUS_END, CORPUS_START, SourceKind

from .dedup import NUM_PERM, ROWS_PER_BAND, deduplicate
from .documents import Document, chunk_document

EXPECTED_SOURCES = (
    "businessline",
    "economic_times",
    "business_standard",
    "mint",
    "rbi",
    "mospi",
    "ppac",
    "pib",
)


def load_documents(path: Path) -> list[Document]:
    documents = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                documents.append(Document.model_validate_json(line))
            except ValueError as exc:
                raise ValueError(f"{path}:{line_number}: invalid document: {exc}") from exc
    return documents


def _jsonl(rows: Iterable[dict]) -> bytes:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")


def _archive(payloads: dict[str, bytes]) -> bytes:
    target = io.BytesIO()
    # Stored rather than compressed entries keep bytes identical across zlib versions.
    with ZipFile(target, "w", compression=ZIP_STORED) as archive:
        for name, payload in sorted(payloads.items()):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, payload)
    return target.getvalue()


def _cell(value: str) -> str:
    return " ".join(value.replace("|", "\\|").split())


@dataclass(frozen=True)
class FreezeResult:
    documents: int
    passages: int
    duplicates: int
    news_documents: int
    official_documents: int
    provisional: bool
    archive_sha256: str
    manifest: Path


def freeze_corpus(
    documents: Iterable[Document],
    output: Path,
    *,
    version: str = "v1",
    threshold: float = 0.85,
    overwrite: bool = False,
) -> FreezeResult:
    """Write validated source texts, passages, duplicate audit, zip and manifest.

    Existing snapshot files require an explicit overwrite. No source text is
    rewritten after parsing: passage offsets address the archived parent text.
    """
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", version):
        raise ValueError("version must be a short filename-safe identifier")
    output = Path(output)
    archive_name = f"corpus-{version}.zip"
    names = ("documents.jsonl", "articles.jsonl", "duplicates.jsonl", archive_name, "MANIFEST.md")
    if not overwrite and any((output / name).exists() for name in names):
        raise FileExistsError("snapshot exists; select another output or explicitly overwrite")
    result = deduplicate(documents, threshold=threshold)
    kept = sorted(result.documents, key=lambda document: document.doc_id)
    passages = [passage for document in kept for passage in chunk_document(document)]
    payloads = {
        "documents.jsonl": _jsonl(document.model_dump(mode="json") for document in kept),
        "articles.jsonl": _jsonl(passage.model_dump(mode="json") for passage in passages),
        "duplicates.jsonl": _jsonl(asdict(duplicate) for duplicate in result.duplicates),
    }
    payloads[archive_name] = _archive(payloads)
    hashes = {name: hashlib.sha256(payload).hexdigest() for name, payload in payloads.items()}
    news = sum(document.source_kind is SourceKind.NEWS for document in kept)
    official = sum(document.source_kind is SourceKind.OFFICIAL for document in kept)
    provisional = news < 900 or official < 60
    counts = Counter(
        (document.source, document.published_at.strftime("%Y-%m")) for document in kept
    )
    months = tuple(f"2026-{month:02d}" for month in range(3, 10))
    sources = sorted(set(EXPECTED_SOURCES) | {document.source for document in kept})
    status = (
        "PROVISIONAL — acquisition targets are not met; this is a pipeline snapshot, not the final frozen research corpus."
        if provisional
        else "TARGET COUNTS MET — source coverage, extraction quality and licences still require review before the final research freeze."
    )
    lines = [
        f"# Corpus snapshot {version}",
        "",
        f"**Status: {status}**",
        "",
        f"Publication window: {CORPUS_START} through {CORPUS_END} (inclusive).",
        f"Retained: {len(kept)} documents ({news} news, {official} official), {len(passages)} passages.",
        f"Removed duplicates: {len(result.duplicates)}; input documents: {len(kept) + len(result.duplicates)}.",
        f"Plan targets: at least 900 news articles and 60 official documents. Shortfalls: {max(0, 900 - news)} news, {max(0, 60 - official)} official.",
        "",
        "## Documents by source and publication month",
        "",
        "| Source | " + " | ".join(months) + " | Total |",
        "|---|" + "---:|" * (len(months) + 1),
    ]
    for source in sources:
        values = [counts[source, month] for month in months]
        lines.append(f"| {_cell(source)} | " + " | ".join(map(str, values)) + f" | {sum(values)} |")
    lines.extend(
        [
            "",
            "## SHA-256 and sharing",
            "",
            f"Share `{archive_name}` separately; corpus payloads remain outside git. The zip contains the three JSONL files below.",
            "",
            "| File | Bytes | SHA-256 |",
            "|---|---:|---|",
        ]
    )
    lines.extend(
        f"| `{name}` | {len(payloads[name])} | `{hashes[name]}` |" for name in sorted(payloads)
    )
    lines.extend(
        [
            "",
            "## Deduplication and offsets",
            "",
            f"Exact full-text hashes plus MinHash on case-folded title + first-paragraph word trigrams; {NUM_PERM} deterministic permutations, {NUM_PERM // ROWS_PER_BAND} bands x {ROWS_PER_BAND} rows, exact Jaccard >= {threshold:g} required for near matches.",
            "MinHash candidate recall is approximate. Earliest publication timestamp, then source/id, chooses the retained representative. Each removal is recorded in `duplicates.jsonl`.",
            "Parent text is preserved in `documents.jsonl`; `articles.jsonl` contains paragraph passages whose character offsets address that exact normalised parent text. Raw publisher payloads and collection logs remain in `data/raw/`.",
            "The zip uses sorted entries, fixed timestamps and permissions, and stored bytes so identical inputs and settings yield identical archive hashes.",
            "",
            "## Licence notes",
            "",
            "These are collection notes, not redistribution permission. Confirm source terms before sharing publisher text.",
        ]
    )
    licences: dict[str, set[str]] = {}
    for document in kept:
        licences.setdefault(document.source, set()).add(document.licence_note)
    if not licences:
        lines.append("No documents collected; no source licence review has been completed.")
    for source, notes in sorted(licences.items()):
        lines.append(f"- {_cell(source)}: " + "; ".join(_cell(note) for note in sorted(notes)))
    lines.extend(
        [
            "",
            "Macro series confirm observed moves only; they are never evidence for causal edges and are excluded from this text corpus snapshot.",
            "",
        ]
    )
    output.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        (output / name).write_bytes(payload)
    manifest = output / "MANIFEST.md"
    manifest.write_text("\n".join(lines), encoding="utf-8")
    return FreezeResult(
        len(kept),
        len(passages),
        len(result.duplicates),
        news,
        official,
        provisional,
        hashes[archive_name],
        manifest,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=Path, default=Path("data/interim/documents.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/processed"))
    parser.add_argument("--version", default="v1")
    parser.add_argument("--threshold", type=float, default=0.85)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        result = freeze_corpus(
            load_documents(args.documents),
            args.output,
            version=args.version,
            threshold=args.threshold,
            overwrite=args.overwrite,
        )
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(asdict(result), default=str, indent=2))


if __name__ == "__main__":
    main()
