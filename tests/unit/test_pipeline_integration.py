"""Exercise the integrated conditions against fixtures, including adversarial tool calls."""

import json
from datetime import date
from pathlib import Path

import pytest

from conditions.pipeline import Pipeline, Query
from corpus.series import SeriesStore
from llm.generate import Completion
from retrieval.bm25 import Aliases, BM25Retriever, Hit
from schema import Anchor, Condition, Edge, Provenance, iter_run_log
from tools.runtime import ToolRuntime
from verify.llm_verifier import Verifier
from verify.paths import rebuild

ROOT = Path(__file__).parents[2]


class FixtureGenerator:
    def generate(self, prompt, *, max_tokens=1500):
        if prompt.startswith("Judge only"):
            result = {
                "verdict": "supported",
                "direction": "up",
                "strength": "direct",
                "reason": "fixture source states this link",
            }
        else:
            result = {
                "edges": [
                    {
                        "src_var": "BRENT",
                        "dst_var": "INDIAN_BASKET",
                        "direction": "up",
                        "strength": "direct",
                        "provenance": "source_asserted",
                        "evidence_passage_id": "bl-2026-03-12-brent100#p1",
                        "evidence_span": "The Indian basket of crude rose to $98.4 a barrel due to the surge in Brent",
                    }
                ]
            }
        return Completion(json.dumps(result), "fixture-only", "api", 1, 1, 0)


@pytest.fixture
def query():
    return Query(
        query_id="integration",
        query="Brent Indian basket crude",
        as_of=date(2026, 3, 20),
        anchor=Anchor(
            var="BRENT",
            direction="up",
            event="Synthetic fixture oil move",
            event_date=date(2026, 3, 12),
        ),
    )


@pytest.fixture
def retriever(passages):
    return BM25Retriever(passages, aliases=Aliases.load(ROOT / "data/aliases.yaml"))


def test_all_seven_conditions_emit_valid_logged_graphs_with_one_shared_backend(
    query, retriever, tmp_path
):
    generator = FixtureGenerator()
    pipeline = Pipeline(
        generator=generator,
        retriever=retriever,
        series=SeriesStore({}),
        reranked_retriever=retriever,
    )
    results = {}
    for condition in Condition:
        path = tmp_path / f"{condition}.jsonl"
        result = pipeline.run(query, condition=condition, run_id="fixture", log_path=path)
        results[condition] = result
        log = iter_run_log(path)
        assert log[-1].event == "stop"
        assert result["tool_calls"] <= 12
        assert result["status"] == "development_unreviewed"
        assert not result["graph"]["anchor"]["confirmed_by_series"]
        assert all(p.event != "model_call" or p.prompt_tokens == 1 for p in log)
        assert not any(
            p.event == "model_call" and p.purpose == "verify" for p in log
        ) or condition in {Condition.M, Condition.A_NOLOOP}
    assert results[Condition.B0]["graph"]["edges"][0]["provenance"] == "model_inferred"
    assert results[Condition.B0]["established_edge_ids"] == ["edge-1"]
    for condition in (Condition.M, Condition.A_NOLOOP):
        edge = results[condition]["graph"]["edges"][0]
        assert edge["verified_by"] == "rules+llm" and edge["provenance"] == "source_asserted"


def runtime(query, retriever, *, budget=12):
    graph = rebuild(query_id=query.query_id, anchor=query.anchor, as_of=query.as_of, edges=[])
    return ToolRuntime(graph=graph, retriever=retriever, series=SeriesStore({}), budget=budget)


def test_malformed_code_fence_is_logged_and_retried(query, retriever, tmp_path):
    class MalformedFirst(FixtureGenerator):
        calls = 0

        def generate(self, prompt, *, max_tokens=1500):
            self.calls += 1
            if self.calls == 1:
                return Completion("```json```", "fixture-only", "api", 1, 1, 0)
            return super().generate(prompt, max_tokens=max_tokens)

    generator = MalformedFirst()
    path = tmp_path / "retry.jsonl"
    result = Pipeline(generator=generator, retriever=retriever, series=SeriesStore({})).run(
        query, condition="B2", run_id="fence-retry", log_path=path
    )
    calls = [row for row in iter_run_log(path) if row.event == "model_call"]
    assert generator.calls == 2 and result["graph"]["edges"]
    assert [row.json_valid for row in calls] == [False, True]
    assert calls[0].completion == "```json```"


