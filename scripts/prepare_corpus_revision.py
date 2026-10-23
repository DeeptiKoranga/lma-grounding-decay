"""Stage an auditable corpus revision without changing the active frozen corpus.

Only explicit related-story paragraphs are removed from existing parent texts.
New source files pass the ordinary checksum, publication, paywall and version
checks. The candidate gets new passage offsets and a separate archive. Reviewers
must accept a corpus revision before indexes, pairs and experiments are migrated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from corpus import Document, normalise_paragraphs, parse_html
from corpus.freeze import freeze_corpus
from corpus.parser import is_navigation_paragraph
from corpus.quality import rejection_reason
from schema import Passage


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(*, frozen: Path, extra_raw: Path, output: Path, report: Path) -> dict:
    if output.exists():
        raise ValueError("candidate output exists; preserve it and choose a fresh path")
    original = [
        Document.model_validate_json(line)
        for line in (frozen / "documents.jsonl").read_text().splitlines()
    ]
    before = [
        Passage.model_validate_json(line)
        for line in (frozen / "articles.jsonl").read_text().splitlines()
    ]
    parents = {d.doc_id: d for d in original}
    if any(parents[p.doc_id].text[p.char_start : p.char_end] != p.text for p in before):
        raise ValueError("original passage/parent alignment failed")
    revised, removals = [], []
    for document in original:
        paragraphs = document.text.split("\n\n")
        removed = [i for i, p in enumerate(paragraphs) if is_navigation_paragraph(p)]
        text = normalise_paragraphs(p for p in paragraphs if not is_navigation_paragraph(p))
        revised.append(Document.model_validate({**document.model_dump(), "text": text}))
        if removed:
            removals.append({"doc_id": document.doc_id, "paragraph_indices": removed})
    added, excluded = [], []
    identities = {d.doc_id for d in revised}
    for sidecar in sorted(extra_raw.glob("*/*.meta.json")):
        meta = json.loads(sidecar.read_text())
        identity = {"url": meta["url"], "metadata": str(sidecar)}
        try:
            if not meta.get("accepted"):
                raise ValueError(meta.get("rejection_reason") or "collector rejected source")
            path = sidecar.with_name(sidecar.name.removesuffix(".meta.json") + ".html")
            if sha256(path) != meta["sha256"]:
                raise ValueError("raw source checksum mismatch")
            doc = parse_html(
                path.read_bytes().decode(meta.get("charset") or "utf-8"),
                source=meta["source"],
                url=meta["url"],
            )
            if reason := rejection_reason(doc):
                raise ValueError(reason)
            if doc.doc_id in identities:
                raise ValueError("source identity already present; no replacement allowed")
            identities.add(doc.doc_id)
            revised.append(doc)
            added.append(
                {
                    **identity,
                    "doc_id": doc.doc_id,
                    "published_at": doc.published_at.isoformat(),
                    "raw_sha256": meta["sha256"],
                }
            )
        except (ValueError, OSError, KeyError) as exc:
            excluded.append({**identity, "reason": str(exc)})
    snapshot = output / "snapshot"
    result = freeze_corpus(revised, snapshot, version="v2-candidate")
    reverse = output / "reverse_order_check"
    repeated = freeze_corpus(list(reversed(revised)), reverse, version="v2-candidate")
    if result.archive_sha256 != repeated.archive_sha256:
        raise ValueError("candidate archive depends on input order")
    documents = [
        Document.model_validate_json(line)
        for line in (snapshot / "documents.jsonl").read_text().splitlines()
    ]
    passages = [
        Passage.model_validate_json(line)
        for line in (snapshot / "articles.jsonl").read_text().splitlines()
    ]
    parents = {d.doc_id: d for d in documents}
    if any(parents[p.doc_id].text[p.char_start : p.char_end] != p.text for p in passages):
        raise ValueError("candidate passage/parent alignment failed")
    if any(is_navigation_paragraph(p.text) for p in passages):
        raise ValueError("explicit related-story navigation remains in candidate")
    groups = defaultdict(list)
    for doc in documents:
        groups[(doc.source, str(doc.published_at.date())[:7])].append(doc)
    sampled = []
    review_text = [
        "# Corpus extraction review — pending human inspection",
        "",
        "Check first/last paragraphs against the raw page/PDF, publication/version, omissions, table layout and source terms. This is a deterministic source/month sample, not an acceptance certificate.",
        "",
    ]
    for key, docs in sorted(groups.items()):
        for doc in sorted(docs, key=lambda d: hashlib.sha256(d.doc_id.encode()).hexdigest())[:2]:
            sample = {
                "doc_id": doc.doc_id,
                "source": key[0],
                "month": key[1],
                "url": doc.url,
                "text_sha256": hashlib.sha256(doc.text.encode()).hexdigest(),
                "extraction_accepted": None,
                "publication_version_accepted": None,
                "source_terms_reviewed": None,
                "notes": "",
            }
            sampled.append(sample)
            parts = doc.text.split("\n\n")
            review_text += [
                f"## {doc.doc_id}",
                "",
                f"{doc.published_at.isoformat()} — {doc.url}",
                "",
                "First paragraph:",
                "",
                parts[0],
                "",
                "Last paragraph:",
                "",
                parts[-1],
                "",
            ]
    judgments = {
        "reviewer": "",
        "reviewed_on": None,
        "accepted": False,
        "snapshot_sha256": sha256(snapshot / "articles.jsonl"),
        "items": sampled,
    }
    (output / "extraction_judgments.json").write_text(json.dumps(judgments, indent=2) + "\n")
    (output / "extraction_review.md").write_text("\n".join(review_text))
    audit = {
        "status": "candidate only; active corpus/index/experiments unchanged",
        "human_review_complete": False,
        "original_articles_sha256": sha256(frozen / "articles.jsonl"),
        "candidate_articles_sha256": sha256(snapshot / "articles.jsonl"),
        "candidate_archive_sha256": result.archive_sha256,
        "removed_navigation_paragraphs": sum(len(x["paragraph_indices"]) for x in removals),
        "changed_original_documents": len(removals),
        "removals": removals,
        "added": added,
        "excluded": excluded,
        "documents": len(documents),
        "passages": len(passages),
        "sources": dict(sorted(Counter(d.source for d in documents).items())),
        "sampled_documents": len(sampled),
        "checks": {
            "original_offsets_exact": True,
            "candidate_offsets_exact": True,
            "known_related_link_prefixes_absent": True,
            "reversed_input_archive_identical": True,
            "human_judgments_blank": True,
        },
        "local_candidate": str(snapshot),
        "local_review": str(output / "extraction_review.md"),
        "limitations": [
            "Unlabelled recommendations, missing lead sentences and flattened PDF tables still require inspection.",
            "RBI and Business Standard remain absent; source terms have not been accepted.",
            "Do not use v1 passage IDs, dense indexes or review receipts with the candidate.",
            "A corpus change requires new retrieval curation, embeddings, review packets and experiments.",
        ],
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(audit, indent=2) + "\n")
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen", type=Path, default=Path("data/processed"))
    parser.add_argument("--extra-raw", type=Path, default=Path("data/raw/track_a_continuation"))
    parser.add_argument(
        "--output", type=Path, default=Path("data/interim/corpus_revision_20261023")
    )
    parser.add_argument("--report", type=Path, default=Path("reports/corpus_revision_audit.json"))
    args = parser.parse_args()
    audit = prepare(
        frozen=args.frozen, extra_raw=args.extra_raw, output=args.output, report=args.report
    )
    print(
        json.dumps(
            {
                k: audit[k]
                for k in [
                    "status",
                    "documents",
                    "passages",
                    "removed_navigation_paragraphs",
                    "sampled_documents",
                ]
            }
        )
    )


if __name__ == "__main__":
    main()
