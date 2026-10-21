"""Run A8's four configurations on one reviewed query/evidence file.

No labels or results are generated automatically. A research pilot requires 20
independently reviewed pairs. Use --smoke for smaller functional checks only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .bm25 import Aliases, BM25Retriever
from .factory import build_retriever
from .hybrid import HybridRetriever
from .pilot import (
    CONFIG_ORDER,
    EvidenceQuery,
    PlainBM25,
    evaluate,
    evaluate_configs,
    select_simplest,
)
from .rerank import BGEReranker, RerankingRetriever


class CachedCandidates:
    """Save the first-stage top 50 so the dense model can unload before reranking."""

    def __init__(self, retriever):
        self.retriever = retriever
        self.passages, self.aliases = retriever.passages, retriever.aliases
        self.cache = {}

    def search(self, query, *, as_of, k=10, source_kind="any", must_mention=None):
        from .filters import validate_query

        args = validate_query(
            query,
            as_of=as_of,
            k=k,
            source_kind=source_kind,
            must_mention=must_mention,
            aliases=self.aliases,
        )
        key = (args.query, args.as_of, args.source_kind, tuple(args.must_mention))
        if key not in self.cache:
            if self.retriever is None:
                raise ValueError("uncached first-stage request after model unloading")
            self.cache[key] = self.retriever.search(
                args.query,
                as_of=args.as_of,
                k=50,
                source_kind=args.source_kind,
                must_mention=args.must_mention,
            )
        return self.cache[key][: args.k]

    def detach(self):
        self.retriever = None


def package_versions():
    versions = {}
    for package in ("torch", "sentence-transformers", "transformers", "faiss-cpu"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/articles.jsonl"))
    parser.add_argument("--aliases", type=Path, default=Path("data/aliases.yaml"))
    parser.add_argument("--output", type=Path, default=Path("reports/pilot_retriever.md"))
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--embedding-batch-size", type=int, default=2)
    parser.add_argument("--reranker-batch-size", type=int, default=1)
    parser.add_argument("--embedding-checkpoint", type=Path)
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument(
        "--embedding-revision", required=True, help="Pinned model revision or local asset id"
    )
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--dense-backend", choices=["exact", "faiss"], default="exact")
    parser.add_argument("--dense-index", type=Path)
    parser.add_argument("--rerank", action="store_true")
    parser.add_argument("--reranker-revision")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    if args.output.exists() and not args.overwrite:
        parser.error("report already exists; review it before using --overwrite")
    if args.rerank and not args.reranker_revision:
        parser.error("--rerank requires a pinned --reranker-revision")
    cache_state = {
        "dense_index_preexisting": bool(args.dense_index and args.dense_index.exists()),
        "embedding_checkpoint_preexisting": bool(
            args.embedding_checkpoint and args.embedding_checkpoint.exists()
        ),
    }
    try:
        queries = [
            EvidenceQuery.model_validate_json(line)
            for line in args.pairs.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(queries) != 20 and not args.smoke:
            raise ValueError(
                "the research pilot requires exactly 20 reviewed pairs; use --smoke for checks"
            )
        aliases = Aliases.load(args.aliases)
        lexical = BM25Retriever.from_jsonl(args.corpus, aliases=aliases)
        dense = build_retriever(
            list(lexical.passages),
            aliases=aliases,
            config="bge_m3",
            device=args.device,
            local_files_only=args.local_files_only,
            embedding_model=args.embedding_model,
            embedding_revision=args.embedding_revision,
            dense_backend=args.dense_backend,
            dense_index=args.dense_index,
            embedding_checkpoint=args.embedding_checkpoint,
            checkpoint_every=args.checkpoint_every,
            embedding_batch_size=args.embedding_batch_size,
            max_length=args.max_length,
        )
        configs = {
            "bm25": PlainBM25(lexical),
            "bm25_alias": lexical,
            "bge_m3": dense,
            "hybrid_rrf": HybridRetriever(lexical, dense),
        }
        configs = {name: CachedCandidates(retriever) for name, retriever in configs.items()}
        try:
            metrics = evaluate_configs(configs, queries)
        finally:
            if hasattr(dense.embedder, "unload"):
                dense.embedder.unload()
        chosen = select_simplest(metrics)
        reranked = None
        if args.rerank:
            configs[chosen].detach()
            scorer = BGEReranker(
                device=args.device,
                revision=args.reranker_revision,
                local_files_only=args.local_files_only,
                batch_size=args.reranker_batch_size,
                max_length=args.max_length,
            )
            try:
                reranked = evaluate(RerankingRetriever(configs[chosen], scorer=scorer), queries)
            finally:
                if hasattr(scorer, "unload"):
                    scorer.unload()
    except (ValueError, OSError, RuntimeError) as exc:
        parser.error(str(exc))
    status = "SMOKE CHECK ONLY; no research decision" if args.smoke else "REVIEWED PILOT"
    lines = [
        "# Retriever pilot",
        "",
        f"Status: **{status}**.",
        "",
        f"Shared query/evidence pairs: {len(queries)}. Positive passage IDs came from the supplied pair file; this runner does not certify independent annotation.",
        f"Corpus SHA-256: `{hashlib.sha256(args.corpus.read_bytes()).hexdigest()}`.",
        f"Pair file SHA-256: `{hashlib.sha256(args.pairs.read_bytes()).hexdigest()}`.",
        f"Alias file SHA-256: `{hashlib.sha256(args.aliases.read_bytes()).hexdigest()}`.",
        f"Embedding: `{args.embedding_model}` revision `{args.embedding_revision}`.",
        f"Device: `{args.device}`; dense backend: `{args.dense_backend}`; RRF constant: 60; candidate pool: 50.",
        f"Maximum input tokens: {args.max_length}; embedding batch size: {args.embedding_batch_size}; reranker batch size: {args.reranker_batch_size}.",
        f"Package versions: `{json.dumps(package_versions(), sort_keys=True)}`.",
        f"Elapsed wall time: {time.monotonic() - started:.2f} seconds.",
        f"Cache state at start: `{json.dumps(cache_state, sort_keys=True)}`. Elapsed time excludes earlier checkpoint/index precomputation.",
        "The dense model is unloaded before the cross-encoder; first-stage candidates are cached unchanged.",
        "",
        "| Configuration | Recall@5 | Recall@10 | MRR@50 |",
        "|---|---:|---:|---:|",
    ]
    for name in CONFIG_ORDER:
        row = metrics[name]
        lines.append(
            f"| {name} | {row.recall_at_5:.4f} | {row.recall_at_10:.4f} | {row.mrr_at_50:.4f} |"
        )
    if reranked is not None:
        lines.append(
            f"| {chosen} + reranker | {reranked.recall_at_5:.4f} | {reranked.recall_at_10:.4f} | {reranked.mrr_at_50:.4f} |"
        )
        lines.extend(
            [
                "",
                f"Reranker: `BAAI/bge-reranker-v2-m3`, revision `{args.reranker_revision}`; top 50 rescored.",
            ]
        )
    lines.extend(
        [
            "",
            f"Simplest configuration within 0.03 Recall@10 of the best: `{chosen}`.",
            "Smoke checks do not resolve D-02/D-03. Review the evidence and corpus quality before recording a research decision.",
            "",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(args.output),
                "smoke": args.smoke,
                "selected": chosen,
                "metrics": {key: asdict(value) for key, value in metrics.items()},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
