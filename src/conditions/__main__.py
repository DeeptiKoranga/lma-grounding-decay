"""Run the same date-safe pipeline for selected conditions and development queries."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import uuid
from pathlib import Path

from corpus.series import SeriesStore
from llm.generate import (ANTHROPIC_HAIKU_45, AnthropicGenerator, ChatCompletionsGenerator, MLXGenerator)
from retrieval.bm25 import Aliases, BM25Retriever
from retrieval.factory import build_retriever
from retrieval.pilot import CONFIG_ORDER
from retrieval.rerank import RerankingRetriever
from retrieval.worker import WorkerRetriever
from schema import Condition
from verify.aliases import load_aliases

from .pipeline import Pipeline, Query
from .provenance import digest, model_identity, runtime_identity, source_identity, validate_cached


class WorkerScorer:
    def __init__(self, python: str, revision: str):
        self.python, self.revision = python, revision

    def score(self, query, texts):
        result = subprocess.run(
            [self.python, "-m", "retrieval.score_cli", "--revision", self.revision],
            input=json.dumps({"query": query, "texts": texts}),
            text=True,
            capture_output=True,
            check=True,
            timeout=600,
            env={**os.environ, "HF_HUB_OFFLINE": "1"},
        )
        return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path("data/processed/articles.jsonl"))
    parser.add_argument("--series", type=Path, default=Path("data/series"))
    parser.add_argument("--aliases", type=Path, default=Path("data/aliases.yaml"))
    parser.add_argument(
        "--conditions",
        nargs="+",
        choices=[c.value for c in Condition],
        default=[c.value for c in Condition],
    )
    parser.add_argument("--backend", choices=["mlx", "llama.cpp", "vllm", "api", "claude"], default="mlx")
    parser.add_argument("--model-path", type=Path, default=Path("data/raw/generator/qwen3-8b-4bit"))
    parser.add_argument("--model")
    parser.add_argument("--revision")
    parser.add_argument("--base-url")
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--retriever", choices=CONFIG_ORDER, default="bge_m3")
    parser.add_argument("--retrieval-python", help="Optional separate retrieval environment")
    parser.add_argument("--embedding-model", default="BAAI/bge-m3")
    parser.add_argument("--embedding-revision", default="5617a9f61b028005a4858fdac845db406aefb181")
    parser.add_argument(
        "--dense-index",
        type=Path,
        default=Path("data/interim/corpus_v7_index_20261026/bge_m3_vectors.json"),
    )
    parser.add_argument("--dense-backend", choices=["exact", "faiss"], default="faiss")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--require-confirmed-anchors", action="store_true")
    parser.add_argument("--reranker-python")
    parser.add_argument("--reranker-revision", default="953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e")
    parser.add_argument("--output", type=Path, default=Path("runs/development"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.model is None:
        args.model = (
            ANTHROPIC_HAIKU_45
            if args.backend == "claude"
            else "mlx-community/Qwen3-8B-4bit"
        )
    if args.backend == "claude":
        args.revision = args.revision or args.model
    elif not args.revision or not args.revision.strip():
        parser.error("--revision is required for reproducible non-Claude runs")
    if Condition.B1_R in args.conditions and not args.reranker_python:
        parser.error(
            "B1-R requires --reranker-python pointing to the existing cross-encoder environment"
        )
    queries = [
        Query.model_validate_json(line)
        for line in args.queries.read_text().splitlines()
        if line.strip()
    ]
    if not queries or len({q.query_id for q in queries}) != len(queries):
        parser.error("queries must be nonempty and uniquely identified")
    if len(set(args.conditions)) != len(args.conditions):
        parser.error("conditions must not be repeated")
    if args.backend not in {"mlx", "claude"} and not args.base_url:
        parser.error("HTTP-compatible backends require --base-url")
    dense = args.retriever in {"bge_m3", "hybrid_rrf"}
    if dense and not args.dense_index.is_file():
        parser.error("selected dense retriever requires an existing corpus-matched --dense-index")
    settings = {
        "config": args.retriever,
        "device": args.device,
        "local_files_only": True,
        "embedding_model": args.embedding_model,
        "embedding_revision": args.embedding_revision,
        "dense_backend": args.dense_backend,
        "dense_index": str(args.dense_index.resolve()) if dense else None,
        "embedding_batch_size": 8,
        "max_length": args.max_length,
    }
    inputs = {
        "format_version": 2,
        "protocol": "shared selected retriever; logged series preflight; prose baselines require independent correction",
        "source": source_identity(),
        "queries_sha256": digest(args.queries),
        "queries": [q.model_dump(mode="json") for q in queries],
        "corpus_sha256": digest(args.corpus),
        "aliases_sha256": digest(args.aliases),
        "model": args.model,
        "revision": args.revision,
        "backend": args.backend,
        "local_model_files": model_identity(args.model_path) if args.backend == "mlx" else None,
        "base_url": args.base_url,
        "allow_remote": args.allow_remote,
        "runtime": runtime_identity(),
        "conditions": args.conditions,
        "retrieval": settings,
        "dense_index_sha256": digest(args.dense_index) if dense else None,
        "retrieval_python": (
            str(Path(args.retrieval_python).absolute()) if args.retrieval_python else None
        ),
        "reranker_python": (
            str(Path(args.reranker_python).absolute()) if args.reranker_python else None
        ),
        "reranker_revision": args.reranker_revision,
        "require_confirmed_anchors": args.require_confirmed_anchors,
        "series_sha256": {p.name: digest(p) for p in sorted(args.series.glob("*.csv"))},
        "status": "development_unreviewed; not a frozen experiment",
    }
    for name in ("retrieval_python", "reranker_python"):
        if inputs[name]:
            inputs[name + "_runtime"] = runtime_identity(inputs[name])
    provenance = args.output / "inputs.json"
    if args.output.exists() and not args.resume:
        parser.error("output already exists; select a new directory or --resume")
    if provenance.exists() and json.loads(provenance.read_text()) != inputs:
        parser.error("resume input settings/hashes differ from the saved run")
    if args.output.exists() and any(args.output.iterdir()) and not provenance.exists():
        parser.error("cannot resume a nonempty directory without bound inputs")
    args.output.mkdir(parents=True, exist_ok=True)
    provenance.write_text(json.dumps(inputs, indent=2) + "\n")
    inputs_sha256 = digest(provenance)
    receipts_path = args.output / "artifacts.json"
    receipts = json.loads(receipts_path.read_text()) if receipts_path.exists() else {}
    pending = []
    for condition in args.conditions:
        for query in queries:
            address = f"{condition}/{query.query_id}.json"
            target = args.output / address
            if target.exists():
                try:
                    if digest(target) != receipts.get(address):
                        raise ValueError("cached artifact checksum mismatch or missing receipt")
                    payload = json.loads(target.read_text())
                    validate_cached(
                        payload, query=query, condition=condition, inputs_sha256=inputs_sha256
                    )
                    log = args.output / condition / payload["log_file"]
                    if log.parent != target.parent or digest(log) != payload["log_sha256"]:
                        raise ValueError("cached execution log checksum mismatch")
                except (ValueError, KeyError, OSError) as exc:
                    parser.error(str(exc))
                print(f"cached {condition} {query.query_id}", flush=True)
            else:
                pending.append((condition, query))
    if not pending:
        return
    if args.backend == "mlx":
        generator = MLXGenerator(args.model_path, model_id=args.model, revision=args.revision)
    elif args.backend == "claude":
        generator = AnthropicGenerator(model=args.model, revision=args.revision)
    else:
        generator = ChatCompletionsGenerator(
            base_url=args.base_url,
            model=args.model,
            backend=args.backend,
            allow_remote=args.allow_remote,
            revision=args.revision,
        )
    first_stage = (
        WorkerRetriever(
            python=args.retrieval_python,
            corpus=args.corpus,
            aliases=args.aliases,
            settings=settings,
        )
        if args.retrieval_python
        else build_retriever(
            list(BM25Retriever.from_jsonl(args.corpus).passages),
            aliases=Aliases.load(args.aliases),
            **{**settings, "dense_index": args.dense_index if dense else None},
        )
    )
    reranked = (
        RerankingRetriever(
            first_stage, scorer=WorkerScorer(args.reranker_python, args.reranker_revision)
        )
        if args.reranker_python
        else None
    )
    pipeline = Pipeline(
        generator=generator,
        retriever=first_stage,
        series=SeriesStore.from_directory(args.series),
        reranked_retriever=reranked,
        aliases=load_aliases(args.aliases),
        require_confirmed_anchors=args.require_confirmed_anchors,
    )
    failures = []
    try:
        for condition, query in pending:
            directory = args.output / condition
            directory.mkdir(exist_ok=True)
            target = directory / f"{query.query_id}.json"
            try:
                log_path = directory / f"{query.query_id}-{uuid.uuid4().hex[:8]}.jsonl"
                result = pipeline.run(
                    query, condition=condition, run_id=uuid.uuid4().hex, log_path=log_path
                )
                result.update(
                    inputs_sha256=inputs_sha256, log_file=log_path.name, log_sha256=digest(log_path)
                )
                target.write_text(json.dumps(result, indent=2) + "\n")
                receipts[str(target.relative_to(args.output))] = digest(target)
                receipts_path.write_text(json.dumps(receipts, indent=2) + "\n")
                print(
                    f"completed {condition} {query.query_id}: {len(result['graph']['edges'])} edges, {result['tool_calls']} tool calls",
                    flush=True,
                )
            except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
                failures.append(
                    {"condition": condition, "query_id": query.query_id, "error": str(exc)}
                )
                print(f"failed {condition} {query.query_id}: {exc}", flush=True)
    finally:
        if isinstance(first_stage, WorkerRetriever):
            first_stage.close()
    (args.output / "failures.json").write_text(json.dumps(failures, indent=2) + "\n")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
