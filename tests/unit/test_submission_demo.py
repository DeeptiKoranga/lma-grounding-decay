import json
from pathlib import Path

from scripts.run_demo import run

from schema import Condition, Graph, iter_run_log

REPO = Path(__file__).resolve().parents[2]


def test_submission_demo_runs_the_shared_pipeline_and_builds_the_checked_in_viewer(tmp_path):
    output = tmp_path / "demo"
    summary = run(output)
    assert set(summary) == {str(condition) for condition in Condition}
    assert summary["M"]["tool_calls"] <= 12
    graph = Graph.model_validate(json.loads((output / "M.json").read_text())["graph"])
    assert [edge.provenance for edge in graph.edges] == [
        "source_asserted",
        "source_asserted",
        "model_inferred",
    ]
    assert graph.anchor.confirmed_by_series
    assert graph.paths[0].weakest_strength == "conditional"
    assert not graph.paths[0].fully_sourced
    log = iter_run_log(output / "M.jsonl")
    assert {event.backend for event in log if event.event == "model_call"} == {"fixture"}
    assert any(event.event == "model_call" and event.purpose == "verify" for event in log)
    assert (output / "graph_explorer.html").read_text() == (
        REPO / "reports/demo_fixture.html"
    ).read_text()
