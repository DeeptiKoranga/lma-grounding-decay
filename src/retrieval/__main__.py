"""Search a Passage JSONL corpus with a mandatory date cutoff."""

import argparse
from datetime import date
from pathlib import Path

from .bm25 import Aliases, BM25Retriever, serialise_hits
from .factory import build_retriever
from .pilot import CONFIG_ORDER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--corpus", type=Path, default=Path("data/interim/articles.jsonl"))
    parser.add_argument("--aliases", type=Path, default=Path("data/aliases.yaml"))
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--source-kind", choices=["any", "news", "official"], default="any")
    parser.add_argument("--must-mention", action="append", default=[])
    parser.add_argument("--no-aliases", action="store_true")
    parser.add_argument("--retriever", choices=CONFIG_ORDER, default="bm25_alias")
    parser.add_argument(
        "--rerank", action="store_true", help="Rescore the top 50 eligible passages"
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--embedding-revision")
    parser.add_argument("--reranker-model", default="BAAI/bge-reranker-v2-m3")
    parser.add_argument("--reranker-revision")
    parser.add_argument("--dense-backend", choices=["exact", "faiss"], default="exact")
    parser.add_argument(
        "--dense-index", type=Path, help="Reusable vector JSON with corpus/model checks"
    )
    args = parser.parse_args()
    if args.no_aliases and args.retriever not in {"bm25", "bm25_alias"}:
        parser.error("--no-aliases applies to BM25; select --retriever bm25")
    try:
        passages = list(BM25Retriever.from_jsonl(args.corpus).passages)
        retriever = build_retriever(
            passages,
            aliases=Aliases.load(args.aliases),
            config="bm25" if args.no_aliases else args.retriever,
            rerank=args.rerank,
            device=args.device,
            local_files_only=args.local_files_only,
            embedding_model=args.embedding_model,
            embedding_revision=args.embedding_revision,
            reranker_model=args.reranker_model,
            reranker_revision=args.reranker_revision,
            dense_backend=args.dense_backend,
            dense_index=args.dense_index,
        )
        hits = retriever.search(
            args.query,
            as_of=args.as_of,
            k=args.k,
            source_kind=args.source_kind,
            must_mention=args.must_mention,
        )
    except (ValueError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    print(serialise_hits(hits))


if __name__ == "__main__":
    main()
