"""Deterministic graph safety checks and clearly labelled text-screening heuristics."""

from __future__ import annotations

import re

from schema import Graph


def inspect_graph(graph: Graph, corpus) -> dict:
    graph = Graph.model_validate(graph.model_dump())
    trusted = {p.passage_id: p for p in corpus}
    failures = []
    for edge in graph.edges:
        if edge.is_asserted:
            passage = trusted.get(edge.evidence_passage_id)
            if passage is None or passage.doc_id != edge.evidence_doc_id:
                failures.append({"edge_id": edge.edge_id, "kind": "out_of_corpus"})
            elif not passage.visible_at(graph.as_of):
                failures.append({"edge_id": edge.edge_id, "kind": "post_date_evidence"})
            elif edge.evidence_span not in passage.text:
                failures.append({"edge_id": edge.edge_id, "kind": "nonverbatim_span"})
            elif edge.evidence_published_at != passage.published_at:
                failures.append({"edge_id": edge.edge_id, "kind": "citation_date_mismatch"})
    return {
        "failures": failures,
        "passed": not failures,
        "scope": "structural source/date/span checks; semantic support requires independent judgment",
    }


def screen_text(text: str) -> dict:
    return {
        "advice_flag": bool(
            re.search(
                r"\b(?:you should|I recommend|you must)\s+(?:buy|sell|invest|short)\b", text, re.I
            )
        ),
        "own_forecast_flag": bool(re.search(r"\bI (?:predict|forecast|expect)\b", text, re.I)),
        "scope": "heuristic flags for review, not a certified advice/forecast leakage metric",
    }
