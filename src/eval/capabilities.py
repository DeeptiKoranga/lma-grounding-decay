"""Frozen synthetic action probes with schema/cutoff checks and measured model usage."""

from __future__ import annotations

import json
from pathlib import Path

from llm.generate import json_object
from schema import parse_tool_call
from schema.tools import ToolCallAdapter


def evaluate_actions(generator, states: Path) -> dict:
    records = [json.loads(line) for line in states.read_text().splitlines() if line.strip()]
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
        try:
            call = parse_tool_call(json_object(completion.text))
            selected = str(call.tool)
            valid = (
                not hasattr(call.args, "as_of") or str(call.args.as_of) == record["state"]["as_of"]
            )
            if not valid:
                error = "cutoff widened or changed"
        except ValueError as exc:
            error = str(exc)
        outputs.append(
            {
                "state_id": record["state_id"],
                "selected_tool": selected,
                "expected_tool": record["expected_tool"],
                "arguments_valid": valid,
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
        "outputs": outputs,
    }
