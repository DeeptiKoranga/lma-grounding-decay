"""Check that a run manifest covers exactly the signed references."""

import argparse
from pathlib import Path

from conditions.pipeline import Query
from conditions.provenance import digest
from eval.references import validate


def identity(record):
    anchor = record.anchor
    return record.as_of, anchor.var, anchor.direction, anchor.event_date


def validate_manifest(queries_path: Path, references_path: Path, corpus: Path):
    queries = [
        Query.model_validate_json(line)
        for line in queries_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    references, receipt = validate(
        references=references_path,
        corpus=corpus,
        expected_corpus_sha256=digest(corpus),
    )
    if len(queries) != len(references) or {q.query_id for q in queries} != references.keys():
        raise ValueError("query manifest must cover each signed reference exactly once")
    for query in queries:
        if identity(query) != identity(references[query.query_id]):
            raise ValueError(f"{query.query_id} differs from its signed cutoff or anchor")
    return queries, references, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--references", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/articles.jsonl"))
    args = parser.parse_args()
    try:
        queries, _, receipt = validate_manifest(args.queries, args.references, args.corpus)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"evaluation preflight: {exc}\n")
    print(f"Validated {len(queries)} queries against signed reference receipt {receipt}")


if __name__ == "__main__":
    main()
