"""Draft the B4 reviewer evidence graphs from the corpus, span-exact (issue #15).

    python scripts/draft_gold_graphs.py [--check]

**These drafts are not yet a gold standard.** `src/eval/gold.py` says a gold
graph has to be read out of the corpus by a person, because a generated
standard measures its generator. That still holds. What this script does is the
mechanical half, so the human half is cheap and auditable:

* every span is **sliced out of the real passage text** between two markers, so
  no span is retyped and none can drift from the corpus;
* every edge is run through the B6 rule layer before it is written, so a draft
  that cannot be confirmed verbatim never reaches disk;
* `notes` on each graph records that it is machine-drafted and pending
  adjudication, and `note` on an edge flags the calls a reviewer must settle.

What it cannot do is judge. Three candidates were dropped by hand that this
script would happily have written: two cited passages that mention both
variables but assert no relation between them (a list of risks the RBI watches
is not an edge), and one whose causation ran the other way (portfolio outflows
pressuring the rupee, not the rupee driving outflows). Adjudication means
reading every span and asking those three questions again.

`--check` rewrites nothing and fails if any draft on disk differs.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from eval.gold import check_against_corpus
from schema import Anchor, Direction, Edge, Graph, GraphNode, Passage
from verify import load_aliases

REPO = Path(__file__).resolve().parent.parent
CORPUS = REPO / "data/processed/articles.jsonl"
QUERIES = REPO / "data/eval/queries_dev.jsonl"
GOLD_DIR = REPO / "data/eval/gold/dev"
SHEET = GOLD_DIR / "ADJUDICATION.md"

#: edge_id, src, dst, direction, strength, hop, passage_id, first marker, last
#: marker, reviewer note. The markers bracket the span inside the passage text;
#: the span is `text[text.find(first) : text.find(last) + len(last)]`.
DRAFTS: dict[str, tuple[tuple, ...]] = {
    "dev-oil-why": (
        (
            "ow1",
            "BRENT",
            "IMPORT_BILL",
            "up",
            "direct",
            1,
            "businessline-17ada433751a4c30c372#p5",
            "Higher crude prices pose",
            "import costs",
            None,
        ),
        (
            "ow2",
            "BRENT",
            "CURRENT_ACCOUNT_DEFICIT",
            "up",
            "conditional",
            1,
            "businessline-33adbc66dad6bae05630#p2",
            "For an oil-importing country",
            "current account deficit",
            None,
        ),
        (
            "ow3",
            "IMPORT_BILL",
            "INR_USD",
            "up",
            "conditional",
            2,
            "businessline-8d4a51b1a94c055d07e3#p2",
            "If the war lingers",
            "weakening of the currency.",
            None,
        ),
        (
            "ow4",
            "BRENT",
            "INR_USD",
            "up",
            "direct",
            1,
            "businessline-469aabd081e5b5594ab2#p0",
            "The rupee and Government Securities",
            "rising crude oil prices",
            None,
        ),
        (
            "ow5",
            "BRENT",
            "TRADE_DEFICIT",
            "up",
            "conditional",
            1,
            "economic_times-4fa40d8770c821dd5406#p9",
            "Higher oil prices linked",
            "if the trend persists.",
            None,
        ),
    ),
    "dev-oil-effects": (
        (
            "oe1",
            "BRENT",
            "FUEL_PRICES",
            "up",
            "conditional",
            1,
            "economic_times-24ec1e6a8dff7543b074#p6",
            "If crude sustains above",
            "may follow.",
            None,
        ),
        (
            "oe2",
            "BRENT",
            "CPI_HEADLINE",
            "up",
            "conditional",
            1,
            "economic_times-24ec1e6a8dff7543b074#p6",
            "A $10 per barrel increase",
            "passed on to consumers",
            None,
        ),
        (
            "oe3",
            "BRENT",
            "OMC_MARGINS",
            "down",
            "direct",
            1,
            "economic_times-24ec1e6a8dff7543b074#p6",
            "Retail auto fuel prices",
            "absorbing price shocks.",
            "ADJUDICATE: the span asserts margins absorb price shocks without naming a "
            "direction. 'down' is read off the anchor (crude up). Reject the edge if you "
            "think the direction has to be stated in the span itself.",
        ),
        (
            "oe4",
            "BRENT",
            "FISCAL_DEFICIT",
            "up",
            "conditional",
            1,
            "economic_times-24ec1e6a8dff7543b074#p6",
            "A $10 per barrel increase",
            "opts to cut taxes.",
            "Span contains oe2's. One sentence offers CPI or the fiscal deficit as "
            "alternatives; both are asserted, conditionally.",
        ),
        (
            "oe5",
            "BRENT",
            "ATF_PRICE",
            "up",
            "direct",
            1,
            "economic_times-015f8f79fd464ee060d8#p6",
            "Indian OMCs revise ATF prices",
            "plus logistics costs.",
            "ADJUDICATE: the span states the ATF pricing formula rather than an observed "
            "move. Mechanical, unhedged, hence 'direct'.",
        ),
        (
            "oe10",
            "ATF_PRICE",
            "AIRFARES",
            "up",
            "conditional",
            2,
            "economic_times-4a678f4564789fcceb8e#p0",
            "Airfares are expected to rise",
            "West Asia conflict.",
            None,
        ),
    ),
    "dev-rupee-why": (
        (
            "rw1",
            "INR_USD",
            "IMPORTED_INFLATION",
            "up",
            "direct",
            1,
            "economic_times-1b2732b34ee05b32bf50#p1",
            "The weakening rupee is amplifying",
            "imported inflation.",
            None,
        ),
        (
            "rw2",
            "INR_USD",
            "IMPORT_BILL",
            "up",
            "direct",
            1,
            "economic_times-1b2732b34ee05b32bf50#p11",
            "A depreciating rupee increases the domestic cost of imports",
            "especially crude oil",
            None,
        ),
        (
            "rw3",
            "IMPORT_BILL",
            "IMPORTED_INFLATION",
            "up",
            "direct",
            2,
            "economic_times-1b2732b34ee05b32bf50#p11",
            "increases the domestic cost of imports",
            "reinforcing inflationary pressures.",
            "Same sentence as rw2. It states rupee -> import cost -> inflationary pressures, "
            "so the middle link is asserted, not inferred.",
        ),
        (
            "rw9",
            "IMPORT_BILL",
            "FUEL_PRICES",
            "up",
            "conditional",
            2,
            "economic_times-6339c59bc47085648592#p12",
            "pushing the landed import cost",
            "current fuel price hike",
            None,
        ),
    ),
    "dev-rupee-effects": (
        (
            "re1",
            "INR_USD",
            "IMPORT_BILL",
            "up",
            "direct",
            1,
            "economic_times-95de6ff7f5c97ba82245#p2",
            "The urgency has grown after the rupee",
            "eroding investors",
            None,
        ),
        (
            "re2",
            "INR_USD",
            "RBI_FX_INTERVENTION",
            "up",
            "direct",
            1,
            "economic_times-76f04bc5898c1c59b89a#p2",
            "as the rupee came under pressure",
            "through dollar sales.",
            None,
        ),
        (
            "re3",
            "INR_USD",
            "IMPORTED_INFLATION",
            "up",
            "direct",
            1,
            "economic_times-1b2732b34ee05b32bf50#p1",
            "The weakening rupee is amplifying",
            "imported inflation.",
            "Same edge and span as rw1 in dev-rupee-why. The two questions share one "
            "mechanism over one episode; that overlap is expected, not a duplicate.",
        ),
        (
            "re4",
            "IMPORT_BILL",
            "FISCAL_DEFICIT",
            "up",
            "correlational",
            2,
            "economic_times-4b42a45c8f9ff3e13586#p0",
            "rising import bill were fuelling",
            "the fiscal deficit",
            "'were fuelling worries about' is reported concern, not an asserted move, "
            "hence correlational.",
        ),
        (
            "re11",
            "INR_USD",
            "FUEL_PRICES",
            "up",
            "conditional",
            1,
            "economic_times-6339c59bc47085648592#p12",
            "Thus, the rupee has already approached",
            "domestic fuel price revisions.",
            None,
        ),
    ),
}

PROVENANCE = (
    "MACHINE-DRAFTED, NOT YET ADJUDICATED. Spans are sliced verbatim from "
    "data/processed/articles.jsonl by scripts/draft_gold_graphs.py and each edge "
    "passes the B6 rule layer. Edge selection, direction and strength have not been "
    "confirmed by a human reviewer, and issue #37's Cohen's kappa still requires two "
    "independent annotators. Treat every number measured against this as provisional "
    "until data/eval/gold/dev/ADJUDICATION.md records sign-off."
)


def _sheet(graphs: list[Graph]) -> str:
    """The reviewer's sign-off sheet, generated so it cannot drift from the files."""
    lines = [
        "# Adjudication sheet - the dev four (B4, issue #15)",
        "",
        "<!-- Generated by scripts/draft_gold_graphs.py. Do not edit by hand. -->",
        "",
        "Every edge below is machine-drafted, span-exact and passes the B6 rule layer.",
        "**None of it is adjudicated.** The rule layer confirms a span is verbatim and",
        "that the passage mentions both variables; it cannot tell whether the passage",
        "*asserts the relation*, which way the causation runs, or whether the strength",
        "label matches the language. Those three are the reviewer's job.",
        "",
        "## For each edge, three questions",
        "",
        "1. **Does the span assert this relation?** A passage that mentions both",
        "   variables without linking them is not evidence. Three candidates were",
        "   dropped for exactly this before the drafts were written.",
        "2. **Does the causation run src -> dst?** One candidate was dropped because it",
        "   ran backwards (outflows pressuring the rupee, read as the rupee driving",
        "   outflows).",
        "3. **Does the strength match the language?** `direct` for unhedged, `conditional`",
        '   for hedged ("could", "may", "if"), `correlational` for co-occurrence',
        '   ("amid", "as", "after"). See `docs/annotation_guide.md`.',
        "",
        "Mark each row `keep`, `fix <what>` or `drop`. An edge dropped by a reviewer is a",
        "correct outcome, not a loss: the gold standard is the set of links a source",
        "states, not the set that is true.",
        "",
        "## Two annotators, not one",
        "",
        "Issue #37 needs Cohen's kappa, so **at least one of these four graphs must be",
        "adjudicated independently by two people who have not compared notes**. Agreement",
        "measured on a sheet one person signed twice is not agreement. Record who did",
        "which graph, and on what date, at the bottom of this file.",
        "",
    ]
    for graph in graphs:
        lines += [
            f"## {graph.query_id}",
            "",
            f"Anchor **{graph.anchor.var} {graph.anchor.direction.value}** - "
            f"{graph.anchor.event} ({graph.anchor.event_date}). As-of **{graph.as_of}**.",
            "",
        ]
        for edge in graph.edges:
            lines += [
                f"### `{edge.edge_id}`  {edge.src_var} -> {edge.dst_var} "
                f"({edge.direction.value}, {edge.strength.value}, hop {edge.hop})",
                "",
                f"> {edge.evidence_span}",
                "",
                f"`{edge.evidence_passage_id}` - "
                f"{edge.evidence_published_at.date() if edge.evidence_published_at else '?'}",
                "",
            ]
            if edge.note:
                lines += [f"**Drafter's note.** {edge.note}", ""]
            lines += [
                "| asserts relation? | direction? | strength? | verdict |",
                "|---|---|---|---|",
                "|  |  |  |  |",
                "",
            ]
    lines += [
        "---",
        "",
        "## Sign-off",
        "",
        "| graph | annotator | date | verdict |",
        "|---|---|---|---|",
        *(f"| {g.query_id} |  |  |  |" for g in graphs),
        "",
        "Until a row here is filled in, every number measured against these graphs is",
        "provisional and the mid report must say so.",
    ]
    return "\n".join(line.rstrip() for line in lines).rstrip() + "\n"


