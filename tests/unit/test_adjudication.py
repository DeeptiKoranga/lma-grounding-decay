"""Blind double-annotation of the gold graphs, and the kappa it feeds (#15, #37).

The point of these is that the measurement cannot be quietly weakened: a
worksheet cannot leak a label, a half-finished sheet cannot be scored, a
contradictory label cannot be recorded, and a kappa that is misleading because
one label dominates says so.
"""

from __future__ import annotations

import csv

import pytest
from pydantic import ValidationError

from eval.adjudication import (
    BLANK_COLUMNS,
    FILLED_COLUMNS,
    AdjudicationLabel,
    against_draft,
    build_items,
    item_id,
    load_worksheet,
    score,
    worksheet_rows,
)
from eval.agreement import kappa
from eval.gold import load_gold_graph

DEV_QUERIES = ["dev-oil-why", "dev-oil-effects", "dev-rupee-why", "dev-rupee-effects"]


@pytest.fixture
def graphs():
    return {q: load_gold_graph(q) for q in DEV_QUERIES}


@pytest.fixture
def items(graphs):
    return build_items(graphs)


# ---------------------------------------------------------------------------
# The worksheet must not leak what it is asking for
# ---------------------------------------------------------------------------


def test_the_worksheet_carries_no_label_column_prefilled(items):
    rows = worksheet_rows(items, "Deepti", seed=1)
    assert rows
    for row in rows:
        for column in BLANK_COLUMNS:
            assert row[column] == "", f"{column} must be blank for the annotator"


def test_the_worksheet_does_not_contain_the_drafted_direction_or_strength(items, graphs):
    """A row that printed 'direct' anywhere would anchor the annotator."""
    drafted = {
        item_id(graph.query_id, edge.edge_id): edge
        for graph in graphs.values()
        for edge in graph.edges
    }
    for row in worksheet_rows(items, "Varun", seed=1):
        edge = drafted[row["item_id"]]
        blob = " ".join(row[column] for column in FILLED_COLUMNS if column != "span").lower()
        assert edge.strength.value not in blob
        assert edge.provenance.value not in blob


def test_item_ids_are_opaque_so_a_row_cannot_be_looked_up_in_the_draft(items):
    for item in items:
        assert item.edge_id not in item.item_id
        assert item.query_id not in item.item_id


def test_two_annotators_get_the_same_edges_in_different_orders(items):
    left = worksheet_rows(items, "Deepti", seed=7)
    right = worksheet_rows(items, "Varun", seed=7)
    assert {r["item_id"] for r in left} == {r["item_id"] for r in right}
    assert [r["item_id"] for r in left] != [r["item_id"] for r in right]


def test_the_order_is_reproducible_across_machines(items):
    assert worksheet_rows(items, "Deepti", seed=7) == worksheet_rows(items, " deepti ", seed=7)


def test_both_annotators_get_every_edge_not_half_each(items, graphs):
    total = sum(len(g.edges) for g in graphs.values())
    assert len(worksheet_rows(items, "Deepti", seed=1)) == total
    assert len(worksheet_rows(items, "Varun", seed=1)) == total


# ---------------------------------------------------------------------------
# A label cannot be self-contradictory
# ---------------------------------------------------------------------------


def test_asserts_yes_needs_a_direction_and_a_strength():
    with pytest.raises(ValidationError, match="needs direction and strength"):
        AdjudicationLabel(item_id="a", asserts=True, verdict="keep")


def test_asserts_no_cannot_carry_a_direction_or_strength():
    with pytest.raises(ValidationError, match="cannot carry a direction"):
        AdjudicationLabel(
            item_id="a", asserts=False, direction="up", strength="direct", verdict="drop"
        )


def test_asserts_no_must_be_dropped():
    with pytest.raises(ValidationError, match="must be verdict 'drop'"):
        AdjudicationLabel(item_id="a", asserts=False, verdict="keep")


def test_asserts_yes_cannot_be_dropped_without_saying_why():
    with pytest.raises(ValidationError, match="contradictory"):
        AdjudicationLabel(
            item_id="a", asserts=True, direction="up", strength="direct", verdict="drop"
        )


def test_an_unknown_verdict_is_refused():
    with pytest.raises(ValidationError, match="verdict must be one of"):
        AdjudicationLabel(
            item_id="a", asserts=True, direction="up", strength="direct", verdict="maybe"
        )


# ---------------------------------------------------------------------------
# A half-finished sheet is not a sheet
# ---------------------------------------------------------------------------


