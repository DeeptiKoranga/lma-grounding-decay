"""Frozen project-schema model pilot; synthetic cases never enter research gold."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from extract.candidates import Extraction, candidate_edge, extraction_prompt
from llm.generate import json_object
from schema import Anchor, Passage, parse_tool_call
from schema.tools import ToolCallAdapter
from verify.llm_verifier import Judgment

MODEL_SPECS = {
    "qwen3-8b": (
        "mlx-community/Qwen3-8B-4bit",
        "545dc4251c05440727734bcd94334791f6ab0192",
        "qwen3-8b-4bit",
    ),
    "qwen3.5-9b": (
        "mlx-community/Qwen3.5-9B-4bit",
        "8b2b98c00a6b4d291155e4890773ca8f769aee53",
        "qwen3.5-9b-4bit",
    ),
}
SELECTION_RULE = (
    "Highest unweighted mean accuracy across the five project tasks; "
    "within 0.03 choose the model with lower mean generation latency. "
    "Report schema validity separately. Selection is for this development protocol, "
    "not a claim of general capability or accepted hypothesis results."
)
PAIRS = [
    ("BRENT", "IMPORT_BILL", "Brent crude prices", "India's import bill"),
    ("INR_USD", "IMPORTED_INFLATION", "rupees per US dollar", "imported inflation"),
    ("REPO_RATE", "LENDING_RATES", "the RBI repo rate", "bank lending rates"),
    ("BANKING_LIQUIDITY", "CALL_MONEY_RATE", "banking system liquidity", "the call money rate"),
    ("GOVT_BORROWING", "GSEC_10Y", "government borrowing", "the 10-year government bond yield"),
    ("CPI_HEADLINE", "RATE_HIKE_EXPECTATIONS", "headline CPI inflation", "rate hike expectations"),
    ("ATF_PRICE", "AIRLINE_COSTS", "aviation turbine fuel prices", "airline operating costs"),
    ("FUEL_PRICES", "CPI_FUEL_LIGHT", "retail fuel prices", "CPI fuel and light inflation"),
    ("FPI_FLOWS", "INR_USD", "foreign portfolio flows", "rupees per US dollar"),
    ("DXY", "INR_USD", "the US dollar index", "rupees per US dollar"),
]


def build_cases(states_path=Path("data/eval/synthetic/agent_states.jsonl")) -> list[dict]:
    cases = []
    states = [json.loads(line) for line in states_path.read_text(encoding="utf-8").splitlines()]
    for i in range(20):
        src, dst, src_name, dst_name = PAIRS[i % len(PAIRS)]
        direction = "up" if i < 10 else "down"
        move = "rise" if direction == "up" else "fall"
        strength = ["direct", "conditional", "correlational"][i % 3]
        text = {
            "direct": f"The report states that a {move} in {src_name} caused a {move} in {dst_name}.",
            "conditional": f"The report warns that a {move} in {src_name} may cause a {move} in {dst_name}.",
            "correlational": f"A {move} in {src_name} was associated with a {move} in {dst_name}; the report describes association only, without establishing causation.",
        }[strength]
        passage = Passage(
            passage_id=f"pilot-{i}#p0",
            doc_id=f"pilot-{i}",
            source="synthetic",
            published_at=datetime(2026, 3, 12, tzinfo=UTC),
            title="Synthetic macro pilot",
            text=text,
            para_idx=0,
            char_start=0,
            char_end=len(text),
            licence_note="Invented for model selection; not real evidence or research gold",
        )
        anchor = Anchor(
            var=src, direction=direction, event="Synthetic pilot move", event_date=date(2026, 3, 12)
        )
        gold = {
            "src_var": src,
            "dst_var": dst,
            "direction": direction,
            "strength": strength,
            "provenance": "source_asserted",
            "evidence_passage_id": passage.passage_id,
            "evidence_span": text,
        }
        gold_graph = {"edges": [gold]}
        Extraction.model_validate(gold_graph)
        cases.append(
            {
                "id": f"extract-{i:02}",
                "task": "extraction",
                "prompt": extraction_prompt(
                    "What relationship between the two named variables does this source describe? Include only that one link.",
                    anchor,
                    [passage],
                    self_labels=True,
                ),
                "gold": gold_graph,
                "passage": passage.model_dump(mode="json"),
            }
        )
        judge_prompt = (
            "Judge the source's relationship using the project's causal-strength classes: direct means explicit causation; "
            "conditional means risk, forecast or hedged causation; correlational means association only. "
            "Return JSON matching the supplied schema. Preserve the destination direction.\n"
            + json.dumps(
                {
                    "src_var": src,
                    "dst_var": dst,
                    "source": text,
                    "schema": Judgment.model_json_schema(),
                }
            )
        )
        cases.append(
            {
                "id": f"strength-{i:02}",
                "task": "strength",
                "prompt": judge_prompt,
                "gold": {"strength": strength, "direction": direction},
            }
        )
        cases.append(
            {
                "id": f"json-{i:02}",
                "task": "json_validity",
                "prompt": "Emit ONLY the TARGET value below as strict JSON, without commentary or Markdown. "
                "The output must have exactly one top-level key: edges. "
                "SCHEMA is a constraint and must never be copied into the output.\nTARGET:\n"
                + json.dumps(gold_graph)
                + "\nSCHEMA:\n"
                + json.dumps(Extraction.model_json_schema()),
                "gold": gold_graph,
                "passage": passage.model_dump(mode="json"),
            }
        )
        state = states[i]
        cases.append(
            {
                "id": f"tool-{i:02}",
                "task": "tool_choice",
                "prompt": "Choose the next read-only tool call for this controller state. "
                "Return one JSON object matching the tool-call schema. Never widen the cutoff. "
                "A required move-confirmation check takes priority over stopping for no open edges.\n"
                + json.dumps(
                    {"state": state["state"], "tool_schema": ToolCallAdapter.json_schema()}
                ),
                "gold": {"tool": state["expected_tool"]},
                "state": state["state"],
            }
        )
        opposite = "fall" if move == "rise" else "rise"
        negative = (
            f"The source mentions {src_name} and {dst_name} in separate lists. It states no relationship between them."
            if i % 2 == 0
            else f"The source states that a {move} in {src_name} caused a {opposite} in {dst_name}."
        )
        verdict = "unsupported" if i % 2 == 0 else "contradicted"
        cases.append(
            {
                "id": f"reject-{i:02}",
                "task": "unsupported_edges",
                "prompt": "Judge only this proposed edge against the source. Co-mention is insufficient. "
                "Use unsupported if no relation is stated and contradicted for an opposite destination move. "
                "Return JSON matching the project's verifier schema.\n"
                + json.dumps(
                    {
                        "src_var": src,
                        "dst_var": dst,
                        "claimed_direction": direction,
                        "source": negative,
                        "schema": Judgment.model_json_schema(),
                    }
                ),
                "gold": {"verdict": verdict},
            }
        )
    return cases


def score(case: dict, output: str) -> dict:
    result = {"score": 0, "strict_json_valid": False, "schema_valid": False}
    try:
        json.loads(output)
        result["strict_json_valid"] = True
    except (ValueError, TypeError):
        pass
    try:
        parsed = json_object(output)
        task = case["task"]
        if task in {"extraction", "json_validity"}:
            extracted = Extraction.model_validate(parsed)
            passage = Passage.model_validate(case["passage"])
            for index, candidate in enumerate(extracted.edges):
                candidate_edge(
                    candidate,
                    edge_id=str(index),
                    passages={passage.passage_id: passage},
                    as_of=date(2026, 3, 20),
                )
            result["schema_valid"] = True
            if task == "json_validity":
                result["score"] = int(result["strict_json_valid"])
            elif len(extracted.edges) == 1:
                actual = extracted.edges[0].model_dump(mode="json")
                gold = case["gold"]["edges"][0]
                result["score"] = int(
                    all(
                        actual[k] == gold[k]
                        for k in (
                            "src_var",
                            "dst_var",
                            "direction",
                            "strength",
                            "provenance",
                            "evidence_passage_id",
                        )
                    )
                    and bool(actual["evidence_span"])
                    and actual["evidence_span"] in passage.text
                )
        elif task in {"strength", "unsupported_edges"}:
            judgment = Judgment.model_validate(parsed)
            result["schema_valid"] = True
            result["score"] = int(
                all(str(getattr(judgment, k)) == v for k, v in case["gold"].items())
            )
        else:
            call = parse_tool_call(parsed)
            result["schema_valid"] = (
                not hasattr(call.args, "as_of") or str(call.args.as_of) == case["state"]["as_of"]
            )
            result["score"] = int(result["schema_valid"] and str(call.tool) == case["gold"]["tool"])
    except (ValueError, KeyError, TypeError) as exc:
        result["error"] = str(exc)
    return result
