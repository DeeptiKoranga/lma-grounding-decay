"""Rebuild BFS hop labels and bounded simple paths after every graph mutation."""

from __future__ import annotations

from collections import deque

from schema import Anchor, Edge, Graph, GraphNode, Path, weakest


def rebuild(
    *, query_id: str, anchor: Anchor, as_of, edges: list[Edge], condition=None, max_hops=4
) -> Graph:
    if not 1 <= max_hops <= 10:
        raise ValueError("path depth must be between 1 and 10")
    adjacency: dict[str, list[Edge]] = {}
    for edge in edges:
        edge = Edge.model_validate(edge.model_dump())
        adjacency.setdefault(edge.src_var, []).append(edge)
    distance, queue = {anchor.var: 0}, deque([anchor.var])
    while queue:
        src = queue.popleft()
        for edge in adjacency.get(src, []):
            if edge.dst_var not in distance:
                distance[edge.dst_var] = distance[src] + 1
                queue.append(edge.dst_var)
    retained = [
        edge.model_copy(update={"hop": distance[edge.src_var] + 1})
        for edge in edges
        if edge.src_var in distance and distance[edge.src_var] < max_hops
    ]
    nodes = {
        anchor.var: GraphNode(
            var=anchor.var,
            direction=anchor.direction,
            is_anchor=True,
            confirmed_by_series=anchor.confirmed_by_series,
            series_id=anchor.series_id,
        )
    }
    adjacency = {}
    for edge in retained:
        nodes.setdefault(edge.dst_var, GraphNode(var=edge.dst_var, direction=edge.direction))
        adjacency.setdefault(edge.src_var, []).append(edge)
    paths = []

    def walk(src, chain, visited):
        successors = [edge for edge in adjacency.get(src, []) if edge.dst_var not in visited]
        if chain and (not successors or len(chain) >= max_hops):
            paths.append(
                Path(
                    path_id=f"path-{len(paths)+1}",
                    edge_ids=[e.edge_id for e in chain],
                    depth=len(chain),
                    weakest_strength=weakest([e.strength for e in chain]),
                    fully_sourced=all(e.is_asserted for e in chain),
                )
            )
            return
        for edge in successors:
            walk(edge.dst_var, [*chain, edge], visited | {edge.dst_var})

    walk(anchor.var, [], {anchor.var})
    return Graph(
        query_id=query_id,
        anchor=anchor,
        as_of=as_of,
        nodes=list(nodes.values()),
        edges=retained,
        paths=paths,
        condition=condition,
    )
