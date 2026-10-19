#!/usr/bin/env python
"""Generate `tests/fixtures/` from the source-of-truth definitions in this file.

Run with `make fixtures` (or `uv run python scripts/build_fixtures.py`) and commit
the output. The fixtures are generated rather than hand-written because char
offsets must be exactly right: the whole verbatim-span check (B6) rests on them,
and a hand-maintained JSONL drifts the first time someone fixes a typo.

Everything emitted here is synthetic. The numbers are plausible for the 2026
window and the cue words are the ones the annotation guide cares about
("due to", "because of", "amid", "could", "poses an upside risk"), but no
sentence is copied from a real article.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from schema import (  # noqa: E402
    Anchor,
    Edge,
    Graph,
    GraphNode,
    Passage,
    parse_run_log_line,
)
from schema import Path as GraphPath  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"

# ---------------------------------------------------------------------------
# 13 synthetic documents -> 20 passages, 1 Mar - 30 Sep 2026
# ---------------------------------------------------------------------------

Doc = tuple[str, str, str, str, str, list[str]]  # doc_id, source, kind, published, title, paras

DOCUMENTS: list[Doc] = [
    (
        "bl-2026-03-12-brent100",
        "businessline",
        "news",
        "2026-03-12T18:40:00+05:30",
        "Brent crosses $100 as Hormuz tensions escalate",
        [
            "Brent crude climbed past $100 a barrel on Thursday, its highest level since 2022, "
            "amid renewed concern over shipping through the Strait of Hormuz.",
            "The Indian basket of crude rose to $98.4 a barrel due to the surge in Brent, PPAC "
            "data showed, lifting the cost of the roughly 85 per cent of the oil India imports.",
        ],
    ),
    (
        "bs-2026-03-13-importbill",
        "business_standard",
        "news",
        "2026-03-13T09:05:00+05:30",
        "Oil surge set to widen March import bill",
        [
            "India's monthly import bill is expected to widen by about $2.5 billion because of "
            "the higher Indian basket price, traders said, with crude accounting for the bulk "
            "of the increase.",
        ],
    ),
    (
        "rbi-2026-03-18-mpc-minutes",
        "rbi",
        "official",
        "2026-03-18T17:00:00+05:30",
        "Minutes of the Monetary Policy Committee meeting, March 2026",
        [
            "Members noted that the recent increase in international crude prices poses an "
            "upside risk to headline inflation over the next two quarters.",
            "Should headline inflation stay above the upper tolerance band, the Committee may "
            "have to consider further tightening, one member observed.",
        ],
    ),
    (
        "mint-2026-03-16-atf",
        "mint",
        "news",
        "2026-03-16T11:20:00+05:30",
        "ATF price raised 6.2% as crude bites",
        [
            "State oil marketing companies raised aviation turbine fuel prices by 6.2 per cent "
            "this fortnight due to the rise in Brent crude.",
            "Fuel accounts for about 40 per cent of an Indian carrier's operating cost, so the "
            "increase feeds straight through to airline operating costs.",
        ],
    ),
    (
        "et-2026-03-17-aviation",
        "economic_times",
        "news",
        "2026-03-17T16:05:00+05:30",
        "Aviation stocks slide as fuel costs climb",
        [
            "Shares of listed Indian carriers fell between 3 and 5 per cent on Tuesday amid "
            "rising airline operating costs, with the aviation index closing at a four-month low.",
        ],
    ),
    (
        "et-2026-04-08-rupee88",
        "economic_times",
        "news",
        "2026-04-08T19:30:00+05:30",
        "Rupee slips past 88 as importers rush for dollars",
        [
            "The rupee weakened to 88.12 against the dollar on Wednesday amid sustained dollar "
            "demand from oil importers.",
            "Dealers said the Reserve Bank was seen selling dollars through state-run banks, "
            "which could slow the pace of depreciation without changing its direction.",
        ],
    ),
    (
        "ppac-2026-04-15-lpg",
        "ppac",
        "official",
        "2026-04-15T12:00:00+05:30",
        "Monthly report on LPG imports and prices, March 2026",
        [
            "LPG imports rose 4.1 per cent in March 2026 over the previous month, with about 90 "
            "per cent of volumes transiting the Strait of Hormuz.",
        ],
    ),
    (
        "mospi-2026-05-12-cpi-apr",
        "mospi",
        "official",
        "2026-05-12T17:30:00+05:30",
        "Consumer Price Index for April 2026",
        [
            "All-India CPI inflation stood at 6.4 per cent in April 2026, up from 5.9 per cent "
            "in March, with the fuel and light group contributing 0.4 percentage points of the "
            "increase.",
        ],
    ),
    (
        "bl-2026-05-20-rupee-record",
        "businessline",
        "news",
        "2026-05-20T20:10:00+05:30",
        "Rupee hits record low of 96.90 as oil outflows mount",
        [
            "The rupee touched a record low of 96.90 to the dollar on Wednesday due to heavy "
            "outflows linked to oil payments and a firmer dollar index.",
            "A weaker rupee raises the landed cost of imports, and economists said imported "
            "inflation could add 20 to 30 basis points to headline CPI over two quarters.",
        ],
    ),
    (
        "bs-2026-06-06-mpc",
        "business_standard",
        "news",
        "2026-06-06T14:45:00+05:30",
        "RBI holds repo rate at 6.50%, stance unchanged",
        [
            "The Monetary Policy Committee voted 4-2 to keep the repo rate unchanged at 6.50 "
            "per cent, citing the need to assess how far the crude shock passes into core "
            "inflation.",
        ],
    ),
    (
        "et-2026-07-02-pump-prices",
        "economic_times",
        "news",
        "2026-07-02T08:15:00+05:30",
        "Petrol and diesel prices raised for the first time in 14 months",
        [
            "Oil marketing companies raised retail petrol and diesel prices by Rs 2 a litre on "
            "Wednesday, the first revision in 14 months, after marketing margins turned "
            "negative due to sustained high crude prices.",
            "The government has so far ruled out an excise duty cut, though officials said the "
            "option could be revisited if the Indian basket stays above $95.",
        ],
    ),
    (
        "mint-2026-08-07-trade",
        "mint",
        "news",
        "2026-08-07T13:25:00+05:30",
        "Trade deficit widens to $31.2 billion in July",
        [
            "The merchandise trade deficit widened to $31.2 billion in July from $27.8 billion "
            "a year earlier, driven by a higher oil import bill and a 12 per cent rise in gold "
            "imports.",
        ],
    ),
    (
        "bl-2026-09-18-bond-selloff",
        "businessline",
        "news",
        "2026-09-18T18:55:00+05:30",
        "Bond sell-off deepens as borrowing calendar lands",
        [
            "The 10-year government security yield rose 14 basis points to 7.42 per cent on "
            "Friday amid a heavier-than-expected second-half borrowing calendar.",
            "Banking system liquidity slipped into deficit for the third consecutive session, "
            "which could keep short-term rates elevated into October.",
        ],
    ),
]


def build_passages() -> tuple[list[Passage], dict[str, str]]:
    """Return the 20 passages plus the document texts their offsets index into."""
    passages: list[Passage] = []
    documents: dict[str, str] = {}

    for doc_id, source, kind, published, title, paragraphs in DOCUMENTS:
        doc_text = "\n\n".join(paragraphs)
        documents[doc_id] = doc_text

        cursor = 0
        for para_idx, paragraph in enumerate(paragraphs):
            start = doc_text.index(paragraph, cursor)
            end = start + len(paragraph)
            cursor = end
            passages.append(
                Passage(
                    passage_id=f"{doc_id}#p{para_idx}",
                    doc_id=doc_id,
                    source=source,
                    source_kind=kind,
                    url=None if kind == "official" else f"https://example.invalid/{doc_id}",
                    published_at=datetime.fromisoformat(published),
                    title=title,
                    text=paragraph,
                    para_idx=para_idx,
                    char_start=start,
                    char_end=end,
                    section="lede" if para_idx == 0 else "body",
                    licence_note="synthetic fixture, not real article text",
                )
            )
    return passages, documents


# ---------------------------------------------------------------------------
# Fixture graph: the Figure 1 example, with a 4-hop rupee chain
# ---------------------------------------------------------------------------

AS_OF = date(2026, 3, 20)

# (edge_id, src, dst, direction, strength, provenance, evidence passage, span)
EDGE_SPEC: list[tuple[str, str, str, str, str, str, str | None, str | None]] = [
    (
        "e1",
        "BRENT",
        "INDIAN_BASKET",
        "up",
        "direct",
        "source_asserted",
        "bl-2026-03-12-brent100#p1",
        "The Indian basket of crude rose to $98.4 a barrel due to the surge in Brent",
    ),
    (
        "e2",
        "INDIAN_BASKET",
        "IMPORT_BILL",
        "up",
        "direct",
        "source_asserted",
        "bs-2026-03-13-importbill#p0",
        "India's monthly import bill is expected to widen by about $2.5 billion because of "
        "the higher Indian basket price",
    ),
    ("e3", "IMPORT_BILL", "INR_USD", "up", "conditional", "model_inferred", None, None),
    ("e4", "INR_USD", "IMPORTED_INFLATION", "up", "conditional", "model_inferred", None, None),
    (
        "e5",
        "BRENT",
        "ATF_PRICE",
        "up",
        "direct",
        "source_asserted",
        "mint-2026-03-16-atf#p0",
        "raised aviation turbine fuel prices by 6.2 per cent this fortnight due to the rise "
        "in Brent crude",
    ),
    (
        "e6",
        "ATF_PRICE",
        "AIRLINE_COSTS",
        "up",
        "direct",
        "source_asserted",
        "mint-2026-03-16-atf#p1",
        "Fuel accounts for about 40 per cent of an Indian carrier's operating cost, so the "
        "increase feeds straight through to airline operating costs",
    ),
    (
        "e7",
        "AIRLINE_COSTS",
        "AIRLINE_SHARES",
        "down",
        "correlational",
        "source_asserted",
        "et-2026-03-17-aviation#p0",
        "Shares of listed Indian carriers fell between 3 and 5 per cent on Tuesday amid "
        "rising airline operating costs",
    ),
    (
        "e8",
        "BRENT",
        "CPI_HEADLINE",
        "up",
        "conditional",
        "source_asserted",
        "rbi-2026-03-18-mpc-minutes#p0",
        "the recent increase in international crude prices poses an upside risk to headline "
        "inflation",
    ),
    (
        "e9",
        "CPI_HEADLINE",
        "RATE_HIKE_EXPECTATIONS",
        "up",
        "conditional",
        "source_asserted",
        "rbi-2026-03-18-mpc-minutes#p1",
        "Should headline inflation stay above the upper tolerance band, the Committee may "
        "have to consider further tightening",
    ),
]

NODES = [
    ("BRENT", "up", "anchor, confirmed against the PPAC series", True, True, "brent_usd_bbl"),
    ("INDIAN_BASKET", "up", "PPAC series", False, True, "indian_basket_usd_bbl"),
    ("IMPORT_BILL", "up", "crude imports", False, False, None),
    ("INR_USD", "up", "weaker rupee", False, True, "inr_usd"),
    ("IMPORTED_INFLATION", "up", None, False, False, None),
    ("ATF_PRICE", "up", None, False, False, None),
    ("AIRLINE_COSTS", "up", None, False, False, None),
    ("AIRLINE_SHARES", "down", None, False, False, None),
    ("CPI_HEADLINE", "up", "inflation risk", False, False, None),
    ("RATE_HIKE_EXPECTATIONS", "up", None, False, False, None),
]

PATHS = [
    ("p-rupee", ["e1", "e2", "e3", "e4"]),
    ("p-airline", ["e5", "e6", "e7"]),
    ("p-cpi", ["e8", "e9"]),
]

HOPS = {"BRENT": 0}


def build_graph(by_passage: dict[str, Passage]) -> Graph:
    from schema.enums import Strength, weakest

    depth = {"BRENT": 0}
    edges: list[Edge] = []
    for edge_id, src, dst, direction, strength, provenance, passage_id, span in EDGE_SPEC:
        depth[dst] = depth[src] + 1
        evidence = by_passage.get(passage_id) if passage_id else None
        if span is not None:
            assert evidence is not None, f"{edge_id}: unknown passage {passage_id}"
            assert span in evidence.text, (
                f"{edge_id}: evidence span is not a verbatim substring of "
                f"{passage_id}\n  span: {span!r}\n  text: {evidence.text!r}"
            )
        edges.append(
            Edge(
                edge_id=edge_id,
                src_var=src,
                dst_var=dst,
                direction=direction,
                provenance=provenance,
                strength=strength,
                hop=depth[src] + 1,
                evidence_span=span,
                evidence_doc_id=evidence.doc_id if evidence else None,
                evidence_passage_id=evidence.passage_id if evidence else None,
                evidence_published_at=evidence.published_at if evidence else None,
                verified_by="rules+llm" if span else None,
                verdict="supported" if span else "unsupported",
                note=(
                    None if span else "no passage in corpus states this relation by the as-of date"
                ),
            )
        )

    by_id = {e.edge_id: e for e in edges}
    paths = []
    for path_id, edge_ids in PATHS:
        members = [by_id[e] for e in edge_ids]
        paths.append(
            GraphPath(
                path_id=path_id,
                edge_ids=edge_ids,
                weakest_strength=weakest([Strength(e.strength) for e in members]),
                fully_sourced=all(e.is_asserted for e in members),
                depth=len(edge_ids),
            )
        )

    return Graph(
        query_id="q-dev-001",
        anchor=Anchor(
            var="BRENT",
            direction="up",
            event="Brent crossed $100 a barrel on 12 March 2026",
            event_date=date(2026, 3, 12),
            confirmed_by_series=True,
            series_id="brent_usd_bbl",
        ),
        as_of=AS_OF,
        nodes=[
            GraphNode(
                var=var,
                direction=direction,
                label=label,
                is_anchor=is_anchor,
                confirmed_by_series=confirmed,
                series_id=series_id,
            )
            for var, direction, label, is_anchor, confirmed, series_id in NODES
        ],
        edges=edges,
        paths=paths,
        condition="M",
        run_id="run-fixture-0001",
        model="qwen3-8b-4bit",
        created_at=datetime.fromisoformat("2026-03-20T10:00:00+05:30"),
        notes=(
            "Synthetic fixture mirroring Figure 1 of the proposal. The rupee chain runs four "
            "hops and its last two hops are model-inferred; the airline chain is fully sourced."
        ),
    )


# ---------------------------------------------------------------------------
# Fixture run log: one M-condition run, 8 of 12 tool calls used
# ---------------------------------------------------------------------------


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_run_log(graph: Graph, by_passage: dict[str, Passage]) -> list[dict]:
    base = datetime.fromisoformat("2026-03-20T10:00:00+05:30")
    common = {"run_id": "run-fixture-0001", "query_id": "q-dev-001", "condition": "M"}

    def at(step: int, seconds: float) -> str:
        return (base + timedelta(seconds=seconds)).isoformat()

    def passage(pid: str) -> dict:
        return json.loads(by_passage[pid].model_dump_json())

    prompt_parse = "Identify the anchor event, its as-of date and the theme of this question."
    prompt_extract = "Extract events and candidate edges, using only the closed ontology."
    prompt_verify = "Does this passage state the relation, in this direction, at what strength?"

    lines: list[dict] = [
        {
            **common,
            "event": "model_call",
            "step": 0,
            "ts": at(0, 0),
            "purpose": "parse_query",
            "model": "qwen3-8b-4bit",
            "backend": "mlx",
            "temperature": 0.0,
            "prompt": prompt_parse,
            "prompt_sha256": _sha(prompt_parse),
            "completion": '{"anchor": "BRENT", "direction": "up", "as_of": "2026-03-20"}',
            "prompt_tokens": 412,
            "completion_tokens": 38,
            "latency_ms": 940.2,
            "json_valid": True,
        },
        {
            **common,
            "event": "tool_call",
            "step": 1,
            "ts": at(1, 2.1),
            "budget_remaining": 12,
            "call": {
                "call_id": "c1",
                "step": 1,
                "run_id": "run-fixture-0001",
                "query_id": "q-dev-001",
                "tool": "get_series",
                "args": {
                    "series_id": "brent_usd_bbl",
                    "start": "2026-03-01",
                    "end": "2026-03-20",
                    "as_of": "2026-03-20",
                },
            },
        },
        {
            **common,
            "event": "tool_result",
            "step": 1,
            "ts": at(1, 2.4),
            "new_passages": 0,
            "result": {
                "call_id": "c1",
                "tool": "get_series",
                "ok": True,
                "latency_ms": 31.0,
                "series_id": "brent_usd_bbl",
                "points": [
                    {"on": "2026-03-11", "value": 97.8},
                    {"on": "2026-03-12", "value": 100.6},
                    {"on": "2026-03-13", "value": 101.2},
                ],
                "move": "up",
            },
        },
        {
            **common,
            "event": "tool_call",
            "step": 2,
            "ts": at(2, 3.0),
            "budget_remaining": 11,
            "call": {
                "call_id": "c2",
                "step": 2,
                "run_id": "run-fixture-0001",
                "query_id": "q-dev-001",
                "tool": "search_corpus",
                "args": {
                    "query": "Brent $100 effects India crude import bill rupee inflation",
                    "k": 10,
                    "as_of": "2026-03-20",
                    "source_kind": "any",
                    "must_mention": [],
                },
            },
        },
        {
            **common,
            "event": "tool_result",
            "step": 2,
            "ts": at(2, 4.8),
            "new_passages": 4,
            "result": {
                "call_id": "c2",
                "tool": "search_corpus",
                "ok": True,
                "latency_ms": 1810.0,
                "passages": [
                    passage("bl-2026-03-12-brent100#p1"),
                    passage("bs-2026-03-13-importbill#p0"),
                    passage("mint-2026-03-16-atf#p0"),
                    passage("rbi-2026-03-18-mpc-minutes#p0"),
                ],
                "scores": [0.91, 0.84, 0.79, 0.71],
                "truncated": False,
            },
        },
        {
            **common,
            "event": "model_call",
            "step": 3,
            "ts": at(3, 6.0),
            "purpose": "extract",
            "model": "qwen3-8b-4bit",
            "backend": "mlx",
            "temperature": 0.0,
            "prompt": prompt_extract,
            "prompt_sha256": _sha(prompt_extract),
            "completion": '{"edges": ["e1", "e2", "e5", "e8"]}',
            "prompt_tokens": 3184,
            "completion_tokens": 266,
            "latency_ms": 6120.7,
            "json_valid": True,
        },
        {
            **common,
            "event": "tool_call",
            "step": 4,
            "ts": at(4, 13.0),
            "budget_remaining": 10,
            "call": {
                "call_id": "c3",
                "step": 4,
                "run_id": "run-fixture-0001",
                "query_id": "q-dev-001",
                "tool": "verify_edge",
                "args": {
                    "edge_id": "e1",
                    "passage_ids": ["bl-2026-03-12-brent100#p1"],
                    "as_of": "2026-03-20",
                },
            },
        },
        {
            **common,
            "event": "model_call",
            "step": 4,
            "ts": at(4, 13.2),
            "purpose": "verify",
            "model": "qwen3-8b-4bit",
            "backend": "mlx",
            "temperature": 0.0,
            "prompt": prompt_verify,
            "prompt_sha256": _sha(prompt_verify),
            "completion": '{"verdict": "supported", "strength": "direct", "direction": "up"}',
            "prompt_tokens": 907,
            "completion_tokens": 44,
            "latency_ms": 1180.3,
            "json_valid": True,
        },
        {
            **common,
            "event": "tool_result",
            "step": 4,
            "ts": at(4, 14.6),
            "new_passages": 0,
            "result": {
                "call_id": "c3",
                "tool": "verify_edge",
                "ok": True,
                "latency_ms": 1600.0,
                "edge_id": "e1",
                "verdict": "supported",
                "provenance": "source_asserted",
                "strength": "direct",
                "direction": "up",
                "evidence_span": EDGE_SPEC[0][7],
                "evidence_passage_id": "bl-2026-03-12-brent100#p1",
                "rule_failures": [],
            },
        },
        {
            **common,
            "event": "state",
            "step": 5,
            "ts": at(5, 15.0),
            "open_edges": ["e3", "e4"],
            "verified_edges": ["e1", "e2", "e5", "e8"],
            "searches_done": 1,
            "budget_remaining": 9,
            "next_action": "search_corpus for evidence on IMPORT_BILL -> INR_USD",
        },
        {
            **common,
            "event": "tool_call",
            "step": 6,
            "ts": at(6, 15.4),
            "budget_remaining": 9,
            "call": {
                "call_id": "c4",
                "step": 6,
                "run_id": "run-fixture-0001",
                "query_id": "q-dev-001",
                "tool": "search_corpus",
                "args": {
                    "query": "import bill rupee depreciation oil payments March 2026",
                    "k": 10,
                    "as_of": "2026-03-20",
                    "source_kind": "any",
                    "must_mention": ["IMPORT_BILL", "INR_USD"],
                },
            },
        },
        {
            **common,
            "event": "tool_result",
            "step": 6,
            "ts": at(6, 17.1),
            "new_passages": 0,
            "result": {
                "call_id": "c4",
                "tool": "search_corpus",
                "ok": False,
                "latency_ms": 1690.0,
                "error": {
                    "kind": "empty_result",
                    "message": "no passage on or before 2026-03-20 mentions both IMPORT_BILL and INR_USD",
                },
            },
        },
        {
            **common,
            "event": "tool_call",
            "step": 7,
            "ts": at(7, 17.5),
            "budget_remaining": 8,
            "call": {
                "call_id": "c5",
                "step": 7,
                "run_id": "run-fixture-0001",
                "query_id": "q-dev-001",
                "tool": "counter_search",
                "args": {
                    "dst_var": "INR_USD",
                    "direction": "up",
                    "exclude_src_vars": ["IMPORT_BILL"],
                    "k": 10,
                    "as_of": "2026-03-20",
                },
            },
        },
        {
            **common,
            "event": "tool_result",
            "step": 7,
            "ts": at(7, 19.0),
            "new_passages": 0,
            "result": {
                "call_id": "c5",
                "tool": "counter_search",
                "ok": True,
                "latency_ms": 1450.0,
                "passages": [],
                "competing_src_vars": [],
            },
        },
        {
            **common,
            "event": "tool_call",
            "step": 8,
            "ts": at(8, 19.4),
            "budget_remaining": 7,
            "call": {
                "call_id": "c6",
                "step": 8,
                "run_id": "run-fixture-0001",
                "query_id": "q-dev-001",
                "tool": "update_graph",
                "args": {
                    "op": "relabel_edge",
                    "edge_id": "e3",
                    "provenance": "model_inferred",
                    "strength": "conditional",
                    "reason": "two searches added nothing; no in-corpus passage states this link",
                },
            },
        },
        {
            **common,
            "event": "tool_result",
            "step": 8,
            "ts": at(8, 19.5),
            "new_passages": 0,
            "result": {
                "call_id": "c6",
                "tool": "update_graph",
                "ok": True,
                "latency_ms": 4.0,
                "applied": True,
                "graph_version": 4,
            },
        },
        {
            **common,
            "event": "tool_call",
            "step": 9,
            "ts": at(9, 19.9),
            "budget_remaining": 6,
            "call": {
                "call_id": "c7",
                "step": 9,
                "run_id": "run-fixture-0001",
                "query_id": "q-dev-001",
                "tool": "stop",
                "args": {
                    "reason": "two_searches_added_nothing",
                    "note": "e3 and e4 stay model-inferred; the other seven edges are verified",
                },
            },
        },
        {
            **common,
            "event": "tool_result",
            "step": 9,
            "ts": at(9, 20.0),
            "new_passages": 0,
            "result": {
                "call_id": "c7",
                "tool": "stop",
                "ok": True,
                "latency_ms": 1.0,
                "calls_used": 7,
                "open_edges_remaining": 2,
            },
        },
        {
            **common,
            "event": "stop",
            "step": 10,
            "ts": at(10, 20.2),
            "reason": "two_searches_added_nothing",
            "calls_used": 7,
            "open_edges_remaining": 2,
            "wall_clock_s": 20.2,
        },
    ]

    for number, line in enumerate(lines, start=1):
        try:
            parse_run_log_line(line)
        except Exception as exc:
            raise SystemExit(f"run log line {number} does not validate: {exc}") from exc
    return lines


# ---------------------------------------------------------------------------


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    passages, documents = build_passages()
    assert len(passages) == 20, f"expected 20 fixture passages, built {len(passages)}"
    by_passage = {p.passage_id: p for p in passages}

    (FIXTURES / "passages.jsonl").write_text(
        "".join(p.model_dump_json() + "\n" for p in passages), encoding="utf-8"
    )
    (FIXTURES / "documents.json").write_text(
        json.dumps(documents, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    graph = build_graph(by_passage)
    (FIXTURES / "graph_brent_hormuz.json").write_text(
        graph.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )

    run_log = build_run_log(graph, by_passage)
    (FIXTURES / "run_log.jsonl").write_text(
        "".join(json.dumps(line) + "\n" for line in run_log), encoding="utf-8"
    )

    print(f"{len(passages)} passages, {len(documents)} documents")
    print(f"graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges, {len(graph.paths)} paths")
    print(f"run log: {len(run_log)} lines")


if __name__ == "__main__":
    main()
