"""Stage source-review repairs as a new candidate; preserve the reviewed corpus."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from corpus import Document, parse_html
from corpus.freeze import freeze_corpus
from corpus.quality import rejection_reason
from schema import Passage


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", type=Path, default=Path("data/processed"))
    p.add_argument("--raw", type=Path, default=Path("data/raw"))
    p.add_argument("--extra-raw", type=Path, default=Path("data/raw/track_a_continuation"))
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--version", default="v4-source-review-candidate")
    p.add_argument("--reviewed-on", default="2026-10-25")
    a = p.parse_args()
    if a.output.exists() or a.report.exists():
        raise ValueError("retain existing candidates and choose fresh paths")
    before = digest(a.snapshot / "articles.jsonl")
    documents = [
        Document.model_validate_json(line)
        for line in (a.snapshot / "documents.jsonl").read_text().splitlines()
    ]
    retained, changed, excluded = [], [], []
    for doc in documents:
        if doc.source_kind.value == "official":
            retained.append(doc)
            continue
        key = hashlib.sha256(doc.url.encode()).hexdigest()[:20]
        matches = [root / doc.source / f"{key}.meta.json" for root in (a.raw, a.extra_raw)]
        matches = [path for path in matches if path.exists()]
        if len(matches) != 1:
            raise ValueError(f"expected one raw source record: {doc.doc_id}")
        sidecar = matches[0]
        meta = json.loads(sidecar.read_text())
        raw = sidecar.with_name(f"{key}.html")
        if (
            not meta.get("accepted")
            or meta["url"] != doc.url
            or meta["source"] != doc.source
            or digest(raw) != meta["sha256"]
        ):
            raise ValueError(f"source identity/checksum mismatch: {doc.doc_id}")
        revised = parse_html(
            raw.read_bytes().decode(meta.get("charset") or "utf-8"), source=doc.source, url=doc.url
        )
        if revised.doc_id != doc.doc_id or revised.published_at != doc.published_at:
            raise ValueError("source publication identity changed")
        if reason := rejection_reason(revised):
            excluded.append({"doc_id": doc.doc_id, "reason": reason, "raw_sha256": meta["sha256"]})
            continue
        retained.append(revised)
        if revised.text != doc.text:
            changed.append(
                {
                    "doc_id": doc.doc_id,
                    "source": doc.source,
                    "old_chars": len(doc.text),
                    "new_chars": len(revised.text),
                    "raw_sha256": meta["sha256"],
                }
            )
    result = freeze_corpus(retained, a.output / "snapshot", version=a.version)
    reverse = freeze_corpus(list(reversed(retained)), a.output / "reverse", version=a.version)
    assert result.archive_sha256 == reverse.archive_sha256
    parents = {
        d.doc_id: d
        for d in (
            Document.model_validate_json(line)
            for line in (a.output / "snapshot/documents.jsonl").read_text().splitlines()
        )
    }
    passages = [
        Passage.model_validate_json(line)
        for line in (a.output / "snapshot/articles.jsonl").read_text().splitlines()
    ]
    assert all(parents[v.doc_id].text[v.char_start : v.char_end] == v.text for v in passages)
    assert digest(a.snapshot / "articles.jsonl") == before
    report = {
        "status": f"{a.version} candidate; source snapshot, prior indexes, experiments and human records unchanged",
        "method": "Codex source review and checksum-bound reparse; not independent human acceptance",
        "reviewed_on": a.reviewed_on,
        "research_acceptance": False,
        "original_corpus_sha256": before,
        "candidate_corpus_sha256": digest(a.output / "snapshot/articles.jsonl"),
        "candidate_archive_sha256": result.archive_sha256,
        "candidate": str(a.output / "snapshot"),
        "documents": len(parents),
        "passages": len(passages),
        "sources": dict(Counter(d.source for d in parents.values())),
        "changed_documents": len(changed),
        "changed_by_source": dict(Counter(d["source"] for d in changed)),
        "changes": changed,
        "excluded": excluded,
        "checks": {
            "all_offsets_exact": True,
            "reverse_input_archive_identical": True,
            "reviewed_corpus_unchanged": True,
        },
        "remaining_limits": [
            "PDF table layout and image-only content are not repaired by HTML fixes.",
            "A corpus change requires new indexes and passage/review migration before experiments.",
            "No human review receipt, source-rights clearance or research configuration decision is generated.",
        ],
    }
    a.report.parent.mkdir(parents=True, exist_ok=True)
    a.report.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps({k: v for k, v in report.items() if k not in {"changes", "excluded"}}, indent=2)
    )


if __name__ == "__main__":
    main()
