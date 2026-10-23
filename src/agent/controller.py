"""Bounded edge-priority repair, with three state-derived stop conditions."""

from __future__ import annotations

from schema import Provenance


def priority(edges):
    """Resolve shallow edges first: errors there affect every downstream path."""
    return sorted(edges, key=lambda edge: (edge.hop, edge.edge_id))


def repair(runtime, *, loop: bool, generate_repair=None):
    for edge in priority(list(runtime.graph.edges)):
        if runtime.remaining < 2 or runtime.empty_searches >= 2:
            break
        if edge.is_asserted:
            continue
        ids = [pid for (eid, pid) in runtime.spans if eid == edge.edge_id and pid in runtime.seen]
        if not ids:
            ids = [
                pid
                for pid in sorted(runtime.seen)
                if all(
                    runtime.retriever.aliases.mentions(runtime.corpus[pid].text, var)
                    for var in (edge.src_var, edge.dst_var)
                )
            ][:2]
        if runtime.require_verification:
            result = runtime.call(
                "verify_edge", edge_id=edge.edge_id, passage_ids=ids[:2], as_of=runtime.graph.as_of
            )
            if not result.ok:
                continue
            if result.provenance != Provenance.SOURCE_ASSERTED and loop and runtime.remaining >= 4:
                result_search = runtime.call(
                    "search_corpus",
                    query=f"{edge.src_var.replace('_', ' ')} {edge.dst_var.replace('_', ' ')} cause effect",
                    k=3,
                    as_of=runtime.graph.as_of,
                    must_mention=[edge.src_var, edge.dst_var],
                )
                if result_search.ok:
                    result = runtime.call(
                        "verify_edge",
                        edge_id=edge.edge_id,
                        passage_ids=[p.passage_id for p in result_search.passages][:2],
                        as_of=runtime.graph.as_of,
                    )
            runtime.call(
                "update_graph",
                op="relabel_edge",
                edge_id=edge.edge_id,
                provenance=result.provenance or Provenance.MODEL_INFERRED,
                strength=(
                    result.strength if result.provenance == Provenance.SOURCE_ASSERTED else None
                ),
                reason="independent rule and semantic verification",
            )
        elif loop and generate_repair is not None:
            searched = runtime.call(
                "search_corpus",
                query=f"{edge.src_var.replace('_', ' ')} {edge.dst_var.replace('_', ' ')} cause effect",
                k=3,
                as_of=runtime.graph.as_of,
                must_mention=[edge.src_var, edge.dst_var],
            )
            if searched.ok and searched.passages:
                replacement = generate_repair(edge, searched.passages)
                if replacement is not None:
                    runtime.call(
                        "update_graph",
                        op="relabel_edge",
                        edge_id=edge.edge_id,
                        edge=replacement,
                        provenance=replacement.provenance,
                        reason="generator self-label; no independent verifier in this ablation",
                    )
    if runtime.empty_searches >= 2:
        reason = "two_searches_added_nothing"
    elif not runtime.open_edges:
        reason = "important_edges_resolved"
    else:
        # Do not claim resolution of edges that the fixed budget left unchecked.
        reason = "budget_exhausted"
    if (reason == "budget_exhausted" and runtime.remaining == 1) or (
        runtime.remaining and reason != "budget_exhausted"
    ):
        runtime.call("stop", reason=reason)
    return reason
