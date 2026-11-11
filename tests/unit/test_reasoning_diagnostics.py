"""Direction accuracy and strength macro-F1 over synthetic graphs.

`runs/**` is gitignored, so these build their own. The cases that matter are the
ones where a plausible implementation quietly says something false: a reversed
edge counted as a match, a class with no instances averaged in as a zero, and
strength inflation's asymmetry leaking into a metric that is meant to be
symmetric.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "report_reasoning_diagnostics", REPO / "scripts/report_reasoning_diagnostics.py"
)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)

macro_f1 = module.macro_f1


def test_a_class_nobody_predicted_or_referenced_is_dropped_not_scored_zero():
    """Only `direct` occurs. Averaging `conditional` and `correlational` in as
    zeros would report 0.333 for a model that got every edge right."""
    value, per_class = macro_f1([("direct", "direct"), ("direct", "direct")])
    assert set(per_class) == {"direct"}
    assert value == 1.0


def test_a_class_that_was_referenced_but_never_predicted_is_scored():
    """Absent from the predictions is not absent from the problem: the model had
    the chance and missed it, so the class stays in the average."""
    value, per_class = macro_f1([("conditional", "direct"), ("direct", "direct")])
    assert set(per_class) == {"direct", "conditional"}
    assert per_class["conditional"]["f1"] == 0.0
    assert per_class["conditional"]["support"] == 1
    assert value is not None and value < 1.0


def test_macro_f1_weights_a_rare_class_as_heavily_as_a_common_one():
    """Six `direct` right and the single `correlational` wrong is 0.857 accuracy
    but 0.5 macro-F1. That gap is the reason the proposal asks for macro."""
    pairs = [("direct", "direct")] * 6 + [("correlational", "direct")]
    value, per_class = macro_f1(pairs)
    assert per_class["correlational"]["f1"] == 0.0
    assert value == round((per_class["direct"]["f1"] + 0.0) / 2, 3)
    assert value < 0.86


def test_macro_f1_counts_understatement_as_well_as_overstatement():
    """Strength inflation counts only over-statement. This must not inherit that
    asymmetry: calling a direct relation correlational is an error too."""
    over, _ = macro_f1([("conditional", "direct")])
    under, _ = macro_f1([("direct", "conditional")])
    assert over == under == 0.0


def test_no_pairs_at_all_gives_none_rather_than_zero():
    value, per_class = macro_f1([])
    assert value is None and per_class == {}


def test_perfect_prediction_over_every_class_is_one():
    pairs = [(s, s) for s in module.STRENGTHS]
    value, per_class = macro_f1(pairs)
    assert value == 1.0 and len(per_class) == 3


def test_the_renderer_prints_n_a_rather_than_none():
    report = {
        "M": {
            "matched_edges": 0,
            "direction_accuracy": None,
            "strength_macro_f1": None,
            "strength_per_class": {},
            "graphs": 0,
            "graphs_without_a_reference": 0,
            "graphs_at_a_different_cutoff": 0,
        }
    }
    text = module.render(report, Path("runs/x"), Path("data/eval/gold/dev"))
    assert "n/a" in text
    assert "None" not in text


def test_the_declared_strength_labels_are_the_ontology_s_own():
    from schema.enums import Strength

    assert set(module.STRENGTHS) == {s.value for s in Strength}


def _graph(query_id, as_of, edges):
    from datetime import date

    from schema import Anchor, Edge, Graph, GraphNode

    anchor = Anchor(
        var="BRENT", direction="up", event="a synthetic anchor event", event_date=date(2026, 1, 1)
    )
    variables = {"BRENT"} | {v for e in edges for v in (e["src"], e["dst"])}
    return Graph(
        query_id=query_id,
        anchor=anchor,
        as_of=as_of,
        nodes=[GraphNode(var=v, direction="up", is_anchor=v == "BRENT") for v in sorted(variables)],
        edges=[
            Edge(
                edge_id=f"g{i}",
                src_var=e["src"],
                dst_var=e["dst"],
                direction=e.get("direction", "up"),
                provenance="model_inferred",
                strength=e.get("strength", "direct"),
                hop=1,
            )
            for i, e in enumerate(edges)
        ],
    )


def test_a_condition_matching_nothing_is_reported_as_zero_not_omitted(monkeypatch, tmp_path):
    """A row that disappears reads as a condition that was never run. A row of
    zeros reads as one that produced nothing matching the references, which is
    a finding about that condition."""
    from datetime import date

    reference = {
        "q1": {"as_of": date(2026, 4, 20), "anchor": ("BRENT", "up", date(2026, 1, 1)), "edges": {}}
    }
    monkeypatch.setattr(module, "_reference_edges", lambda _: reference)
    monkeypatch.setattr(
        module,
        "_generated",
        lambda _: [("B0", _graph("q1", date(2026, 4, 20), [{"src": "BRENT", "dst": "NIFTY50"}]))],
    )
    report = module.summarise(tmp_path, tmp_path)
    assert "B0" in report, "a condition with no matched edges vanished"
    assert report["B0"]["matched_edges"] == 0
    assert report["B0"]["direction_accuracy"] is None
    assert report["B0"]["graphs"] == 1


def test_a_graph_at_a_different_cutoff_is_skipped_and_counted(monkeypatch, tmp_path):
    """The reference was adjudicated under its own as-of discipline. Matching
    across cutoffs scores edges against evidence that was not yet visible."""
    from datetime import date

    reference = {
        "q1": {
            "as_of": date(2026, 4, 20),
            "anchor": ("BRENT", "up", date(2026, 1, 1)),
            "edges": {
                ("BRENT", "INR_USD"): {"direction": "up", "strength": "direct", "edge_id": "r1"}
            },
        }
    }
    monkeypatch.setattr(module, "_reference_edges", lambda _: reference)
    monkeypatch.setattr(
        module,
        "_generated",
        lambda _: [("M", _graph("q1", date(2026, 9, 30), [{"src": "BRENT", "dst": "INR_USD"}]))],
    )
    report = module.summarise(tmp_path, tmp_path)
    assert report["M"]["matched_edges"] == 0, "scored an edge across a cutoff mismatch"
    assert report["M"]["graphs_at_a_different_cutoff"] == 1


def test_a_graph_at_the_declared_cutoff_is_scored(monkeypatch, tmp_path):
    from datetime import date

    reference = {
        "q1": {
            "as_of": date(2026, 4, 20),
            "anchor": ("BRENT", "up", date(2026, 1, 1)),
            "edges": {
                ("BRENT", "INR_USD"): {"direction": "up", "strength": "direct", "edge_id": "r1"}
            },
        }
    }
    monkeypatch.setattr(module, "_reference_edges", lambda _: reference)
    monkeypatch.setattr(
        module,
        "_generated",
        lambda _: [("M", _graph("q1", date(2026, 4, 20), [{"src": "BRENT", "dst": "INR_USD"}]))],
    )
    report = module.summarise(tmp_path, tmp_path)
    assert report["M"]["matched_edges"] == 1
    assert report["M"]["direction_accuracy"] == 1.0
    assert report["M"]["graphs_at_a_different_cutoff"] == 0


def test_wrong_anchor_at_same_cutoff_is_not_scored(monkeypatch, tmp_path, graph):
    anchor = graph.anchor
    reference = {
        graph.query_id: {
            "as_of": graph.as_of,
            "anchor": (anchor.var, anchor.direction, graph.as_of),
            "edges": {},
        },
    }
    assert anchor.event_date != graph.as_of
    monkeypatch.setattr(module, "_reference_edges", lambda _: reference)
    monkeypatch.setattr(module, "_generated", lambda _: [("M", graph)])
    row = module.summarise(tmp_path, tmp_path)["M"]
    assert row["graphs_at_a_different_anchor"] == 1
    assert row["matched_edges"] == 0
