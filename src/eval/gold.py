"""B4 - the reviewer-identified evidence graphs, and what makes one valid.

A gold graph is a `Graph` whose edges a human reviewer identified from the
corpus, each `source_asserted` and carrying a verbatim span. Every Phase 3
number is measured against these, so a gold graph that is wrong is worse than
one that is missing: reference-edge recall, UER and strength inflation all
inherit the error silently.

This module validates them. It deliberately **cannot** write one. The spans
have to be read out of the corpus by a person; a generated gold standard would
measure the generator.

Two levels of checking:

`validate_gold_graph`
    Structure only, and needs no corpus: every edge is source_asserted with a
    span and a dated source, nothing is published after the as-of date, the
    anchor matches the query, and the edge count is in the reviewed range.

`check_against_corpus`
    Adds the B6 rule layer, so each span is confirmed verbatim in the passage
    it cites. Needs `data/processed/articles.jsonl`, which is not in git.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path as FsPath

from pydantic import BaseModel, ConfigDict, Field

from schema import Edge, Graph, Passage
from verify import check_edge, load_aliases

__all__ = [
    "MAX_EDGES",
    "MIN_EDGES",
    "GoldIssue",
    "GoldReport",
    "check_against_corpus",
    "gold_path",
    "load_gold_graph",
    "missing_gold_graphs",
    "validate_gold_graph",
]

#: The proposal asks for "about 4-6 source-asserted edges" per reviewed query.
MIN_EDGES = 4
MAX_EDGES = 6

GOLD_DIR = FsPath("data/eval/gold/dev")


class GoldIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query_id: str
    edge_id: str | None = None
    problem: str


class GoldReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    query_id: str
    edge_count: int
    issues: tuple[GoldIssue, ...] = ()
    corpus_checked: bool = Field(
        default=False,
        description="True when spans were confirmed against the corpus, not just structure.",
    )

    @property
    def ok(self) -> bool:
        return not self.issues


def gold_path(query_id: str, root: FsPath | str = GOLD_DIR) -> FsPath:
    return FsPath(root) / f"{query_id}.json"


def load_gold_graph(query_id: str, root: FsPath | str = GOLD_DIR) -> Graph:
    path = gold_path(query_id, root)
    return Graph.model_validate_json(path.read_text(encoding="utf-8"))


def missing_gold_graphs(query_ids: Iterable[str], root: FsPath | str = GOLD_DIR) -> tuple[str, ...]:
    """Which reviewed queries still have no gold graph. B4 is done when empty."""
    return tuple(q for q in query_ids if not gold_path(q, root).is_file())


def validate_gold_graph(graph: Graph, *, expect_query_id: str | None = None) -> GoldReport:
    """Structural checks. No corpus needed, so these run anywhere."""
    issues: list[GoldIssue] = []

    def fail(problem: str, edge_id: str | None = None) -> None:
        issues.append(GoldIssue(query_id=graph.query_id, edge_id=edge_id, problem=problem))

    if expect_query_id is not None and graph.query_id != expect_query_id:
        fail(f"graph is labelled {graph.query_id!r} but was loaded for {expect_query_id!r}")

    if not MIN_EDGES <= len(graph.edges) <= MAX_EDGES:
        fail(
            f"a reviewed graph carries {MIN_EDGES}-{MAX_EDGES} edges; this one has "
            f"{len(graph.edges)}"
        )

    for edge in graph.edges:
        _check_edge_shape(edge, graph, fail)

    if graph.edges and not any(
        edge.src_var == graph.anchor.var or edge.dst_var == graph.anchor.var for edge in graph.edges
    ):
        fail("no edge touches the anchor, so the graph does not answer its query")

    return GoldReport(query_id=graph.query_id, edge_count=len(graph.edges), issues=tuple(issues))


def _check_edge_shape(edge: Edge, graph: Graph, fail) -> None:
    if not edge.is_asserted:
        fail(
            "a gold edge records what a source states, so it must be source_asserted; "
            f"this one is {edge.provenance}",
            edge.edge_id,
        )
        return
    if not edge.evidence_span or not edge.evidence_span.strip():
        fail("source_asserted with no verbatim evidence span", edge.edge_id)
    if not edge.evidence_doc_id or not edge.evidence_passage_id:
        fail("evidence span with no document or passage to find it in", edge.edge_id)
    if edge.evidence_published_at is None:
        fail("evidence with no publication date, so as-of cannot be checked", edge.edge_id)
    elif edge.evidence_published_at.date() > graph.as_of:
        fail(
            f"evidence published {edge.evidence_published_at.date()}, after the "
            f"as-of date {graph.as_of}",
            edge.edge_id,
        )


def check_against_corpus(
    graph: Graph,
    passages: Sequence[Passage],
    *,
    aliases=None,
) -> GoldReport:
    """Structure, plus the B6 rule layer on every edge. Needs the corpus."""
    structural = validate_gold_graph(graph)
    issues = list(structural.issues)
    table = aliases if aliases is not None else load_aliases()
    by_id = {p.passage_id: p for p in passages}
    corpus_doc_ids = {p.doc_id for p in passages}

    for edge in graph.edges:
        passage = by_id.get(edge.evidence_passage_id or "")
        if passage is None:
            issues.append(
                GoldIssue(
                    query_id=graph.query_id,
                    edge_id=edge.edge_id,
                    problem=f"cited passage {edge.evidence_passage_id!r} is not in the corpus",
                )
            )
            continue
        # Strict, single-passage mention scope: this branch predates D-17's
        # two-paragraph window. Once b/mention-window merges, pass
        # `document=preceding_window(passage, passages)` here, or gold edges
        # whose relation spans a paragraph break will be reported as failures.
        report = check_edge(
            edge,
            passage,
            as_of=graph.as_of,
            corpus_doc_ids=corpus_doc_ids,
            aliases=table,
        )
        if not report.passed:
            issues.append(
                GoldIssue(
                    query_id=graph.query_id,
                    edge_id=edge.edge_id,
                    problem=f"fails the rule layer: {report.reason()}",
                )
            )

    return GoldReport(
        query_id=graph.query_id,
        edge_count=len(graph.edges),
        issues=tuple(issues),
        corpus_checked=True,
    )
