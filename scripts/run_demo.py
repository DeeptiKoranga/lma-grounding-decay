"""Exercise all seven conditions on a synthetic case with scripted responses."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from scripts.build_graph_explorer import build

from conditions.pipeline import Pipeline, Query
from conditions.provenance import write_json
from corpus.series import Observation, SeriesStore
from eval.safety import inspect_graph
from llm.generate import Completion
from retrieval.bm25 import Aliases, BM25Retriever
from retrieval.rerank import RerankingRetriever
from schema import Condition, Graph, Passage, iter_run_log
from verify import load_aliases

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures"
ALIASES = ROOT / "data/aliases.yaml"


class FixtureModel:
    """Supply known responses to the real extraction and verification interfaces."""

    def __init__(self, edges):
        self.edges = edges

    def generate(self, prompt, *, max_tokens=1500):
        instruction, _, payload = prompt.partition("\n")
        if instruction.startswith("Judge only"):
            claim = json.loads(payload)
            edge = next(
                (
                    edge
                    for edge in self.edges
                    if (edge.src_var, edge.dst_var) == (claim["src_var"], claim["dst_var"])
                    and edge.evidence_span
                    and edge.evidence_span in claim["span"]
                ),
                None,
            )
            reply = json.dumps(
                {
                    "verdict": "supported" if edge else "unsupported",
                    "direction": claim["claimed_direction"],
                    "strength": "direct" if edge and edge.hop == 1 else "conditional",
                    "reason": "scripted fixture judgment",
                }
            )
        elif instruction.startswith("Answer the question"):
            passage_ids = {p["passage_id"] for p in json.loads(payload)["passages"]}
            sentences = [
                "Higher Brent prices raised the Indian basket price",
                "A higher Indian basket price may widen the oil import bill",
                "A higher import bill could put pressure on the rupee",
            ]
            reply = (
                ". ".join(
                    (
                        f"{sentence} [{edge.evidence_passage_id}]"
                        if edge.evidence_passage_id in passage_ids
                        else sentence
                    )
                    for sentence, edge in zip(sentences, self.edges, strict=True)
                )
                + "."
            )
        else:
            passages = {p["passage_id"] for p in json.loads(payload)["passages"]}
            candidates = []
            for edge in self.edges:
                cited = edge.evidence_passage_id in passages
                candidates.append(
                    {
                        "src_var": edge.src_var,
                        "dst_var": edge.dst_var,
                        "direction": edge.direction,
                        "strength": edge.strength,
                        "provenance": "source_asserted" if cited else "model_inferred",
                        "evidence_passage_id": edge.evidence_passage_id if cited else None,
                        "evidence_span": edge.evidence_span if cited else None,
                    }
                )
            reply = json.dumps({"edges": candidates})
        return Completion(reply, "scripted-fixture", "fixture", 0, 0, 0)


class FixtureReranker:
    """Provide deterministic ranking scores without a cross-encoder download."""

    def __init__(self):
        self.calls = 0

    def score(self, query, texts):
        self.calls += 1
        return [float("import bill" in text.casefold()) for text in texts]


def run(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    passages = [
        Passage.model_validate_json(line)
        for line in (FIXTURES / "passages.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    seed = Graph.model_validate_json(
        (FIXTURES / "graph_brent_hormuz.json").read_text(encoding="utf-8")
    )
    query = Query(
        query_id="synthetic-oil-effects",
        query="Brent crude, Indian basket price, import bill and rupee. What effects were reported?",
        anchor=seed.anchor,
        as_of=seed.as_of,
        anchor_threshold={"episode_id": "synthetic-oil", "comparison": "at_or_above", "value": 100},
    )
    series = SeriesStore(
        {
            "brent_usd_bbl": [
                Observation(
                    on=date(2026, 3, 12),
                    value=102,
                    available_on=date(2026, 3, 12),
                    source_url="https://example.org/synthetic-series",
                    unit="USD per barrel",
                )
            ]
        }
    )
    retriever = BM25Retriever(passages, aliases=Aliases.load(ALIASES))
    scorer = FixtureReranker()
    pipeline = Pipeline(
        generator=FixtureModel(seed.edges[:3]),
        retriever=retriever,
        reranked_retriever=RerankingRetriever(retriever, scorer=scorer),
        series=series,
        aliases=load_aliases(ALIASES),
        require_confirmed_anchors=True,
    )
    artifacts, summary = [], {}
    for condition in Condition:
        log = output / f"{condition}.jsonl"
        result = pipeline.run(query, condition=condition, run_id=f"demo-{condition}", log_path=log)
        graph = Graph.model_validate(result["graph"])
        graph.notes = "Synthetic demonstration using scripted model and reranker responses."
        safety = inspect_graph(graph, passages)
        events = iter_run_log(log)
        for event in events:
            if (
                event.event == "tool_result"
                and event.result.tool in ("search_corpus", "counter_search")
                and any(not passage.visible_at(query.as_of) for passage in event.result.passages)
            ):
                raise RuntimeError("demo retrieval violated the as-of boundary")
        if not safety["passed"] or not result["anchor_check"]["confirmed"]:
            raise RuntimeError(f"{condition} demo output failed structural validation")
        path = output / f"{condition}.json"
        write_json(path, {**result, "graph": graph.model_dump(mode="json")})
        artifacts.append(path)
        summary[str(condition)] = {
            "asserted_edges": sum(edge.is_asserted for edge in graph.edges),
            "inferred_edges": sum(not edge.is_asserted for edge in graph.edges),
            "tool_calls": result["tool_calls"],
            "stop_reason": result["stop_reason"],
        }

    full = summary["M"]
    if not full["asserted_edges"] or not full["inferred_edges"] or scorer.calls != 1:
        raise RuntimeError("demo did not exercise verification, inference and the reranker")
    build((), output / "graph_explorer.html", run_artifacts=artifacts)
    write_json(
        output / "summary.json",
        {
            "scope": "synthetic scripted engineering demo",
            "fixture_reranker_calls": scorer.calls,
            "conditions": summary,
        },
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("runs/demo"))
    args = parser.parse_args()
    try:
        summary = run(args.output)
    except FileExistsError:
        parser.error("choose a new --output directory")
    print(json.dumps(summary, indent=2))
    print(f"Open {args.output / 'graph_explorer.html'} in a browser.")


if __name__ == "__main__":
    main()
