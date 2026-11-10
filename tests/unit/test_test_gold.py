"""The test-half gold drafts (#38).

These guard two things the dev tests cannot. First, that the test half is
honestly labelled: it is drafted and **not** adjudicated, so its provenance line
must say so and must not claim a receipt it does not have. Second, that the
partial coverage is deliberate — two of the four test queries carry no graph,
and a future run that silently produced four, or zero, should fail here rather
than be noticed in a results table.

The corpus payload is not in git, so span-level checks are skipped without it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.gold import MIN_EDGES, gold_path, load_gold_graph, validate_gold_graph
from schema import Passage

REPO = Path(__file__).resolve().parents[2]
CORPUS = REPO / "data/processed/articles.jsonl"
TEST_GOLD_DIR = REPO / "data/eval/gold/test"
TEST_QUERIES_FILE = REPO / "data/eval/queries_test.jsonl"

#: Drafted on 10 Nov 2026 after reading the corpus. `test-cpi-why` is excluded
#: by D-27 (its target is never paired with headline CPI in Indian coverage);
#: `test-cpi-effects` is excluded because this corpus runs the wrong way through
#: it — Indian headline CPI is the destination of the oil shock here, not its
#: source, so an effects graph rooted at CPI cannot reach MIN_EDGES.
DRAFTED = ("test-fpi-why", "test-fpi-effects")
NOT_DRAFTED = ("test-cpi-why", "test-cpi-effects")


def _declared_query_ids() -> list[str]:
    return [
        json.loads(line)["query_id"]
        for line in TEST_QUERIES_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_the_test_half_declares_four_queries():
    assert sorted(_declared_query_ids()) == sorted(DRAFTED + NOT_DRAFTED)


@pytest.mark.parametrize("query_id", DRAFTED)
def test_each_drafted_test_graph_exists_and_is_structurally_valid(query_id):
    report = validate_gold_graph(load_gold_graph(query_id, TEST_GOLD_DIR), expect_query_id=query_id)
    assert report.ok, [i.problem for i in report.issues]


@pytest.mark.parametrize("query_id", NOT_DRAFTED)
def test_the_two_undraftable_queries_have_no_graph(query_id):
    """Absence here is a finding, not an oversight. A file appearing for either
    of these means someone drafted a graph the corpus does not support, and it
    would be scored as a reference set."""
    assert not gold_path(query_id, TEST_GOLD_DIR).is_file()


@pytest.mark.parametrize("query_id", DRAFTED)
def test_each_drafted_test_graph_is_marked_unadjudicated(query_id):
    """The dev set says ADJUDICATED and names its receipt. The test set must say
    the opposite, because nothing stops a reader citing a gold-shaped file as a
    reviewed reference set except the sentence inside it."""
    notes = load_gold_graph(query_id, TEST_GOLD_DIR).notes or ""
    assert "DRAFT, NOT ADJUDICATED" in notes
    assert "ADJUDICATED 2026-11-08" not in notes
    assert "review_receipt" not in notes


@pytest.mark.parametrize("query_id", DRAFTED)
def test_each_drafted_test_graph_clears_min_edges(query_id):
    edges = load_gold_graph(query_id, TEST_GOLD_DIR).edges
    assert len(edges) >= MIN_EDGES


def test_the_test_half_has_no_signed_receipt():
    """Scoring with --references must stay refused until two annotators have
    read every span. The receipt's absence is what enforces that."""
    assert not (TEST_GOLD_DIR / "review_receipt.json").is_file()


def test_the_drafted_test_set_reaches_past_hop_one():
    hops = {e.hop for q in DRAFTED for e in load_gold_graph(q, TEST_GOLD_DIR).edges}
    assert max(hops) >= 2, f"test gold edges only reach hop {max(hops)}"


@pytest.mark.skipif(not CORPUS.is_file(), reason="corpus payload is not in git")
@pytest.mark.parametrize("query_id", DRAFTED)
def test_each_drafted_test_span_is_verbatim_in_the_corpus(query_id):
    passages = {
        p.passage_id: p
        for p in (
            Passage.model_validate_json(line)
            for line in CORPUS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    graph = load_gold_graph(query_id, TEST_GOLD_DIR)
    for edge in graph.edges:
        passage = passages.get(edge.evidence_passage_id or "")
        assert passage is not None, f"{edge.edge_id}: passage not in corpus"
        assert edge.evidence_span in passage.text, f"{edge.edge_id}: span not verbatim"
        assert passage.published_at.date() <= graph.as_of, f"{edge.edge_id}: published late"
