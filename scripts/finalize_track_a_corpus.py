"""Build a scoped, reproducible development corpus from verified local originals.

PDF narrative is indexed; table/chart fragments and image-led articles are
excluded rather than assigned invented meanings. Originals and older corpora
are preserved. No research acceptance or human receipt is generated.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from corpus import Document, chunk_document, normalise_paragraphs, parse_html
from corpus.freeze import freeze_corpus
from corpus.parser import ParseError
from corpus.pdf_layout import extract_narrative
from corpus.quality import rejection_reason


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(snapshot, output, report, version="v5-narrative-development"):
    if output.exists() or report.exists():
        raise ValueError("choose fresh output paths; existing revisions are preserved")
    before = digest(snapshot / "articles.jsonl")
    old = [
        Document.model_validate_json(line)
        for line in (snapshot / "documents.jsonl").read_text().splitlines()
    ]
    output.mkdir(parents=True)
    documents, changes, exclusions, pdf_counts = [], [], [], Counter()
    for document in old:
        key = hashlib.sha256(document.url.encode()).hexdigest()[:20]
        sidecars = [
            root / document.source / f"{key}.meta.json"
            for root in (Path("data/raw"), Path("data/raw/track_a_continuation"))
        ]
        matches = [p for p in sidecars if p.exists()]
        if len(matches) != 1:
            raise ValueError(f"expected one accepted original for {document.doc_id}")
        meta_path = matches[0]
        meta = json.loads(meta_path.read_text())
        suffix = ".pdf" if meta["content_type"] == "application/pdf" else ".html"
        raw = meta_path.with_name(key + suffix)
        if not meta["accepted"] or meta["url"] != document.url or digest(raw) != meta["sha256"]:
            raise ValueError("raw source identity/checksum changed")
        if document.source_kind.value == "official":
            try:
                paragraphs, layout = extract_narrative(raw.read_bytes())
            except ParseError as error:
                if not str(error).startswith("no adequate narrative"):
                    raise
                exclusions.append(
                    {"doc_id": document.doc_id, "reason": str(error), "raw_sha256": meta["sha256"]}
                )
                continue
            revised = Document.model_validate(
                {**document.model_dump(), "text": normalise_paragraphs(paragraphs)}
            )
            records = []
            for row in layout:
                records.append(
                    {**row, "text_sha256": hashlib.sha256(row["text"].encode()).hexdigest()}
                )
                pdf_counts["retained" if row["reason"] is None else "excluded"] += 1
            (output / f"{document.doc_id}.layout.json").write_text(
                json.dumps(
                    {"raw_sha256": meta["sha256"], "blocks": records}, ensure_ascii=False, indent=2
                )
                + "\n"
            )
        else:
            revised = parse_html(
                raw.read_bytes().decode(meta.get("charset") or "utf-8"),
                source=document.source,
                url=document.url,
            )
        if revised.doc_id != document.doc_id or revised.published_at != document.published_at:
            raise ValueError("publication identity changed")
        if reason := rejection_reason(revised):
            exclusions.append(
                {"doc_id": document.doc_id, "reason": reason, "raw_sha256": meta["sha256"]}
            )
            continue
        documents.append(revised)
        if revised.text != document.text:
            changes.append(
                {
                    "doc_id": document.doc_id,
                    "source": document.source,
                    "old_chars": len(document.text),
                    "new_chars": len(revised.text),
                    "raw_sha256": meta["sha256"],
                }
            )
    frozen = freeze_corpus(documents, output / "snapshot", version=version)
    reverse = freeze_corpus(list(reversed(documents)), output / "reverse", version=version)
    assert frozen.archive_sha256 == reverse.archive_sha256
    parents = [
        Document.model_validate_json(line)
        for line in (output / "snapshot/documents.jsonl").read_text().splitlines()
    ]
    passages = [p for d in parents for p in chunk_document(d)]
    assert all(
        d.text[p.char_start : p.char_end] == p.text for d in parents for p in chunk_document(d)
    )
    assert digest(snapshot / "articles.jsonl") == before
    result = {
        "version": version,
        "built_on": "2026-10-26",
        "status": "scoped development corpus; independent research acceptance pending",
        "research_acceptance": False,
        "source_corpus_sha256": before,
        "corpus_sha256": digest(output / "snapshot/articles.jsonl"),
        "documents_sha256": digest(output / "snapshot/documents.jsonl"),
        "archive_sha256": frozen.archive_sha256,
        "snapshot": str(output / "snapshot"),
        "documents": len(parents),
        "passages": len(passages),
        "sources": dict(sorted(Counter(d.source for d in parents).items())),
        "changed_documents": len(changes),
        "changes": changes,
        "excluded_documents": exclusions,
        "pdf_blocks": dict(pdf_counts),
        "checks": {
            "offsets_exact": True,
            "reverse_archive_identical": True,
            "original_corpus_unchanged": True,
        },
        "scope": [
            "PDF evidence is narrative-only; tables/charts/headers/short fragments remain in checksummed originals and block-location audit files, outside the text index.",
            "No table headers, decimal points or infographic numbers are inferred or transcribed.",
            "ET custom related-story links and explicit publisher promotion are excluded; lifestyle and image-led articles are outside this evidence scope.",
            "Publisher-origin word-joining defects are preserved verbatim, not silently corrected.",
            "Source balance, rights, dated-source adequacy and independent human acceptance are limitations, not passed gates.",
        ],
    }
    report.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"changes", "excluded_documents"}},
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=Path("data/processed"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--version", default="v5-narrative-development")
    args = parser.parse_args()
    build(args.snapshot, args.output, args.report, args.version)


if __name__ == "__main__":
    main()
