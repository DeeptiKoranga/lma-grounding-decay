"""Measure passage retrieval against the signed test references."""

import argparse
from pathlib import Path

from conditions.provenance import digest
from retrieval.bm25 import Aliases
from retrieval.factory import build_retriever
from retrieval.pilot import EvidenceQuery, evaluate
from retrieval.rerank import BGEReranker, RerankingRetriever
from schema import Passage
from validate_evaluation_queries import validate_manifest

EMBEDDING_REVISION = "5617a9f61b028005a4858fdac845db406aefb181"
RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument(
        "--report", default=Path("reports/test_retrieval_descriptive.md"), type=Path
    )
    args = parser.parse_args()
    if not args.index.is_file():
        parser.error("select the frozen dense index")
    queries_path = Path("data/eval/queries_test_anchored_v2.jsonl")
    queries, references, receipt = validate_manifest(
        queries_path, Path("data/eval/gold/test"), args.corpus
    )
    passages = [
        Passage.model_validate_json(line)
        for line in args.corpus.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    evidence_queries = [
        EvidenceQuery(
            query_id=query.query_id,
            query=query.query,
            as_of=query.as_of,
            relevant_passage_ids={e.evidence_passage_id for e in references[query.query_id].edges},
        )
        for query in queries
    ]
    aliases_path = Path("data/aliases.yaml")
    retriever = build_retriever(
        passages,
        aliases=Aliases.load(aliases_path),
        config="bge_m3",
        local_files_only=True,
        embedding_revision=EMBEDDING_REVISION,
        dense_backend="faiss",
        dense_index=args.index,
    )
    reranker = BGEReranker(revision=RERANKER_REVISION, local_files_only=True, batch_size=1)
    lines = [
        "# Descriptive retrieval on the signed FPI test references",
        "",
        "Two queries share one episode. Recall uses the distinct adjudicated evidence passage IDs",
        "per query. MRR@50 uses the first relevant passage. Means weight each query equally.",
        "Other relevant passages may exist outside the signed references.",
        "",
        "| Configuration | Query | Relevant passages | Recall@5 | Recall@10 | MRR@50 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for name, configuration in (
        ("BGE-M3", retriever),
        ("BGE-M3 + top-50 cross-encoder", RerankingRetriever(retriever, scorer=reranker)),
    ):
        measurements = [evaluate(configuration, [query]) for query in evidence_queries]
        for query, row in zip(evidence_queries, measurements, strict=True):
            lines.append(
                f"| {name} | {query.query_id} | {len(query.relevant_passage_ids)} | "
                f"{row.recall_at_5:.3f} | {row.recall_at_10:.3f} | {row.mrr_at_50:.3f} |"
            )
        n = len(measurements)
        values = [
            sum(getattr(row, metric) for row in measurements) / n
            for metric in ("recall_at_5", "recall_at_10", "mrr_at_50")
        ]
        lines.append(
            f"| {name} | mean (n={n}) | | " + " | ".join(f"{v:.3f}" for v in values) + " |"
        )
    lines += [
        "",
        f"Reference receipt `{receipt}`.",
        f"Query manifest `{digest(queries_path)}`.",
        f"Corpus `{digest(args.corpus)}`.",
        f"Dense index `{digest(args.index)}`.",
        f"Aliases `{digest(aliases_path)}`.",
        f"BGE-M3 revision `{EMBEDDING_REVISION}`. Reranker revision `{RERANKER_REVISION}`.",
        "",
        "This report measures passage ranking for the signed FPI queries.",
    ]
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.report}")


if __name__ == "__main__":
    main()
