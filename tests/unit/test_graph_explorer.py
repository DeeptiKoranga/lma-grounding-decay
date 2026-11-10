"""The interactive event-impact graph (proposal section 8).

The page embeds every graph as JSON inside its own `<script>` block, which is
the part that can break quietly: a span containing `</script>` would end the
block early and the page would render as text from that point on. It is also
the one artifact that shows corpus excerpts, so these check it stays offline
and stays faithful to the gold files rather than paraphrasing them.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "build_graph_explorer", REPO / "scripts/build_graph_explorer.py"
)
module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(module)

GOLD = (REPO / "data/eval/gold/dev", REPO / "data/eval/gold/test")


@pytest.fixture(scope="module")
def page(tmp_path_factory) -> str:
    out = tmp_path_factory.mktemp("explorer") / "graph_explorer.html"
    module.build(GOLD, out)
    return out.read_text(encoding="utf-8")


def _payload(page: str) -> list[dict]:
    match = re.search(r"const GRAPHS = (\[.*?\]);\n", page, re.S)
    assert match, "embedded payload not found"
    # No un-escaping needed: the builder writes "<" as \u003c, which is a plain
    # JSON escape that json.loads resolves on its own.
    return json.loads(match.group(1))


def test_the_embedded_payload_parses(page):
    graphs = _payload(page)
    assert graphs and all(g["edges"] for g in graphs)


def test_no_span_can_terminate_the_script_block(page):
    """The escape is what stops a passage containing a closing tag from ending
    the data early. Without it the failure is silent: the page renders, and
    everything after the offending span is gone."""
    match = re.search(r"const GRAPHS = (\[.*?\]);\n", page, re.S)
    assert "</script>" not in match.group(1)
    assert "<script" not in match.group(1), "an opening tag can trigger double-escaping"
    assert page.count("<script>") == 1
    assert page.count("</script>") == 1


def test_a_span_containing_a_closing_tag_survives_a_round_trip(tmp_path):
    """Directly, rather than relying on the corpus not containing one today."""
    graph = {
        "query_id": "q",
        "_set": "dev",
        "as_of": "2026-01-01",
        "anchor": {"var": "A", "direction": "up"},
        "nodes": [{"var": "A", "direction": "up", "is_anchor": True}],
        "edges": [
            {
                "edge_id": "e1",
                "src_var": "A",
                "dst_var": "B",
                "direction": "up",
                "provenance": "source_asserted",
                "strength": "direct",
                "hop": 1,
                "evidence_span": "before </script><script>alert(1)</script> after",
            }
        ],
    }
    graph["_depth"] = module._depths(graph)
    out = tmp_path / "x.html"
    payload = json.dumps([graph], ensure_ascii=False).replace("<", "\\u003c")
    out.write_text(module.PAGE.replace("__DATA__", payload), encoding="utf-8")
    text = out.read_text(encoding="utf-8")
    assert text.count("<script>") == 1
    assert _payload(text)[0]["edges"][0]["evidence_span"] == graph["edges"][0]["evidence_span"]


def test_every_span_is_byte_identical_to_its_gold_file(page):
    """The page is the only place a reader meets the evidence directly. A span
    that drifted from the gold file would be showing them something the study
    did not measure."""
    for embedded in _payload(page):
        source = REPO / f"data/eval/gold/{embedded['_set']}/{embedded['query_id']}.json"
        gold = json.loads(source.read_text(encoding="utf-8"))
        by_id = {e["edge_id"]: e for e in gold["edges"]}
        for edge in embedded["edges"]:
            assert edge.get("evidence_span") == by_id[edge["edge_id"]].get("evidence_span")


def test_the_page_loads_nothing_from_the_network(page):
    """It is opened from disk, possibly offline, and it shows licensed corpus
    text. Both reasons point the same way: no CDN, no fonts, no fetch."""
    stripped = page.replace("http://www.w3.org/2000/svg", "")
    for needle in ("http://", "https://", "cdn.", "<link", "@import", "fetch(", "XMLHttpRequest"):
        assert needle not in stripped, needle


def test_every_edge_endpoint_has_a_column(page):
    """A variable with no depth is dropped by the renderer without an error, so
    the edge simply does not appear."""
    for graph in _payload(page):
        depth = graph["_depth"]
        endpoints = {v for e in graph["edges"] for v in (e["src_var"], e["dst_var"])}
        assert endpoints <= set(depth)
        assert depth[graph["anchor"]["var"]] == 0


def test_a_variable_reached_twice_takes_the_shallower_column():
    """Otherwise an edge can point backwards and the chain stops reading left
    to right, which is the one thing the layout is for."""
    graph = {
        "anchor": {"var": "A"},
        "nodes": [{"var": v} for v in "ABC"],
        "edges": [
            {"src_var": "A", "dst_var": "C", "hop": 3},
            {"src_var": "A", "dst_var": "C", "hop": 1},
        ],
    }
    assert module._depths(graph)["C"] == 1


def test_both_halves_are_included(page):
    assert {g["_set"] for g in _payload(page)} == {"dev", "test"}
