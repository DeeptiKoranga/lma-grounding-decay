"""Build a local, unfilled Track A reviewer workspace without rankings or seeds."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
from pathlib import Path

from corpus.review import prepare as prepare_corpus
from retrieval.review import Judgments as RetrievalJudgments

CURATOR = "Codex (machine curation for Varun Patil)"
MARKER = '<script id="embeddedPacket" type="application/json">null</script>'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_page(template: str, directory: Path, originals: dict | None = None) -> None:
    payload = (directory / "packet.json").read_bytes()
    data = {
        "payload": base64.b64encode(payload).decode(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "originals": originals or {},
    }
    embedded = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c")
    (directory / "Review.html").write_text(
        template.replace(
            MARKER, f'<script id="embeddedPacket" type="application/json">{embedded}</script>'
        )
    )


def prepare(
    *,
    snapshot: Path,
    sample: Path,
    retrieval: Path,
    raw: Path,
    extra_raw: Path,
    template_path: Path,
    output: Path,
    report: Path,
) -> dict:
    template = template_path.read_text()
    if template.count(MARKER) != 1:
        raise ValueError("review page must have exactly one empty embedded packet slot")
    # Validate source packet before copying any unfilled reviewer materials.
    rpacket = json.loads((retrieval / "packet.json").read_text())
    rjudgments = RetrievalJudgments.model_validate_json((retrieval / "judgments.json").read_text())
    if rpacket["corpus_sha256"] != digest(snapshot / "articles.jsonl"):
        raise ValueError("retrieval packet belongs to another corpus")
    if rjudgments.packet_sha256 != digest(retrieval / "packet.json"):
        raise ValueError("retrieval judgment packet binding differs")
    if (
        rjudgments.reviewer
        or rjudgments.reviewed_on
        or rjudgments.independent_review
        or rjudgments.blinded_to_results
        or any(q.suitable is not None or q.notes for q in rjudgments.queries)
        or any(
            c.relevant is not None or c.evidence_span is not None or c.notes
            for c in rjudgments.candidates
        )
    ):
        raise ValueError("reviewer delivery requires wholly blank judgments and attestations")
    # Require the exact public packet structure: no curator-side origin/rank labels.
    if set(rpacket) != {
        "aliases_sha256",
        "candidates",
        "corpus_sha256",
        "curator",
        "pairs_sha256",
        "pool_method",
        "queries",
        "scope",
        "version",
    } or any(set(c) != {"query_id", "passage"} for c in rpacket["candidates"]):
        raise ValueError("unexpected fields in blinded retrieval packet")
    output.mkdir(parents=True, exist_ok=False)
    corpus_dir = output / "01_corpus"
    cinfo = prepare_corpus(snapshot=snapshot, sample=sample, curator=CURATOR, output=corpus_dir)
    corpus_packet = json.loads((corpus_dir / "packet.json").read_text())
    originals, source_records = {}, []
    (corpus_dir / "originals").mkdir()
    for row in corpus_packet["items"]:
        doc = row["document"]
        url_key = hashlib.sha256(doc["url"].encode()).hexdigest()[:20]
        candidates = [root / doc["source"] / f"{url_key}.meta.json" for root in (raw, extra_raw)]
        candidates = [path for path in candidates if path.exists()]
        if len(candidates) != 1:
            raise ValueError(f"expected one raw source record for {doc['doc_id']}")
        sidecar = candidates[0]
        meta = json.loads(sidecar.read_text())
        if not meta.get("accepted") or meta["source"] != doc["source"] or meta["url"] != doc["url"]:
            raise ValueError("raw source identity or acceptance differs")
        suffix = ".pdf" if meta["content_type"] == "application/pdf" else ".html"
        source = sidecar.with_name(f"{url_key}{suffix}")
        if digest(source) != meta["sha256"]:
            raise ValueError("raw original checksum mismatch")
        file_key = hashlib.sha256(doc["doc_id"].encode()).hexdigest()[:24]
        name = f"originals/{file_key}{suffix}"
        shutil.copyfile(source, corpus_dir / name)
        original = {
            "kind": "pdf" if suffix == ".pdf" else "html",
            "path": name,
            "sha256": meta["sha256"],
            "record": meta,
        }
        if suffix == ".html":
            html = source.read_bytes().decode(meta.get("charset") or "utf-8")
            original["payload"] = base64.b64encode(html.encode()).decode()
        originals[doc["doc_id"]] = original
        source_records.append(
            {
                "doc_id": doc["doc_id"],
                "path": name,
                "raw_sha256": meta["sha256"],
                "source_record": meta,
            }
        )
    (corpus_dir / "source_records.json").write_text(json.dumps(source_records, indent=2) + "\n")
    make_page(template, corpus_dir, originals)
    retrieval_dir = output / "02_relevance"
    retrieval_dir.mkdir()
    for name in ("packet.json", "judgments.json"):
        shutil.copyfile(retrieval / name, retrieval_dir / name)
    make_page(template, retrieval_dir)
    instructions = """# Track A independent review

