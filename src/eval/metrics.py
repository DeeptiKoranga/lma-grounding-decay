"""Proposal metrics, query-macro averaged; missing judgments are never support labels."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from schema import Graph, Strength, strength_rank


@dataclass(frozen=True)
class SupportJudgment:
    supported: bool
    evidence_strength: Strength | None = None

    def __post_init__(self):
        if self.supported and self.evidence_strength is None:
            raise ValueError("supported established edges require an evidence strength judgment")


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def signature(edge):
    return edge.src_var, edge.dst_var, str(edge.direction)


def score_graph(
    graph: Graph,
    *,
    established: set[str],
    judgments: dict[str, SupportJudgment],
    reference: Graph | None = None,
) -> dict:
    graph = Graph.model_validate(graph.model_dump())
    edges = {edge.edge_id: edge for edge in graph.edges}
    if set(judgments) != set(edges) or not established <= set(edges):
        raise ValueError(
            "support judgments must cover exactly the graph edges; established ids must exist"
        )
    output = {}
    for bucket in ("overall", "1", "2", "3+"):
        selected = [
            edge
            for edge in graph.edges
            if bucket == "overall" or (str(edge.hop) == bucket if edge.hop < 3 else bucket == "3+")
        ]
        asserted = [e for e in selected if e.edge_id in established]
        supported = [e for e in asserted if judgments[e.edge_id].supported]
        inflated = [
            e
            for e in supported
            if strength_rank(e.strength) < strength_rank(judgments[e.edge_id].evidence_strength)
        ]
        recovered = {signature(e) for e in supported}
        refs = (
            {
                signature(e)
                for e in reference.edges
                if bucket == "overall" or (str(e.hop) == bucket if e.hop < 3 else bucket == "3+")
            }
            if reference is not None
            else None
        )
        paths = [
            path
            for path in graph.paths
            if bucket == "overall"
            or (str(path.depth) == bucket if path.depth < 3 else bucket == "3+")
        ]
        valid_paths = [
            path
            for path in paths
            if all(
                eid in established
                and judgments[eid].supported
                and strength_rank(edges[eid].strength)
                >= strength_rank(judgments[eid].evidence_strength)
                for eid in path.edge_ids
            )
        ]
        output[bucket] = {
            "edges": len(selected),
            "established_edges": len(asserted),
            "supported_established_edges": len(supported),
            "uer": ratio(len(asserted) - len(supported), len(asserted)),
            "strength_inflation": ratio(len(inflated), len(supported)),
            "reference_edge_recall": (
                ratio(len(recovered & refs), len(refs)) if refs is not None else None
            ),
            "provenance_accuracy": ratio(
                sum(e.is_asserted == judgments[e.edge_id].supported for e in selected),
                len(selected),
            ),
            "strict_path_validity": ratio(len(valid_paths), len(paths)),
        }
    return output


def aggregate(queries: list[dict]) -> dict:
    if not queries:
        raise ValueError("cannot aggregate an empty evaluation")
    metrics = (
        "uer",
        "strength_inflation",
        "reference_edge_recall",
        "provenance_accuracy",
        "strict_path_validity",
    )
    return {
        bucket: {
            metric: {
                "mean": (
                    mean(values)
                    if (
                        values := [
                            q[bucket][metric] for q in queries if q[bucket][metric] is not None
                        ]
                    )
                    else None
                ),
                "queries_with_denominator": len(values),
                "queries_without_denominator": len(queries) - len(values),
            }
            for metric in metrics
        }
        for bucket in ("overall", "1", "2", "3+")
    }
