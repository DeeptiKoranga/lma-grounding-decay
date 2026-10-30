"""RQ1 and RQ2 findings, and the gates that stop a thin slice becoming a claim.

The risk these cover is not a wrong number, it is a true number carrying a
claim it cannot support: a monotone "trend" across two populated hop buckets,
or a UER improvement that is really the verifier deleting edges it could not
confirm. Every test here is about the finding refusing to say more than the
data allows.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.metrics import SupportJudgment, aggregate, score_graph
from eval.review import prepare
from eval.rq import (
    MIN_ESTABLISHED_PER_BUCKET,
    MIN_QUERIES_FOR_INFERENCE,
    rq1_finding,
    rq2_finding,
)
from schema import Graph

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.fixture
def graph():
    return Graph.model_validate_json((FIXTURES / "graph_brent_hormuz.json").read_text())


def _scored(graph, *, established, supported, reference=None):
    judgments = {
        edge.edge_id: SupportJudgment(
            edge.edge_id in supported,
            edge.strength if edge.edge_id in supported else None,
        )
        for edge in graph.edges
    }
    return score_graph(
        graph, established=set(established), judgments=judgments, reference=reference
    )


def _signed_references(graph, folder: Path, corpus: Path) -> Path:
    """A reference set with a completed attestation, for fixture use only.

    Signing a receipt is a human act; doing it here is legitimate precisely
    because these are synthetic fixtures with no research claim attached.
    """
    from eval.references import prepare as prepare_references

    folder.mkdir(parents=True)
    payload = graph.model_dump(mode="json")
    payload["edges"] = [e for e in payload["edges"] if e["provenance"] == "source_asserted"]
    payload["paths"] = []
    reference = Graph.model_validate(payload)
    (folder / f"{reference.query_id}.json").write_text(
        reference.model_dump_json(indent=2, exclude_none=True)
    )
    prepare_references(references=folder, corpus=corpus)
    receipt = folder / "review_receipt.json"
    data = json.loads(receipt.read_text())
    data.update(
        reviewer="Fixture annotators",
        reviewed_on="2026-10-28",
        independent_review=True,
        all_relations_and_strengths_reviewed=True,
    )
    receipt.write_text(json.dumps(data, indent=2))
    return folder


def _condition(per_query: dict[str, dict]):
    return aggregate(list(per_query.values())), per_query


# ---------------------------------------------------------------------------
# RQ1 will not report a trend it cannot support
# ---------------------------------------------------------------------------


def test_a_thin_bucket_cannot_support_a_claim_about_that_hop(graph):
    asserted = [e.edge_id for e in graph.edges if e.is_asserted]
    scored = _scored(graph, established=asserted, supported=asserted[:3])
    finding = rq1_finding("B1", *_condition({"q1": scored}))

    assert finding.trend == "insufficient_data"
    thin = [row for row in finding.buckets if not row.usable]
    assert thin, "one query of nine edges cannot clear the per-bucket minimum"
    assert all(str(MIN_ESTABLISHED_PER_BUCKET) in (row.reason or "") for row in thin)


def test_an_empty_deep_bucket_is_named_as_the_finding(graph):
    """The hop >=3 slice is what H1 is about. Its absence must not read as a
    footnote under a two-point trend."""
    shallow = [e.edge_id for e in graph.edges if e.is_asserted and e.hop < 3]
    scored = _scored(graph, established=shallow, supported=shallow[:2])
    finding = rq1_finding("B1", *_condition({"q1": scored}))

    assert finding.deep_bucket_empty
    assert "empty" in finding.statement
    assert "two-point trend" in finding.statement


def test_a_full_set_of_usable_buckets_reports_the_direction(graph):
    """Synthetic, and only to prove the trend arm is reachable - a real run has
    to clear the same gates."""
    asserted = [e.edge_id for e in graph.edges if e.is_asserted]
    # Repeat the query enough times that every bucket clears the minimum, and
    # support nothing, so UER is 1.0 in each bucket.
    per_query = {f"q{n}": _scored(graph, established=asserted, supported=[]) for n in range(12)}
    finding = rq1_finding("B1", *_condition(per_query))

    assert set(finding.usable_buckets) == {"1", "2", "3+"}
    # Flat at 1.0 everywhere is not monotone, and must not be called a trend.
    assert finding.trend == "no_monotone_trend"
    assert finding.inferential


def test_four_queries_is_marked_descriptive_not_inferential(graph):
    asserted = [e.edge_id for e in graph.edges if e.is_asserted]
    per_query = {f"q{n}": _scored(graph, established=asserted, supported=[]) for n in range(4)}
    finding = rq1_finding("B1", *_condition(per_query))

    assert finding.queries == 4 < MIN_QUERIES_FOR_INFERENCE
    assert not finding.inferential


def test_rq1_needs_at_least_one_scored_query():
    with pytest.raises(ValueError, match="at least one scored query"):
        rq1_finding("B1", {}, {})


# ---------------------------------------------------------------------------
# RQ2 will not call a UER drop a repair without the recall guard
# ---------------------------------------------------------------------------


def test_rq2_is_not_addressable_without_both_conditions():
    finding = rq2_finding({"per_query": {"B1": {"q": {}}}})
    assert finding.recall_guard == "undetermined"
    assert "needs B1 and M" in finding.statement


def test_a_uer_drop_with_an_undetermined_guard_is_not_a_repair():
    """The headline moved the right way and we cannot tell why. That has to be
    said, because deleting unconfirmable edges produces the same number."""
    finding = rq2_finding(
        {
            "per_query": {"B1": {"q1": {}, "q2": {}}, "M": {"q1": {}, "q2": {}}},
            "contrasts": {"uer": {"M_minus_B1_overall": {"estimate": -0.25, "ci95": [-0.4, -0.1]}}},
            "recall_guard": {
                "passes_descriptively": None,
                "status": "requires reviewed reference recall",
                "minimum_M_minus_B1": -0.10,
            },
        }
    )
    assert finding.uer_delta == -0.25
    assert finding.recall_guard == "undetermined"
    assert "cannot be reported as a repair" in finding.statement
    assert "deleting edges" in finding.statement


def test_a_uer_drop_that_fails_h2d_is_called_what_it_is():
    finding = rq2_finding(
        {
            "per_query": {"B1": {"q1": {}}, "M": {"q1": {}}},
            "contrasts": {"uer": {"M_minus_B1_overall": {"estimate": -0.30, "ci95": None}}},
            "recall_guard": {
                "passes_descriptively": False,
                "M_minus_B1": -0.22,
                "minimum_M_minus_B1": -0.10,
            },
        }
    )
    assert finding.recall_guard == "fails"
    assert "H2d fails" in finding.statement
    assert "bought by dropping supported edges" in finding.statement
    assert finding.uer_ci95 is None, "a one-query bootstrap interval is withheld"


def test_a_uer_rise_that_fails_h2d_is_not_described_as_a_trade_off():
    """Saying an improvement was bought by dropping edges, when UER also rose,
    would describe a trade that did not happen."""
    finding = rq2_finding(
        {
            "per_query": {"B1": {"q1": {}, "q2": {}}, "M": {"q1": {}, "q2": {}}},
            "contrasts": {"uer": {"M_minus_B1_overall": {"estimate": 0.42, "ci95": [0.1, 0.7]}}},
            "recall_guard": {
                "passes_descriptively": False,
                "M_minus_B1": -0.43,
                "minimum_M_minus_B1": -0.10,
            },
        }
    )
    assert "raises UER" in finding.statement
    assert "bought by dropping" not in finding.statement
    assert "worse on both counts" in finding.statement


def test_a_uer_drop_within_the_guard_is_reported_as_holding():
    finding = rq2_finding(
        {
            "per_query": {f"q{n}": {} for n in range(1)}
            and {"B1": {f"q{n}": {} for n in range(12)}, "M": {f"q{n}": {} for n in range(12)}},
            "contrasts": {
                "uer": {"M_minus_B1_overall": {"estimate": -0.18, "ci95": [-0.3, -0.05]}}
            },
            "recall_guard": {
                "passes_descriptively": True,
                "M_minus_B1": -0.03,
                "minimum_M_minus_B1": -0.10,
            },
        }
    )
    assert finding.recall_guard == "passes"
    assert "H2d holds" in finding.statement
    assert finding.inferential
    assert "Descriptive only" not in finding.statement


def test_a_small_paired_sample_is_marked_descriptive():
    finding = rq2_finding(
        {
            "per_query": {"B1": {"q1": {}, "q2": {}}, "M": {"q1": {}, "q2": {}}},
            "contrasts": {"uer": {"M_minus_B1_overall": {"estimate": -0.18, "ci95": [-0.9, 0.5]}}},
            "recall_guard": {
                "passes_descriptively": True,
                "M_minus_B1": -0.03,
                "minimum_M_minus_B1": -0.10,
            },
        }
    )
    assert not finding.inferential
    assert "Descriptive only" in finding.statement


# ---------------------------------------------------------------------------
# The whole path, from run artifacts to two report files
# ---------------------------------------------------------------------------


def test_the_reports_are_written_from_a_reviewed_run(graph, tmp_path, monkeypatch):
    import scripts.report_rq as report_rq

    runs = tmp_path / "runs"
    for condition in ("B1", "M"):
        folder = runs / condition
        folder.mkdir(parents=True)
        payload = graph.model_dump(mode="json")
        payload["condition"] = condition
        (folder / "query.json").write_text(
            json.dumps(
                {
                    "graph": payload,
                    "established_edge_ids": [e.edge_id for e in graph.edges if e.is_asserted],
                }
            )
        )

    review = tmp_path / "review"
    prepare(runs=runs, corpus=FIXTURES / "passages.jsonl", output=review)
    judgments = json.loads((review / "judgments.json").read_text())
    judgments.update(
        reviewer="Fixture reviewer",
        reviewed_on="2026-10-28",
        independent_review=True,
        blinded_to_condition=True,
    )
    for row in judgments["judgments"]:
        row.update(supported=False)
    (review / "judgments.json").write_text(json.dumps(judgments))

    references = _signed_references(graph, tmp_path / "refs", FIXTURES / "passages.jsonl")

    rq1, rq2 = tmp_path / "rq1.md", tmp_path / "rq2.md"
    code = report_rq.main(
        [
            "--review-dir",
            str(review),
            "--references",
            str(references),
            "--corpus",
            str(FIXTURES / "passages.jsonl"),
            "--rq1",
            str(rq1),
            "--rq2",
            str(rq2),
        ]
    )
    assert code == 0
    body1, body2 = rq1.read_text(), rq2.read_text()
    assert "RQ1" in body1 and "B1" in body1 and "M" in body1
    assert "Do not edit by hand" in body1
    # Nothing is supported, so UER is 1 and no bucket can carry a trend claim.
    assert "not testable" in body1
    assert "recall guard is reported beside UER" in body2


def test_missing_results_write_nothing_and_say_what_is_needed(tmp_path, capsys):
    import scripts.report_rq as report_rq

    code = report_rq.main(
        [
            "--review-dir",
            str(tmp_path / "absent"),
            "--rq1",
            str(tmp_path / "rq1.md"),
            "--rq2",
            str(tmp_path / "rq2.md"),
        ]
    )
    assert code == 2
    assert not (tmp_path / "rq1.md").exists()
    assert not (tmp_path / "rq2.md").exists()
    err = capsys.readouterr().err
    assert "#41" in err and "#42" in err and "#37" in err


def test_scoring_without_references_disables_h2d_and_says_so(graph, tmp_path):
    import scripts.report_rq as report_rq

    runs = tmp_path / "runs"
    for condition in ("B1", "M"):
        folder = runs / condition
        folder.mkdir(parents=True)
        payload = graph.model_dump(mode="json")
        payload["condition"] = condition
        (folder / "query.json").write_text(
            json.dumps(
                {
                    "graph": payload,
                    "established_edge_ids": [e.edge_id for e in graph.edges if e.is_asserted],
                }
            )
        )
    review = tmp_path / "review"
    prepare(runs=runs, corpus=FIXTURES / "passages.jsonl", output=review)
    judgments = json.loads((review / "judgments.json").read_text())
    judgments.update(
        reviewer="Fixture reviewer",
        reviewed_on="2026-10-28",
        independent_review=True,
        blinded_to_condition=True,
    )
    for row in judgments["judgments"]:
        row.update(supported=True, evidence_strength="correlational")
    (review / "judgments.json").write_text(json.dumps(judgments))

    rq1, rq2 = tmp_path / "rq1.md", tmp_path / "rq2.md"
    code = report_rq.main(
        [
            "--review-dir",
            str(review),
            "--no-references",
            "--corpus",
            str(FIXTURES / "passages.jsonl"),
            "--rq1",
            str(rq1),
            "--rq2",
            str(rq2),
        ]
    )
    assert code == 0
    body = rq2.read_text()
    assert "--no-references" in body
    assert "H2d cannot be evaluated" in body
    assert "RQ1 is unaffected" in body