1. Open `01_corpus/Review.html` in a browser. The 73 extracted documents and their
   checksummed archived originals are attached. HTML originals are displayed
   without scripts or network access; PDF originals are local files. Check the
   complete extraction, publication/version eligibility and source terms.
2. Save progress at any point; keep the downloaded `corpus_judgments.json` or `relevance_judgments.json`. To resume,
   open the same Review page and load your saved judgments. Nothing is uploaded.
   Supply your own identity/date/independence only after doing the review.
3. Give the completed corpus judgments to the curator for validation. Rejected
   items require correction and a new version-bound packet before acceptance.
   Acceptance covers this deterministic source/month sample, not every source,
   all extraction quality or any redistribution permission.
4. After corpus acceptance, open `02_relevance/Review.html`. Review suitability
   of all 20 questions, then relevance of each passage at its displayed cutoff.
   A relevant judgment needs an exact evidence span. Scores, ranks, retrieval
   origins and seed flags are withheld. Do not read comparison reports or the
   source pair file before a blinded review. Save and return your judgments.

The reviewer must be a human distinct from the curator. Do not prefill judgments
from model outputs. This workspace does not include baseline correction or
support review; those use the separate archived v1 experiment packets and may
require different reviewers to preserve condition blinding. Keep publisher text
local unless its redistribution terms have been checked. No external messages,
sharing, assignment or research acceptance has occurred by creating this folder.
"""
    (output / "START_HERE.md").write_text(instructions)
    files = sorted(p for p in output.rglob("*") if p.is_file())
    result = {
        "status": "ready for independent human review; wholly blank judgments",
        "reviewer_assigned": False,
        "directory": str(output),
        "corpus_sha256": rpacket["corpus_sha256"],
        "corpus_review_items": cinfo["items"],
        "raw_originals_attached": len(originals),
        "retrieval_questions": len(rpacket["queries"]),
        "retrieval_passages": len(rpacket["candidates"]),
        "corpus_packet_sha256": cinfo["packet_sha256"],
        "retrieval_packet_sha256": digest(retrieval_dir / "packet.json"),
        "files": [
            {"path": str(p.relative_to(output)), "bytes": p.stat().st_size, "sha256": digest(p)}
            for p in files
        ],
        "contains_no_seed_pair_file_or_scores": True,
        "contains_no_curator_mapping": True,
        "reviewer_judgments_blank": True,
        "research_acceptance": False,
    }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=Path("data/processed"))
    parser.add_argument(
        "--sample",
        type=Path,
        default=Path("data/interim/corpus_v3_20261023/extraction_judgments.json"),
    )
    parser.add_argument(
        "--retrieval", type=Path, default=Path("data/interim/retrieval_review_temporal_v4")
    )
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--extra-raw", type=Path, default=Path("data/raw/track_a_continuation"))
    parser.add_argument("--template", type=Path, default=Path("notebooks/review_track_a.html"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(
            snapshot=args.snapshot,
            sample=args.sample,
            retrieval=args.retrieval,
            raw=args.raw,
            extra_raw=args.extra_raw,
            template_path=args.template,
            output=args.output,
            report=args.report,
        )
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                key: result[key]
                for key in [
                    "status",
                    "corpus_review_items",
                    "raw_originals_attached",
                    "retrieval_questions",
                    "retrieval_passages",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
