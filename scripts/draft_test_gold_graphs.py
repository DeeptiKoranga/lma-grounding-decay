"""Draft the test-half reviewer evidence graphs from the corpus, span-exact (#38).

    PYTHONPATH=src python scripts/draft_test_gold_graphs.py [--check]

This is the test-set counterpart of `scripts/draft_gold_graphs.py` and it is a
separate file on purpose. The dev script writes `data/eval/gold/dev`, which is
adjudicated and bound by a signed receipt whose hash covers those bytes
(Section 4.4); nothing that regenerates the test half should be able to touch
it by accident.

**These graphs were adjudicated on 11 November 2026 (D-30).** This script is the
mechanical half of the job, exactly as on the dev side: every span is sliced
out of the real passage text between two markers so no span is retyped, and
every edge is run through the B6 rule layer before it reaches disk. What the
rule layer cannot do is judge whether the passage asserts the relation, in
which direction, or whether it is about India. Two annotators have to read
every span and settle that, under D-26.

`--check` rewrites nothing and fails if any draft on disk differs.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from eval.gold import check_against_corpus
from schema import Anchor, Direction, Edge, Graph, GraphNode, Passage

REPO = Path(__file__).resolve().parent.parent
CORPUS = REPO / "data/processed/articles.jsonl"
QUERIES = REPO / "data/eval/queries_test.jsonl"
GOLD_DIR = REPO / "data/eval/gold/test"
SHEET = GOLD_DIR / "ADJUDICATION.md"

#: edge_id, src, dst, direction, strength, hop, passage_id, first marker, last
#: marker, reviewer note. The markers bracket the span inside the passage text;
#: the span is `text[text.find(first) : text.find(last) + len(last)]`.
#:
#: `test-cpi-why` has no entry. D-27 established it cannot be answered from this
#: corpus: its target is paired with headline CPI in exactly one passage on or
#: before the as-of date, that passage is Federal Reserve coverage, and it runs
#: the wrong way. `test-cpi-effects` has no entry either, for a reason found
#: only by reading - see TEST_CPI_EFFECTS_FINDING below.
DRAFTS: dict[str, tuple[tuple, ...]] = {
    "test-fpi-why": (
        (
            "tw1",
            "FPI_FLOWS",
            "INR_USD",
            "up",
            "direct",
            1,
            "businessline-469aabd081e5b5594ab2#p4",
            "the rupee is under pressure as",
            "continuing",
            "Three causes are listed together and FPI selling is one of them. A "
            "reviewer must decide whether 'on account of' attributes the pressure "
            "to FPI selling directly or only lists it alongside two others.",
        ),
        (
            "tw3",
            "INR_USD",
            "IMPORT_BILL",
            "up",
            "conditional",
            2,
            "economic_times-6a4582bc53bfe30b98f6#p5",
            "A sustained depreciation in the rupee",
            "inflate the import bill",
            "Hypothetical ('would'), so drafted conditional. Do not upgrade it.",
        ),
        (
            "tw4",
            "INR_USD",
            "CURRENT_ACCOUNT_DEFICIT",
            "up",
            "conditional",
            2,
            "economic_times-6a4582bc53bfe30b98f6#p5",
            "A sustained depreciation in the rupee",
            "current account deficit",
            "Same sentence as tw3 and tw5. One span, three destinations: check "
            "that each destination's move is stated, not just listed.",
        ),
        (
            "tw5",
            "INR_USD",
            "FISCAL_DEFICIT",
            "up",
            "conditional",
            2,
            "economic_times-6a4582bc53bfe30b98f6#p5",
            "A sustained depreciation in the rupee",
            "fiscal deficit",
            "'widen both the current account deficit and fiscal deficit' - the verb "
            "is shared. A reviewer may read the fiscal leg as weaker than the "
            "current-account leg.",
        ),
    ),
    "test-fpi-effects": (
        (
            "te1",
            "FPI_FLOWS",
            "INR_USD",
            "up",
            "correlational",
            1,
            "businessline-6a0ed15b9a4761115dc7#p1",
            "The rupee closed at a new low",
            "strengthening Dollar",
            "'amid' lists three conditions and asserts no mechanism. Drafted "
            "correlational on the annotation guide's own reading of 'amid'.",
        ),
        (
            "te3",
            "INR_USD",
            "IMPORT_BILL",
            "up",
            "conditional",
            2,
            "economic_times-6a4582bc53bfe30b98f6#p5",
            "A sustained depreciation in the rupee",
            "inflate the import bill",
            "Hypothetical ('would'), so drafted conditional.",
        ),
        (
            "te4",
            "INR_USD",
            "CURRENT_ACCOUNT_DEFICIT",
            "up",
            "conditional",
            2,
            "economic_times-6a4582bc53bfe30b98f6#p5",
            "A sustained depreciation in the rupee",
            "current account deficit",
            "Hypothetical ('would'), so drafted conditional.",
        ),
        (
            "te5",
            "INR_USD",
            "FISCAL_DEFICIT",
            "up",
            "conditional",
            2,
            "economic_times-6a4582bc53bfe30b98f6#p5",
            "A sustained depreciation in the rupee",
            "fiscal deficit",
            "Shared verb across two deficits; see tw5.",
        ),
    ),
}

#: Why `test-cpi-effects` is absent, recorded here because the next person to
#: read the feasibility audit will expect it to be draftable.
#:
#: `reports/test_gold_feasibility.md` reports 28 variables co-occurring with
#: `CPI_HEADLINE` and concludes there are "enough distinct partners to reach 4
#: edges, if the passages assert relations". That audit counts co-occurrence
#: only, and says so. Reading the passages shows the condition fails: in this
#: corpus Indian headline CPI is almost always the **destination** of the oil
#: shock, not its source. `BRENT`, `FUEL_PRICES`, `CPI_FOOD`, `CPI_CORE` and
#: `WPI` all run *into* CPI, and an effects graph rooted at CPI cannot use them.
#: What survives in the CPI-as-cause direction is CPI -> REPO_RATE (up), stated
#: conditionally in `mint-74467ebbc52e72308935#p5` and
#: `businessline-eb43f44f9ee97cd0dd7b#p1`, and a possible hop-2 REPO_RATE ->
#: GDP_GROWTH whose destination the alias table does not match on the bare word
#: "growth". That is one or two edges against `MIN_EDGES` of 4.
TEST_CPI_EFFECTS_FINDING = (
    "test-cpi-effects is not drafted. The feasibility audit's partner count is "
    "a co-occurrence count, and reading the passages shows this corpus treats "
    "Indian headline CPI as an effect of the oil shock rather than a cause, so "
    "an effects graph rooted at CPI reaches one or two edges, not MIN_EDGES."
)

PROVENANCE = (
    "ADJUDICATED 2026-11-11. Spans are sliced verbatim from "
    "data/processed/articles.jsonl by scripts/draft_test_gold_graphs.py and each "
    "edge passes the B6 rule layer. Two annotators then labelled every drafted "
    "edge independently, blind to the draft and to each other: raw agreement "
    "1.000 on whether the span asserts the relation (Cohen's kappa 1.000) and "
    "1.000 on direction, with kappa undefined there because one label was used "
    "throughout. Strength agreed on 1 of 8 (raw 0.125, kappa 0.000), and the "
    "pre-declared direct-versus-hedged collapse did not rescue it because that "
    "is the axis of the split (reports/adjudication_kappa_test.md). "
    "Reconciliation applied one rule, D-30: strength is read off the modality of "
    "the clause carrying the causal claim, not off the manner in which the "
    "mechanism is described, so a claim under 'would' is conditional however "
    "firmly the mechanism inside it is worded. Both annotators independently "
    "rejected the same two FPI_FLOWS -> GSEC_10Y edges, which are dropped, "
    "leaving four edges per graph at exactly MIN_EDGES. The reviewers' "
    "attestation lives in data/eval/gold/test/review_receipt.json and is signed "
    "separately. Two of the four test queries carry no graph at all: "
    "test-cpi-why by D-27, and test-cpi-effects by D-27a."
)


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

    into: dict[str, Direction] = {e.dst_var: e.direction for e in edges}
    variables = {anchor.var} | {e.src_var for e in edges} | {e.dst_var for e in edges}

    def direction_of(var: str) -> Direction:
        if var == anchor.var:
            return anchor.direction
        if var in into:
            return into[var]
        raise AssertionError(
            f"{query_id}: {var} has no inbound edge, so its node direction would be "
            "a guess. Add the edge that states its move, or drop the edges leaving it."
        )

    nodes = [
        GraphNode(
            var=var,
            direction=direction_of(var),
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


def _sheet(graphs: list[Graph]) -> str:
    lines = [
        "# Adjudicated test gold - the two queries this corpus supports (#38)",
        "",
        "<!-- Generated by scripts/draft_test_gold_graphs.py. Do not edit by hand. -->",
        "",
        "> **Do not read this file before you annotate.** It prints the drafter's own",
        "> labels, and reading them first turns your agreement with the other annotator",
        "> into agreement with the draft. The kappa would then measure how persuasive",
        "> the draft was, which is not recoverable afterwards. Work from your blind",
        "> worksheet in `adjudication/` and come back here for the comparison once both",
        "> sheets are committed.",
        "",
        "Every edge below was machine-drafted, span-exact and passed the B6 rule layer,",
        "then labelled independently by two annotators and reconciled under D-30.",
        "The two edges they both rejected are gone; what remains is four per graph,",
        "exactly MIN_EDGES. Agreement figures are in reports/adjudication_kappa_test.md",
        "and the attestation is signed separately in review_receipt.json.",
        "",
        f"Two of the four test queries carry no graph. {TEST_CPI_EFFECTS_FINDING}",
        "`test-cpi-why` is excluded by D-27.",
        "",
    ]
    for graph in graphs:
        lines += [
            f"## `{graph.query_id}`",
            "",
            f"Anchor `{graph.anchor.var}` {graph.anchor.direction.value}, cutoff {graph.as_of}, "
            f"{len(graph.edges)} edges.",
            "",
            "| edge | claim | strength | hop | passage | span |",
            "|---|---|---|---:|---|---|",
        ]
        for edge in graph.edges:
            span = edge.evidence_span.replace("|", "\\|")
            lines.append(
                f"| `{edge.edge_id}` | {edge.src_var} -> {edge.dst_var} "
                f"({edge.direction.value}) | {edge.strength.value} | {edge.hop} | "
                f"`{edge.evidence_passage_id}` | {span} |"
            )
        lines.append("")
        for edge in graph.edges:
            if edge.note:
                lines.append(f"- **`{edge.edge_id}`** - {edge.note}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if not CORPUS.is_file():
        raise SystemExit(f"corpus not found at {CORPUS}; it is not in git")

    passages = [
        Passage.model_validate_json(line)
        for line in CORPUS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {p.passage_id: p for p in passages}
    queries = {
        json.loads(line)["query_id"]: json.loads(line)
        for line in QUERIES.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    graphs = []
    for query_id in DRAFTS:
        if query_id not in queries:
            raise SystemExit(f"{query_id} is not in {QUERIES}")
        graph = _build(query_id, queries[query_id], by_id)
        report = check_against_corpus(graph, passages)
        if not report.ok:
            print(f"{query_id}: rule layer rejected the draft")
            for issue in report.issues:
                print(f"  [{issue.edge_id}] {issue.problem}")
            return 1
        graphs.append(graph)

    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    for graph in graphs:
        path = GOLD_DIR / f"{graph.query_id}.json"
        payload = graph.model_dump_json(indent=2, exclude_none=True) + "\n"
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != payload:
                failures.append(path)
        else:
            path.write_text(payload, encoding="utf-8")
        print(f"{'checked' if args.check else 'wrote'} {path.relative_to(REPO)}")

    sheet = _sheet(graphs)
    if args.check:
        if not SHEET.is_file() or SHEET.read_text(encoding="utf-8") != sheet:
            failures.append(SHEET)
    else:
        SHEET.write_text(sheet, encoding="utf-8")

    if failures:
        for path in failures:
            print(f"DIFFERS: {path.relative_to(REPO)}")
        return 1

    print(
        f"\n{len(graphs)} test graphs {'checked' if args.check else 'written'}; adjudicated (D-30)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