def test_cutoff_cannot_be_widened_and_backend_cannot_forge_passages(query, retriever):
    tools = runtime(query, retriever)
    failed = tools.call("search_corpus", query="oil", as_of=date(2026, 9, 30))
    assert failed.error.kind == "after_as_of" and not tools.seen
    passage = retriever.passages[0]
    impostor = passage.model_copy(update={"title": "forged"})
    retriever.search = lambda **_: [Hit(impostor, 1)]
    result = tools.call("search_corpus", query="oil", as_of=query.as_of)
    assert result.error.kind == "backend_error" and not tools.seen


def test_budget_is_structural_even_when_every_tool_fails(query, retriever):
    tools = runtime(query, retriever, budget=2)
    for _ in range(3):
        result = tools.call(
            "get_series",
            series_id="absent",
            start=date(2026, 3, 1),
            end=date(2026, 3, 10),
            as_of=query.as_of,
        )
    assert result.error.kind == "budget_exhausted" and tools.calls_used == 2
    with pytest.raises(ValueError):
        runtime(query, retriever, budget=13)


def test_rules_passing_never_promotes_without_a_fresh_semantic_judgment(query, retriever):
    class Opposite(FixtureGenerator):
        def generate(self, *args, **kwargs):
            return Completion(
                json.dumps(
                    {
                        "verdict": "supported",
                        "direction": "down",
                        "strength": "direct",
                        "reason": "opposite destination",
                    }
                ),
                "fixture",
                "api",
                0,
                0,
                0,
            )

    edge = Edge(
        edge_id="e",
        src_var="BRENT",
        dst_var="INDIAN_BASKET",
        direction="up",
        strength="direct",
        provenance="model_inferred",
        hop=1,
    )
    passage = next(p for p in retriever.passages if p.passage_id == "bl-2026-03-12-brent100#p1")
    verifier = Verifier(Opposite(), list(retriever.passages))
    result = verifier.verify(
        edge, passage=passage, span=passage.text, as_of=query.as_of, call_id="v"
    )
    assert result.verdict == "contradicted" and result.provenance == Provenance.MODEL_INFERRED
    forged = passage.model_copy(update={"title": "forged"})
    assert (
        verifier.verify(
            edge, passage=forged, span=forged.text, as_of=query.as_of, call_id="v2"
        ).verdict
        == "out_of_corpus"
    )


def test_rejected_verification_is_saved_as_candidate_evidence(query, retriever):
    class Opposite(FixtureGenerator):
        def generate(self, *args, **kwargs):
            return Completion(
                json.dumps(
                    {
                        "verdict": "supported",
                        "direction": "down",
                        "strength": "direct",
                        "reason": "opposite direction",
                    }
                ),
                "fixture",
                "api",
                0,
                0,
                0,
            )

    edge = Edge(
        edge_id="e",
        src_var="BRENT",
        dst_var="INDIAN_BASKET",
        direction="up",
        strength="direct",
        provenance="model_inferred",
        hop=1,
    )

    graph = rebuild(
        query_id=query.query_id,
        anchor=query.anchor,
        as_of=query.as_of,
        edges=[edge],
    )

    verifier = Verifier(Opposite(), list(retriever.passages))

    tools = ToolRuntime(
        graph=graph,
        retriever=retriever,
        series=SeriesStore({}),
        verifier=verifier,
    )

    passage = next(p for p in retriever.passages if p.passage_id == "bl-2026-03-12-brent100#p1")
    tools.seen.add(passage.passage_id)

    result = tools.call(
        "verify_edge",
        edge_id="e",
        passage_ids=[passage.passage_id],
        as_of=query.as_of,
    )

    assert result.verdict.value == "contradicted"

    saved = tools.graph.edges[0]
    assert saved.provenance == Provenance.MODEL_INFERRED
    assert saved.evidence_span is None
    assert len(saved.candidate_evidence) == 1
    assert saved.candidate_evidence[0].passage_id == passage.passage_id
    assert saved.candidate_evidence[0].verdict.value == "contradicted"


