"""Rebuild normalised documents + Passage JSONL from collected raw HTML."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from . import chunk_document, parse_html
from .official import parse_official
from .quality import rejection_reason


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/interim"))
    parser.add_argument(
        "--macro-only",
        action="store_true",
        help="Apply the documented research-topic screen to news",
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    docs = {}
    failures = []
    for sidecar in sorted(args.raw.glob("*/*.meta.json")):
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
            if not isinstance(meta, dict):
                raise ValueError("cached metadata must be a JSON object")
            if not meta.get("accepted"):
                raise ValueError(meta.get("rejection_reason") or "not accepted by collector")
            extension = ".pdf" if meta.get("content_type") == "application/pdf" else ".html"
            payload = sidecar.with_name(sidecar.name.removesuffix(".meta.json") + extension)
            raw = payload.read_bytes()
            if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
                raise ValueError("raw payload checksum mismatch")
            if meta.get("source_kind") == "official":
                doc = parse_official(
                    raw,
                    source=meta["source"],
                    url=meta["url"],
                    title=meta["title"],
                    published_at=meta["published_at"],
                    content_type=meta["content_type"],
                    charset=meta.get("charset") or "utf-8",
                )
            else:
                doc = parse_html(
                    raw.decode(meta.get("charset") or "utf-8", errors="replace"),
                    source=meta["source"],
                    url=meta["url"],
                )
            if args.macro_only and (reason := rejection_reason(doc)):
                raise ValueError(reason)
            if doc.doc_id in docs and docs[doc.doc_id] != doc:
                raise ValueError("conflicting cached versions of a document")
            docs[doc.doc_id] = doc
        except (ValueError, OSError, KeyError, LookupError, TypeError) as exc:
            failures.append({"file": str(sidecar), "error": str(exc)})
    with (
        (args.output / "documents.jsonl").open("w", encoding="utf-8") as documents,
        (args.output / "articles.jsonl").open("w", encoding="utf-8") as passages,
    ):
        for doc in sorted(docs.values(), key=lambda d: d.doc_id):
            documents.write(doc.model_dump_json() + "\n")
            for passage in chunk_document(doc):
                passages.write(passage.model_dump_json() + "\n")
    (args.output / "parse_errors.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in failures), encoding="utf-8"
    )
    print(json.dumps({"documents": len(docs), "rejected": len(failures)}))


if __name__ == "__main__":
    main()
