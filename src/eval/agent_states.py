"""Validation and scoring for frozen synthetic agent-state evaluations."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

VALID_TOOLS = {
    "search_corpus", "get_series", "verify_edge",
    "counter_search", "update_graph", "stop",
}


def load_states(path: str | Path) -> list[dict]:
    rows = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    validate_states(rows)
    return rows


def validate_states(rows: list[dict]) -> None:
    if not rows:
        raise ValueError("agent-state dataset is empty")
    ids = set()
    for row in rows:
        sid = row.get("state_id")
        if not sid or sid in ids:
            raise ValueError(f"missing or duplicate state_id: {sid!r}")
        ids.add(sid)
        if row.get("expected_tool") not in VALID_TOOLS:
            raise ValueError(f"invalid expected_tool for {sid}")
        if not isinstance(row.get("state"), dict):
            raise ValueError(f"state must be an object for {sid}")
        if not row.get("status"):
            raise ValueError(f"missing synthetic/gold-status disclosure for {sid}")


def score_actions(rows: list[dict], predictions: dict[str, str]) -> dict:
    """Score predicted tool names; absent predictions count as incorrect."""
    validate_states(rows)
    known = {row["state_id"] for row in rows}
    unknown = set(predictions) - known
    if unknown:
        raise ValueError(f"predictions contain unknown state IDs: {sorted(unknown)}")
    correct = sum(
        predictions.get(row["state_id"]) == row["expected_tool"] for row in rows
    )
    by_tool = {}
    for tool in sorted(VALID_TOOLS):
        subset = [r for r in rows if r["expected_tool"] == tool]
        hits = sum(predictions.get(r["state_id"]) == tool for r in subset)
        by_tool[tool] = {
            "correct": hits,
            "total": len(subset),
            "accuracy": hits / len(subset) if subset else None,
        }
    return {
        "dataset_size": len(rows),
        "predictions_supplied": len(predictions),
        "coverage": len(predictions) / len(rows),
        "correct": correct,
        "accuracy_all_states": correct / len(rows),
        "by_expected_tool": by_tool,
        "status": "synthetic scripted states; not human-reviewed gold",
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--states", default="data/eval/synthetic/agent_states.jsonl"
    )
    parser.add_argument(
        "--predictions",
        help="JSON object mapping state_id to predicted tool name",
    )
    args = parser.parse_args()
    rows = load_states(args.states)
    print(f"Validated {len(rows)} states.")
    print("Expected tools:", dict(Counter(r["expected_tool"] for r in rows)))
    if args.predictions:
        predictions = json.loads(
            Path(args.predictions).read_text(encoding="utf-8")
        )
        print(json.dumps(score_actions(rows, predictions), indent=2))


if __name__ == "__main__":
    main()