def test_graph_mutations_recompute_hops_paths_and_protect_verified_labels(query, retriever):
    tools = runtime(query, retriever)
    first = Edge(
        edge_id="e1",
        src_var="BRENT",
        dst_var="INDIAN_BASKET",
        direction="up",
        strength="direct",
        provenance="model_inferred",
        hop=1,
    )
    second = Edge(
        edge_id="e2",
        src_var="INDIAN_BASKET",
        dst_var="IMPORT_BILL",
        direction="up",
        strength="conditional",
        provenance="model_inferred",
        hop=1,
    )
    for edge in (first, second):
        assert tools.call("update_graph", op="add_edge", edge=edge).applied
    assert tools.graph.edges[1].hop == 2
    assert tools.graph.paths[0].weakest_strength == "conditional"
    refused = tools.call(
        "update_graph", op="relabel_edge", edge_id="e1", provenance="source_asserted"
    )
    assert not refused.ok
    assert tools.call("update_graph", op="drop_edge", edge_id="e1").applied
    assert tools.graph.edges == [] and tools.graph.paths == []


def test_schema_can_round_trip_added_nodes_and_bad_stop_conditions(query, retriever):
    tools = runtime(query, retriever)
    result = tools.call(
        "update_graph", op="add_node", node={"var": "CPI_HEADLINE", "direction": "up"}
    )
    assert result.applied and len(tools.graph.nodes) == 2
    assert not tools.call("stop", reason="two_searches_added_nothing").ok
    assert not tools.call("stop", reason="budget_exhausted").ok


def test_rebuilding_a_cycle_is_bounded_and_labels_weakest_link(query):
    edges = [
        Edge(
            edge_id="a",
            src_var="BRENT",
            dst_var="INR_USD",
            direction="up",
            strength="direct",
            provenance="model_inferred",
            hop=1,
        ),
        Edge(
            edge_id="b",
            src_var="INR_USD",
            dst_var="BRENT",
            direction="up",
            strength="correlational",
            provenance="model_inferred",
            hop=2,
        ),
    ]
    graph = rebuild(query_id=query.query_id, anchor=query.anchor, as_of=query.as_of, edges=edges)
    assert len(graph.paths) == 1 and graph.paths[0].depth == 1


def test_repair_stops_on_two_empty_searches_without_claiming_unused_budget_exhausted(
    query, retriever
):
    from agent.controller import repair

    tools = runtime(query, retriever)
    tools.require_verification = False
    tools.set_edges(
        [
            Edge(
                edge_id="e1",
                src_var="BRENT",
                dst_var="IMPORT_BILL",
                direction="up",
                strength="conditional",
                provenance="model_inferred",
                hop=1,
            )
        ]
    )
    retriever.search = lambda **_: []
    reason = repair(tools, loop=True, generate_repair=lambda *args: None)
    assert reason == "two_searches_added_nothing"
    assert tools.calls_used == 3 and tools.remaining == 9 and tools.stopped


def test_failed_verification_retries_are_bounded_by_the_actual_call_budget(query, retriever):
    from agent.controller import repair

    tools = runtime(query, retriever, budget=4)
    tools.set_edges(
        [
            Edge(
                edge_id="e1",
                src_var="BRENT",
                dst_var="IMPORT_BILL",
                direction="up",
                strength="conditional",
                provenance="model_inferred",
                hop=1,
            )
        ]
    )
    # No verifier configured: the real tool returns a typed backend error.
    assert repair(tools, loop=False) == "budget_exhausted"
    assert tools.calls_used == 4 and tools.remaining == 0
