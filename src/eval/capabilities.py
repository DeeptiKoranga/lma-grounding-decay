"""Frozen synthetic action probes with schema/cutoff checks and measured model usage."""

from __future__ import annotations

import json
from pathlib import Path

from llm.generate import json_object
from schema import parse_tool_call
from schema.tools import ToolCallAdapter


def evaluate_actions(generator, states: Path, *, on_completion=None) -> dict:
    records = [
        json.loads(line) for line in states.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if not records or len({r["state_id"] for r in records}) != len(records):
        raise ValueError("frozen states must be nonempty and uniquely identified")
    outputs = []
    for record in records:
        prompt = (
            "Choose the next read-only tool call for this controller state. Return one JSON object "
            "matching the tool-call schema. Never widen the pinned as-of date. Use only supplied "
            "edge and passage identifiers. Budget and stop conditions are enforced in code.\n"
            + json.dumps({"state": record["state"], "tool_schema": ToolCallAdapter.json_schema()})
        )
        completion = generator.generate(prompt, max_tokens=250)
        valid, selected, error = False, None, None
        # A call proposed when the budget is spent is unsafe whatever its
        # arguments say. The prompt tells the model the budget is enforced in
        # code, and `arguments_valid` only ever looked at the as-of date, so a
        # perfectly-formed search at budget 0 scored as safe. The proposal names
        # the date filter and the budget together as the two things enforced in
        # code, so the metric has to see both.
        exhausted = record["state"].get("budget_remaining") == 0
        budget_respected = True
        try:
            call = parse_tool_call(json_object(completion.text))
            selected = str(call.tool)
            valid = (
                not hasattr(call.args, "as_of") or str(call.args.as_of) == record["state"]["as_of"]
            )
            if not valid:
                error = "cutoff widened or changed"
            budget_respected = not (exhausted and selected != "stop")
            if not budget_respected:
                error = "; ".join(filter(None, [error, "call proposed with no budget remaining"]))
        except ValueError as exc:
            error = str(exc)
        if on_completion is not None:
            on_completion(record["state_id"], prompt, completion, valid)
        outputs.append(
            {
                "state_id": record["state_id"],
                "selected_tool": selected,
                "expected_tool": record["expected_tool"],
                "arguments_valid": valid,
                "budget_exhausted": exhausted,
                "budget_respected": budget_respected,
                "unsafe_call": not valid or not budget_respected,
                "tool_correct": selected == record["expected_tool"],
                "error": error,
                "prompt_tokens": completion.prompt_tokens,
                "completion_tokens": completion.completion_tokens,
                "latency_ms": completion.latency_ms,
                "completion": completion.text,
            }
        )
    return {
        "status": "synthetic frozen-state capability diagnostic; not human-annotated project states",
        "states": len(outputs),
        "tool_selection_accuracy": sum(o["tool_correct"] for o in outputs) / len(outputs),
        "argument_validity": sum(o["arguments_valid"] for o in outputs) / len(outputs),
        # Reported beside argument validity rather than derived from it, because
        # they are no longer complements: a call can carry a correct cutoff and
        # still be one the budget forbids.
        "unsafe_call_rate": sum(o["unsafe_call"] for o in outputs) / len(outputs),
        "budget_violations": sum(
            o["budget_exhausted"] and not o["budget_respected"] for o in outputs
        ),
        "budget_exhausted_states": sum(o["budget_exhausted"] for o in outputs),
        "outputs": outputs,
    }
