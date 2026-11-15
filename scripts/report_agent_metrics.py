"""The agentic capability metrics, computed from run logs (proposal Table 4).

    PYTHONPATH=src python scripts/report_agent_metrics.py --runs runs/dev-gold-qwen3-8b

Table 4's Agentic row asks for four numbers. One of them, next-action accuracy
on the 40 frozen states, is scored separately against gold actions and is
already in Section 4.6. The other three are properties of real runs rather than
of scripted states, and `src/schema/runlog.py` says plainly where they come
from: "Every agentic metric (next-action accuracy, redundant-search rate, tool
calls per query) and the whole compute log are computed from these lines, so a
line that is not written is a number that cannot be reported."

This script computes those three:

* **tool calls per query** - `tool_call` lines per (condition, query), and the
  budget ceiling the controller was given.
* **redundant-search rate** - the share of search and counter-search calls whose
  result added **no passage** the run had not already seen. `new_passages` on
  the matching `tool_result` line is what records that. A redundant search is
  not an error; two of them in a row is a declared stop reason. The rate says
  how much of the budget went on ground already covered.
* **unresolved high-priority edges at stop** - `open_edges_remaining` on the
  `stop` line, beside the reason the controller gave. An agent that stops with
  edges still open may be budget-bound or may have decided they did not matter,
  and the stop reason is what separates those.

Nothing here judges support or grounding. These are controller-behaviour
numbers, and they are reported per condition because the ablations differ in
exactly this respect: A-NoLoop has no agent loop to measure.

`runs/**` is gitignored, so this runs where the sweep ran.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Calls that go looking for new evidence. `verify_edge` re-reads passages the
#: run already holds and `update_graph`/`stop`/`get_series` retrieve nothing, so
#: none of them can be redundant in this sense.
SEARCH_TOOLS = ("search_corpus", "counter_search")
LOOP_CONDITIONS = {"M", "A-NoVerify"}


def _lines(run_dir: Path) -> list[dict]:
    from eval.run_audit import audit

    checked = audit(runs=run_dir, corpus=REPO / "data/processed/articles.jsonl")
    if not checked["complete"]:
        raise ValueError(f"run audit failed: {checked['failures']}")
    # Read only the artifact-bound successful logs; orphaned attempts must not
    # silently add calls or stops to the completed sweep's denominators.
    paths = set()
    for artifact in sorted(run_dir.glob("*/*.json")):
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        if "graph" in payload:
            paths.add(artifact.parent / payload["log_file"])
    out: list[dict] = []
    for path in sorted(paths):
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                out.append(json.loads(raw))
    return out


def summarise(lines: list[dict]) -> dict[str, dict]:
    """Per condition: call counts, redundant-search rate, open edges at stop."""
    calls: dict[tuple[str, str], int] = defaultdict(int)
    searches: dict[str, int] = defaultdict(int)
    redundant: dict[str, int] = defaultdict(int)
    stops: dict[str, list[tuple[str, int]]] = defaultdict(list)
    queries: dict[str, set[str]] = defaultdict(set)

    # A tool_result carries no tool name, so pair it with the call that precedes
    # it in the same run at the same step.
    pending: dict[tuple[str, str, int], str] = {}

    for line in lines:
        condition = line.get("condition", "?")
        query_id = line.get("query_id", "?")
        event = line.get("event")
        queries[condition].add(query_id)

        if event == "tool_call":
            tool = (line.get("call") or {}).get("tool", "?")
            calls[(condition, query_id)] += 1
            if tool in SEARCH_TOOLS:
                searches[condition] += 1
                pending[(line.get("run_id", ""), query_id, line.get("step", -1))] = tool
        elif event == "tool_result":
            key = (line.get("run_id", ""), query_id, line.get("step", -1))
            if pending.pop(key, None) in SEARCH_TOOLS and not line.get("new_passages", 0):
                redundant[condition] += 1
        elif event == "stop":
            stops[condition].append(
                (line.get("reason", "?"), int(line.get("open_edges_remaining", 0)))
            )

    report: dict[str, dict] = {}
    for condition in sorted(queries):
        per_query = [calls[(condition, q)] for q in queries[condition]]
        ends = stops[condition]
        report[condition] = {
            "queries": len(queries[condition]),
            "tool_calls_total": sum(per_query),
            "tool_calls_per_query_mean": (
                round(sum(per_query) / len(per_query), 3) if per_query else None
            ),
            "tool_calls_per_query_max": max(per_query, default=None),
            "searches": searches[condition],
            "redundant_searches": redundant[condition],
            "redundant_search_rate": (
                round(redundant[condition] / searches[condition], 3)
                if searches[condition] and condition in LOOP_CONDITIONS
                else None
            ),
            "stops": len(ends),
            "open_edges_at_stop_total": sum(n for _, n in ends),
            "stops_with_open_edges": sum(1 for _, n in ends if n),
            "stop_reasons": dict(
                sorted((r, sum(1 for x, _ in ends if x == r)) for r in {r for r, _ in ends})
            ),
        }
    return report


def render(report: dict[str, dict], runs: Path) -> str:
    lines = [
        "# Agentic capability metrics (proposal Table 4)",
        "",
        "<!-- Generated by scripts/report_agent_metrics.py. Do not edit by hand. -->",
        "",
        f"Computed from the run logs under `{runs}`.",
        "",
        "Next-action accuracy is **not** here: it is scored against the 40 frozen "
        "states with gold actions and is reported in Section 4.6. These three are "
        "properties of real runs.",
        "",
        "| Condition | Queries | Tool calls/query (mean, max) | Searches | Redundant | "
        "Redundant rate | Stops with open edges |",
        "|---|---:|---|---:|---:|---:|---|",
    ]
    if (runs / "inputs.json").is_file():
        lines[6:6] = [
            "Only completed, checksum-bound logs are included; the full run audit passed.",
            f"Inputs SHA-256: `{hashlib.sha256((runs / 'inputs.json').read_bytes()).hexdigest()}`.",
            f"Artifact receipt SHA-256: `{hashlib.sha256((runs / 'artifacts.json').read_bytes()).hexdigest()}`.",
            "",
        ]
    for condition, row in report.items():
        mean, top = row["tool_calls_per_query_mean"], row["tool_calls_per_query_max"]
        calls = "n/a" if mean is None else f"{mean} / {top}"
        rate = "n/a" if row["redundant_search_rate"] is None else f"{row['redundant_search_rate']}"
        lines.append(
            f"| {condition} | {row['queries']} | {calls} | {row['searches']} | "
            f"{row['redundant_searches']} | {rate} | "
            f"{row['stops_with_open_edges']} of {row['stops']} "
            f"({row['open_edges_at_stop_total']} edges) |"
        )
    lines += ["", "## Stop reasons", ""]
    for condition, row in report.items():
        reasons = row["stop_reasons"] or {"(no stop line)": 0}
        shown = ", ".join(f"`{r}` x{n}" for r, n in reasons.items())
        lines.append(f"- **{condition}**: {shown}")
    lines += [
        "",
        "## How to read this",
        "",
        "A redundant search is not an error. The controller's own declared stop "
        "condition is two searches adding nothing, so some redundancy is the "
        "mechanism working. The rate says how much of a bounded budget went on "
        "ground already covered.",
        "",
        "Open edges are unchecked inferred edges (no verifier verdict), not every "
        "unsupported edge. The controller orders all open edges shallow-first; it "
        "has no separate binary high-priority threshold, so these counts cover the "
        "entire priority queue. Checked rejections are resolved for this controller. "
        "Read the count beside the stop reason: `budget_exhausted` with open edges "
        "means the budget prevented completion. Fixed prose/prompted baselines do "
        "not run this controller; their stop labels do not indicate that it judged "
        "remaining edges unimportant.",
        "",
        "Conditions without an agent loop (A-NoLoop and the fixed baselines) "
        "retrieve at most once per query, so their redundant-search rate is undefined rather than "
        "zero.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True, help="a sweep output directory")
    parser.add_argument("--report", type=Path, default=REPO / "reports/agent_metrics.md")
    parser.add_argument("--json", type=Path, help="also write the raw numbers here")
    args = parser.parse_args(argv)

    if not args.runs.is_dir():
        raise SystemExit(f"{args.runs} is not a directory; runs/** is gitignored")
    lines = _lines(args.runs)
    if not lines:
        raise SystemExit(f"no .jsonl run-log lines under {args.runs}")

    report = summarise(lines)
    if not report:
        raise SystemExit("run logs carry no condition field; nothing to group by")

    text = render(report, args.runs)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(text, encoding="utf-8")
    print(f"wrote {args.report}")
    if args.json:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
