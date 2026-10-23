"""Run the same date-safe pipeline for selected conditions and development queries."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import uuid
from pathlib import Path

from corpus.series import SeriesStore
from llm.generate import ChatCompletionsGenerator, MLXGenerator
from retrieval.bm25 import Aliases, BM25Retriever
from retrieval.pilot import PlainBM25
from retrieval.rerank import RerankingRetriever
from schema import Condition

from .pipeline import Pipeline, Query


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
    parser.add_argument("--backend", choices=["mlx", "llama.cpp", "vllm", "api"], default="mlx")
    parser.add_argument("--model-path", type=Path, default=Path("data/raw/generator/qwen3-8b-4bit"))
    parser.add_argument("--model", default="mlx-community/Qwen3-8B-4bit")
    parser.add_argument("--revision", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--reranker-python")
    parser.add_argument("--reranker-revision", default="953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e")
    parser.add_argument("--output", type=Path, default=Path("runs/development"))
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
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
    args.output.mkdir(parents=True, exist_ok=args.resume)

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    inputs = {
        "protocol": "prose baselines, mechanically extracted graphs; independent correction pending",
        "pipeline_sha256": hashlib.sha256(
            b"".join(
                str(path.relative_to(Path("src"))).encode() + path.read_bytes()
                for directory in ("agent", "conditions", "extract", "llm", "tools", "verify")
                for path in sorted((Path("src") / directory).glob("*.py"))
            )
        ).hexdigest(),
        "queries_sha256": digest(args.queries),
        "corpus_sha256": digest(args.corpus),
        "aliases_sha256": digest(args.aliases),
        "model": args.model,
        "revision": args.revision,
        "backend": args.backend,
        "conditions": args.conditions,
        "reranker_revision": args.reranker_revision,
        "first_stage": "plain BM25 (development; D-02 unresolved)",
        "series_sha256": {p.name: digest(p) for p in sorted(args.series.glob("*.csv"))},
        "status": "development_unreviewed; not a frozen experiment",
    }
    provenance = args.output / "inputs.json"
    if provenance.exists() and json.loads(provenance.read_text()) != inputs:
        parser.error("resume input settings/hashes differ from the saved run")
    provenance.write_text(json.dumps(inputs, indent=2) + "\n")
    if args.backend == "mlx":
        generator = MLXGenerator(args.model_path, model_id=args.model, revision=args.revision)
    else:
        if not args.base_url:
            parser.error("HTTP backends require --base-url")
        generator = ChatCompletionsGenerator(
            base_url=args.base_url,
            model=args.model,
            backend=args.backend,
            allow_remote=args.allow_remote,
        )
    first_stage = PlainBM25(
        BM25Retriever.from_jsonl(args.corpus, aliases=Aliases.load(args.aliases))
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
    )
    failures = []
    for condition in args.conditions:
        directory = args.output / condition
        directory.mkdir(exist_ok=True)
        for query in queries:
            target = directory / f"{query.query_id}.json"
            if target.exists() and args.resume:
                from schema import Graph

                Graph.model_validate(json.loads(target.read_text())["graph"])
                print(f"cached {condition} {query.query_id}", flush=True)
                continue
            try:
                result = pipeline.run(
                    query,
                    condition=condition,
                    run_id=uuid.uuid4().hex,
                    log_path=directory / f"{query.query_id}-{uuid.uuid4().hex[:8]}.jsonl",
                )
                target.write_text(json.dumps(result, indent=2) + "\n")
                print(
                    f"completed {condition} {query.query_id}: {len(result['graph']['edges'])} edges, {result['tool_calls']} tool calls",
                    flush=True,
                )
            except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
                failures.append(
                    {"condition": condition, "query_id": query.query_id, "error": str(exc)}
                )
                print(f"failed {condition} {query.query_id}: {exc}", flush=True)
    (args.output / "failures.json").write_text(json.dumps(failures, indent=2) + "\n")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
