"""Prepare blinded retrieval relevance review and export hash-bound pilot labels.

This is Track A's passage-relevance review, not Track B's causal annotations.
The editable judgments contain no retrieval scores, ranks or seed-positive flags.
Reviewer independence is an explicit attestation, not authenticated identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from schema import Passage

from .bm25 import Aliases, BM25Retriever
from .pilot import EvidenceQuery

Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
SCOPE = (
    "Relevance reviewed within this candidate pool; exhaustive corpus positives not established."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_queries(path: Path) -> list[EvidenceQuery]:
    queries = [
        EvidenceQuery.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not queries or len({q.query_id for q in queries}) != len(queries):
        raise ValueError("review requires nonempty queries with unique query ids")
    return queries


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CandidatePoolQuery(Record):
    query_id: Name
    query: Name
    as_of: date
    passage_ids: frozenset[Name] = Field(min_length=1)


class QueryJudgment(Record):
    query_id: Name
    suitable: bool | None = None
    notes: str = ""


class CandidateJudgment(Record):
    query_id: Name
    passage_id: Name
    relevant: bool | None = None
    evidence_span: str | None = None
    notes: str = ""


class Judgments(Record):
    packet_sha256: Digest
    reviewer: str = ""
    reviewed_on: date | None = None
    independent_review: bool = False
    blinded_to_results: bool = False
    queries: list[QueryJudgment]
    candidates: list[CandidateJudgment]


class ReviewReceipt(Record):
    version: Literal[1] = 1
    curator: Name
    reviewer: Name
    reviewed_on: date
    independent_review: Literal[True]
    blinded_to_results: Literal[True]
    corpus_sha256: Digest
    input_pairs_sha256: Digest
    reviewed_pairs_sha256: Digest
    packet_sha256: Digest
    judgments_sha256: Digest
    query_ids: list[Name] = Field(min_length=1)
    judged_candidates: int = Field(ge=1)
    relevant_passages: int = Field(ge=1)
    pool_method: Name
    scope: Literal[SCOPE] = SCOPE

    @model_validator(mode="after")
    def _check(self):
        if self.reviewed_on > date.today():
            raise ValueError("review date cannot be in the future")

        def identity(name):
            return " ".join(unicodedata.normalize("NFKC", name).casefold().split())

        if identity(self.curator) == identity(self.reviewer):
            raise ValueError("independent reviewer must differ from the curator")
        if len(set(self.query_ids)) != len(self.query_ids):
            raise ValueError("receipt query ids must be unique")
        if not len(self.query_ids) <= self.relevant_passages <= self.judged_candidates:
            raise ValueError("receipt candidate/positive/query counts are inconsistent")
        return self


def _dump(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def prepare_review(
    *,
    pairs: Path,
    corpus: Path,
    aliases: Path,
    output: Path,
    curator: str,
    pool_size: int = 10,
    candidate_pool: Path | None = None,
) -> dict:
    """Union seed positives and both lexical pools; shuffle deterministically.

    Without candidate_pool this omits dense-only candidates. Neither variant
    establishes exhaustive relevance or representative temporal coverage.
    """
    curator = curator.strip()
    if not curator or not 1 <= pool_size <= 50:
        raise ValueError("curator is required and pool size must be between 1 and 50")
    queries = read_queries(pairs)
    retriever = BM25Retriever.from_jsonl(corpus, aliases=Aliases.load(aliases))
    by_id = {p.passage_id: p for p in retriever.passages}
    extra = {}
    if candidate_pool is not None:
        pooled = [
            CandidatePoolQuery.model_validate_json(line)
            for line in candidate_pool.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        extra = {q.query_id: q for q in pooled}
        if len(extra) != len(pooled) or set(extra) != {q.query_id for q in queries}:
            raise ValueError("candidate pool must cover exactly the review queries")
        if any(
            extra[q.query_id].query != q.query or extra[q.query_id].as_of != q.as_of
            for q in queries
        ):
            raise ValueError("candidate pool query text/dates differ from review queries")
    candidates = []
    for query in queries:
        ids = set(query.relevant_passage_ids)
        if extra:
            ids.update(extra[query.query_id].passage_ids)
        if ids - by_id.keys():
            raise ValueError(f"seed evidence absent from corpus for {query.query_id}")
        if any(not by_id[pid].visible_at(query.as_of) for pid in ids):
            raise ValueError(f"seed evidence postdates as-of for {query.query_id}")
        for expand in (False, True):
            ids.update(
                hit.passage.passage_id
                for hit in retriever.search(
                    query.query, as_of=query.as_of, k=pool_size, expand_aliases=expand
                )
            )
        # Hash ordering hides both ranking and seed-positive membership.
        for pid in sorted(
            ids, key=lambda pid: hashlib.sha256(f"{query.query_id}/{pid}".encode()).digest()
        ):
            candidates.append(
                {"query_id": query.query_id, "passage": by_id[pid].model_dump(mode="json")}
            )
    method = f"seed positives union plain/alias BM25 top {pool_size}; hash order"
    if candidate_pool is not None:
        method += f"; supplied candidate pool SHA-256 {sha256(candidate_pool)}"
    packet = {
        "version": 1,
        "curator": curator,
        "corpus_sha256": sha256(corpus),
        "pairs_sha256": sha256(pairs),
        "aliases_sha256": sha256(aliases),
        "pool_method": method,
        "scope": SCOPE,
        "queries": [q.model_dump(mode="json", exclude={"relevant_passage_ids"}) for q in queries],
        "candidates": candidates,
    }
    # Never overwrite a teammate's partially completed judgments.
    output.mkdir(parents=True, exist_ok=False)
    packet_path = output / "packet.json"
    packet_path.write_text(_dump(packet), encoding="utf-8")
    judgments = Judgments(
        packet_sha256=sha256(packet_path),
        queries=[QueryJudgment(query_id=q.query_id) for q in queries],
        candidates=[
            CandidateJudgment(query_id=c["query_id"], passage_id=c["passage"]["passage_id"])
            for c in candidates
        ],
    )
    (output / "judgments.json").write_text(
        _dump(judgments.model_dump(mode="json")), encoding="utf-8"
    )
    lines = [
        "# Blinded passage relevance review",
        "",
        "Read this packet and edit judgments.json. Keep scores, prior labels and pilot reports hidden.",
        "Accept each query only if its wording and date can be evaluated from these sources.",
        "Judge every candidate. For each relevant passage, copy a nonempty verbatim supporting span.",
        "Relevance does not establish causal direction, strength, or source-asserted edge labels.",
        "Set your identity, review date and both attestations only after completing independent review.",
        "Reject unsuitable queries; curate a replacement set before the 20-query research pilot.",
        "",
        f"Pool: {packet['pool_method']}. {SCOPE}",
        (
            "An additional candidate pool is included; its coverage still requires review."
            if extra
            else "Dense-only candidates are missing. Expand the pool before final configuration selection."
        ),
        "Review files contain publisher text and stay local under data/interim/.",
    ]
    for query in packet["queries"]:
        lines.extend(
            ["", f"## {query['query_id']}", "", query["query"], "", f"As-of: {query['as_of']}."]
        )
        for item in candidates:
            if item["query_id"] != query["query_id"]:
                continue
            p = item["passage"]
            lines.extend(
                [
                    "",
                    f"### {p['passage_id']}",
                    "",
                    f"{p['title']} — {p['source']}, {p['published_at']}",
                    "",
                    p["url"],
                    "",
                    p["text"],
                ]
            )
    (output / "review.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "status": "pending independent review",
        "packet_sha256": sha256(packet_path),
        "corpus_sha256": packet["corpus_sha256"],
        "pairs_sha256": packet["pairs_sha256"],
        "aliases_sha256": packet["aliases_sha256"],
        "queries": len(queries),
        "known_seed_positives": sum(len(q.relevant_passage_ids) for q in queries),
        "candidates": len(candidates),
        "as_of_months": dict(sorted(Counter(q.as_of.strftime("%Y-%m") for q in queries).items())),
        "pool_method": packet["pool_method"],
        "scope": SCOPE,
    }


def export_review(
    *, packet_path: Path, judgments_path: Path, corpus: Path, output: Path
) -> ReviewReceipt:
    """Fail closed on partial, stale, non-independent or unsupported review."""
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    judgments = Judgments.model_validate_json(judgments_path.read_text(encoding="utf-8"))
    if packet.get("version") != 1 or judgments.packet_sha256 != sha256(packet_path):
        raise ValueError("review packet version/hash mismatch")
    if packet["corpus_sha256"] != sha256(corpus):
        raise ValueError("review corpus snapshot hash mismatch")
    queries = {q["query_id"]: q for q in packet["queries"]}
    if len(queries) != len(packet["queries"]):
        raise ValueError("packet query ids must be unique")
    q_reviews = {q.query_id: q for q in judgments.queries}
    if len(q_reviews) != len(judgments.queries) or set(q_reviews) != set(queries):
        raise ValueError("review must cover exactly the packet queries, without duplicates")
    if any(q.suitable is not True for q in q_reviews.values()):
        raise ValueError("all queries need independent acceptance; replace rejected queries")
    current = {p.passage_id: p for p in BM25Retriever.from_jsonl(corpus).passages}
    candidates = {}
    for item in packet["candidates"]:
        p = Passage.model_validate(item["passage"])
        key = (item["query_id"], p.passage_id)
        if key in candidates or key[0] not in queries:
            raise ValueError("packet has duplicate candidates or unknown queries")
        if current.get(p.passage_id) != p or not p.visible_at(
            date.fromisoformat(queries[key[0]]["as_of"])
        ):
            raise ValueError("candidate is outside the current corpus or postdates as-of")
        candidates[key] = p
    reviews = {(r.query_id, r.passage_id): r for r in judgments.candidates}
    if len(reviews) != len(judgments.candidates) or set(reviews) != set(candidates):
        raise ValueError("review must cover exactly the candidate pool, without duplicates")
    positives = {qid: [] for qid in queries}
    for key, review in reviews.items():
        if review.relevant is None:
            raise ValueError("candidate review is incomplete")
        if review.relevant:
            span = review.evidence_span
            if not span or not span.strip() or span not in candidates[key].text:
                raise ValueError("relevant candidates require a verbatim evidence span")
            positives[key[0]].append(key[1])
        elif review.evidence_span is not None:
            raise ValueError("irrelevant candidates cannot carry evidence spans")
    if any(not ids for ids in positives.values()):
        raise ValueError("every query must retain at least one reviewed positive")
    pairs_text = "".join(
        json.dumps(
            {**q, "relevant_passage_ids": sorted(positives[qid])},
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
        for qid, q in queries.items()
    )
    receipt = ReviewReceipt(
        curator=packet["curator"],
        reviewer=judgments.reviewer,
        reviewed_on=judgments.reviewed_on,
        independent_review=judgments.independent_review,
        blinded_to_results=judgments.blinded_to_results,
        corpus_sha256=packet["corpus_sha256"],
        input_pairs_sha256=packet["pairs_sha256"],
        reviewed_pairs_sha256=hashlib.sha256(pairs_text.encode()).hexdigest(),
        packet_sha256=sha256(packet_path),
        judgments_sha256=sha256(judgments_path),
        query_ids=list(queries),
        judged_candidates=len(candidates),
        relevant_passages=sum(map(len, positives.values())),
        pool_method=packet["pool_method"],
    )
    # Validate before creating either artifact and refuse existing output directories.
    output.mkdir(parents=True, exist_ok=False)
    (output / "pairs.jsonl").write_text(pairs_text, encoding="utf-8")
    (output / "receipt.json").write_text(_dump(receipt.model_dump(mode="json")), encoding="utf-8")
    return receipt


def validate_receipt(path: Path, *, pairs: Path, corpus: Path) -> ReviewReceipt:
    receipt = ReviewReceipt.model_validate_json(path.read_text(encoding="utf-8"))
    if receipt.reviewed_pairs_sha256 != sha256(pairs) or receipt.corpus_sha256 != sha256(corpus):
        raise ValueError("review receipt does not match the current pair/corpus hashes")
    queries = read_queries(pairs)
    if set(receipt.query_ids) != {q.query_id for q in queries}:
        raise ValueError("review receipt query ids differ from pilot queries")
    if receipt.relevant_passages != sum(len(q.relevant_passage_ids) for q in queries):
        raise ValueError("review receipt positive count differs from pilot pairs")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Create local blinded packet and blank judgments")
    prepare.add_argument("--pairs", type=Path, required=True)
    prepare.add_argument("--aliases", type=Path, default=Path("data/aliases.yaml"))
    prepare.add_argument("--curator", required=True)
    prepare.add_argument("--pool-size", type=int, default=10)
    prepare.add_argument(
        "--candidate-pool",
        type=Path,
        help="Unranked pooled candidates from pilot_runner --candidate-output",
    )
    export = commands.add_parser(
        "export", help="Validate human judgments and export pilot pairs/receipt"
    )
    export.add_argument("--packet", type=Path, required=True)
    export.add_argument("--judgments", type=Path, required=True)
    for command in (prepare, export):
        command.add_argument("--corpus", type=Path, default=Path("data/processed/articles.jsonl"))
        command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare_review(
                pairs=args.pairs,
                corpus=args.corpus,
                aliases=args.aliases,
                output=args.output,
                curator=args.curator,
                pool_size=args.pool_size,
                candidate_pool=args.candidate_pool,
            )
        else:
            result = export_review(
                packet_path=args.packet,
                judgments_path=args.judgments,
                corpus=args.corpus,
                output=args.output,
            ).model_dump(mode="json")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