def _write(path, rows):
    columns = [*FILLED_COLUMNS, *BLANK_COLUMNS]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def test_a_partly_filled_worksheet_is_refused(tmp_path, items):
    rows = worksheet_rows(items, "Deepti", seed=1)
    for row in rows[:3]:
        row.update(asserts="yes", direction="up", strength="direct", verdict="keep")
    path = tmp_path / "worksheet-deepti.csv"
    _write(path, rows)
    with pytest.raises(ValueError, match="incomplete"):
        load_worksheet(path)


def test_a_complete_worksheet_round_trips(tmp_path, items):
    rows = worksheet_rows(items, "Deepti", seed=1)
    for row in rows:
        row.update(asserts="y", direction="up", strength="conditional", verdict="keep")
    path = tmp_path / "worksheet-deepti.csv"
    _write(path, rows)
    labels = load_worksheet(path)
    assert len(labels) == len(rows)
    assert all(label.asserts for label in labels.values())


def test_a_nonsense_asserts_value_is_refused(tmp_path, items):
    rows = worksheet_rows(items, "Deepti", seed=1)
    for row in rows:
        row.update(asserts="probably", direction="up", strength="direct", verdict="keep")
    path = tmp_path / "worksheet-deepti.csv"
    _write(path, rows)
    with pytest.raises(ValueError, match="must be yes or no"):
        load_worksheet(path)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _labels(items, **over):
    out = {}
    for item in items:
        out[item.item_id] = AdjudicationLabel(
            item_id=item.item_id,
            asserts=True,
            direction="up",
            strength="direct",
            verdict="keep",
            **over,
        )
    return out


def test_direction_and_strength_are_scored_only_where_both_said_asserts(items):
    first = _labels(items)
    second = dict(_labels(items))
    rejected = next(iter(second))
    second[rejected] = AdjudicationLabel(item_id=rejected, asserts=False, verdict="drop")

    asserts, direction, strength = score(first, second)
    assert asserts.items == len(items)
    assert direction.items == len(items) - 1
    assert strength.items == len(items) - 1
    assert "excluded" in (direction.note or "")


def test_scoring_refuses_worksheets_covering_different_items(items):
    first = _labels(items)
    second = dict(first)
    second.pop(next(iter(second)))
    with pytest.raises(ValueError, match="different items"):
        score(first, second)


def test_a_constant_label_leaves_kappa_undefined_rather_than_zero(items):
    """Both annotators saying 'asserts' on everything is agreement, but chance
    agreement is 1, so a kappa would be meaningless rather than perfect."""
    asserts, _, _ = score(_labels(items), _labels(items))
    assert asserts.observed_agreement == 1.0
    assert asserts.kappa is None


def test_the_kappa_paradox_is_flagged_not_hidden():
    """19 of 20 items agreeing, with one label dominating, gives a kappa near
    zero. Reporting that alone would say the annotators disagreed, which is the
    opposite of what happened."""
    left = {f"i{n}": "True" for n in range(20)}
    right = dict(left)
    right["i0"] = "False"
    result = kappa(left, right)
    assert result["observed_agreement"] == 0.95
    assert result["kappa"] is not None and result["kappa"] < 0.4
    assert result["paradox_warning"]


def test_kappa_carries_an_interval_because_twenty_items_is_a_small_sample():
    left = {f"i{n}": ("x" if n % 2 else "y") for n in range(20)}
    right = dict(left)
    right["i0"] = "x"
    result = kappa(left, right)
    low, high = result["ci95"]
    assert low < result["kappa"] < high
    assert high - low > 0.2, "an interval this tight at n=20 would be suspicious"


def test_agreement_with_the_draft_is_reported_separately_from_agreement(items, graphs):
    """It answers a different question and must never be quoted as kappa."""
    stats = against_draft(_labels(items), items, graphs)
    assert stats["items"] == len(items)
    # Every label above says 'direct'; the draft is a mix, so this cannot be 1.0.
    assert stats["strength_match"] < 1.0


def test_the_two_halves_do_not_share_a_report_path_or_a_gold_directory():
    """Regression: `--sheets data/eval/gold/test/adjudication` once scored test
    worksheets against **dev** gold and overwrote the dev report with a file
    still titled "the dev gold graphs". Everything that differs between the
    halves now hangs off one flag, so it cannot drift again."""
    import importlib.util
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "score_adjudication", repo / "scripts/score_adjudication.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    sets = module.SETS
    assert set(sets) == {"dev", "test"}
    for key in ("queries", "gold", "sheets", "report", "title"):
        values = [sets[half][key] for half in sets]
        assert len(set(map(str, values))) == len(values), f"{key} is shared between halves"
    assert "dev" in sets["dev"]["title"]
    assert "test" in sets["test"]["title"]