def _queries() -> dict[str, dict]:
    return {
        (q := json.loads(line))["query_id"]: q
        for line in QUERIES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def _passages() -> list[Passage]:
    return [
        Passage.model_validate_json(line)
        for line in CORPUS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _slice(passage: Passage, first: str, last: str, edge_id: str) -> str:
    start = passage.text.find(first)
    end = passage.text.find(last)
    if start < 0 or end < 0:
        missing = "first" if start < 0 else "last"
        raise SystemExit(f"{edge_id}: {missing} marker not found in {passage.passage_id}")
    if end < start:
        raise SystemExit(f"{edge_id}: last marker precedes first in {passage.passage_id}")
    return passage.text[start : end + len(last)]


def _build(query_id: str, query: dict, by_id: dict[str, Passage]) -> Graph:
    anchor = Anchor.model_validate(query["anchor"])
    edges: list[Edge] = []
    for edge_id, src, dst, direction, strength, hop, pid, first, last, note in DRAFTS[query_id]:
        passage = by_id.get(pid)
        if passage is None:
            raise SystemExit(f"{edge_id}: passage {pid} is not in the corpus")
        edges.append(
            Edge(
                edge_id=edge_id,
                src_var=src,
                dst_var=dst,
                direction=direction,
                provenance="source_asserted",
                strength=strength,
                hop=hop,
                evidence_span=_slice(passage, first, last, edge_id),
                evidence_doc_id=passage.doc_id,
                evidence_passage_id=passage.passage_id,
                evidence_published_at=passage.published_at,
                note=note,
            )
        )

    # One node per variable. A node's direction is the move attributed to it by
    # the edge that points at it; the anchor keeps the anchor's own direction.
    into: dict[str, Direction] = {e.dst_var: e.direction for e in edges}
    variables = {anchor.var} | {e.src_var for e in edges} | {e.dst_var for e in edges}
    nodes = [
        GraphNode(
            var=var,
            direction=anchor.direction if var == anchor.var else into[var],
            is_anchor=var == anchor.var,
            confirmed_by_series=anchor.confirmed_by_series if var == anchor.var else False,
            series_id=anchor.series_id if var == anchor.var else None,
        )
        for var in sorted(variables)
    ]
    return Graph(
        query_id=query_id,
        anchor=anchor,
        as_of=date.fromisoformat(query["as_of"]),
        nodes=nodes,
        edges=edges,
        notes=PROVENANCE,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="rewrite nothing; fail if stale")
    args = parser.parse_args(argv)

    if not CORPUS.is_file():
        raise SystemExit(f"{CORPUS.relative_to(REPO)} not found; see data/processed/MANIFEST.md")

    queries = _queries()
    passages = _passages()
    by_id = {p.passage_id: p for p in passages}
    table = load_aliases()

    stale, failed, built = [], 0, []
    for query_id in DRAFTS:
        graph = _build(query_id, queries[query_id], by_id)
        report = check_against_corpus(graph, passages, aliases=table)
        if not report.ok:
            failed += 1
            print(f"  FAILED  {query_id}")
            for issue in report.issues:
                print(f"            [{issue.edge_id}] {issue.problem}")
            continue

        built.append(graph)
        body = graph.model_dump_json(indent=2, exclude_none=True) + "\n"
        path = GOLD_DIR / f"{query_id}.json"
        current = path.read_text(encoding="utf-8") if path.is_file() else None
        hops = ", ".join(f"hop {e.hop}" for e in graph.edges)
        if args.check:
            if current != body:
                stale.append(query_id)
            print(f"  ok      {query_id}  ({len(graph.edges)} edges: {hops})")
        else:
            path.write_text(body, encoding="utf-8")
            print(f"  wrote   {query_id}  ({len(graph.edges)} edges: {hops})")

    if failed:
        print(f"\n{failed} draft(s) failed the rule layer; nothing written for them")
        return 1

    sheet = _sheet(built)
    if args.check:
        on_disk = SHEET.read_text(encoding="utf-8") if SHEET.is_file() else None
        if on_disk != sheet:
            stale.append(SHEET.name)
    else:
        SHEET.write_text(sheet, encoding="utf-8")
        print(f"  wrote   {SHEET.relative_to(REPO)}")
    if stale:
        print(f"\nstale on disk: {', '.join(stale)} - re-run without --check")
        return 1
    print(f"\n{len(DRAFTS)} drafts {'checked' if args.check else 'written'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
