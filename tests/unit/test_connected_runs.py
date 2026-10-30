"""Regressions for selected retrieval, resume identity and non-vacuous completion."""

import json
import sys
from datetime import date
from pathlib import Path

import pytest

from conditions import __main__ as command
from conditions.pipeline import Pipeline, Query
from conditions.provenance import source_identity
from corpus.series import Observation, SeriesStore
from eval.run_audit import audit
from llm.generate import Completion
from retrieval.bm25 import Aliases, BM25Retriever
from retrieval.worker import WorkerRetriever
from schema import Condition, iter_run_log
from verify import AliasTable

ROOT = Path(__file__).parents[2]
CORPUS = ROOT / "tests/fixtures/passages.jsonl"
ALIASES = ROOT / "data/aliases.yaml"


class EmptyGenerator:
    def generate(self, prompt, *, max_tokens=1500):
        return Completion('{"edges": []}', "fixture", "vllm", 1, 1, 0)


def query(**overrides):
    return Query.model_validate(
        {
            "query_id": "q",
            "query": "crude rupee",
            "as_of": "2026-03-20",
            "anchor": {
                "var": "BRENT",
                "direction": "up",
                "event": "Declared window move",
                "event_date": "2026-03-12",
                "confirmed_by_series": True,
            },
            **overrides,
        }
    )


def execute(monkeypatch, tmp_path, *, conditions=("B0", "B1")):
    queries = tmp_path / "queries.jsonl"
    queries.write_text(query().model_dump_json() + "\n")
    series = tmp_path / "series"
    series.mkdir()
    output = tmp_path / "runs"
    argv = [
        "conditions",
        "--queries",
        str(queries),
        "--corpus",
        str(CORPUS),
        "--aliases",
        str(ALIASES),
        "--series",
        str(series),
        "--retriever",
        "bm25",
        "--backend",
        "vllm",
        "--base-url",
        "http://localhost:1234/v1",
        "--revision",
        "fixture",
        "--conditions",
        *conditions,
        "--output",
        str(output),
    ]
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(command, "ChatCompletionsGenerator", lambda **_: EmptyGenerator())
    command.main()
    return output, argv


def test_command_binds_complete_matrix_and_resumes_without_loading_model(monkeypatch, tmp_path):
    output, argv = execute(monkeypatch, tmp_path)
    report = audit(runs=output, corpus=CORPUS)
    assert report["passed"] and report["complete"] and report["completed_graphs"] == 2
    assert report["compute"]["B1"]["tool_calls"] == 2  # series diagnostic + search
    monkeypatch.setattr(sys, "argv", [*argv, "--resume"])
    monkeypatch.setattr(
        command, "ChatCompletionsGenerator", lambda **_: pytest.fail("loaded on cached resume")
    )
    command.main()


def test_old_windows_receipt_keys_resume_and_audit_without_disabling_checks(monkeypatch, tmp_path):
    output, argv = execute(monkeypatch, tmp_path)
    receipt = output / "artifacts.json"
    old = json.loads(receipt.read_text(encoding="utf-8"))
    receipt.write_text(
        json.dumps({k.replace("/", "\\"): v for k, v in old.items()}), encoding="utf-8"
    )
    assert audit(runs=output, corpus=CORPUS)["complete"]
    monkeypatch.setattr(sys, "argv", [*argv, "--resume"])
    monkeypatch.setattr(
        command, "ChatCompletionsGenerator", lambda **_: pytest.fail("model reloaded")
    )
    command.main()


def test_cli_forwards_and_binds_vllm_thinking_settings(monkeypatch, tmp_path):
    output, argv = execute(monkeypatch, tmp_path)
    assert json.loads((output / "inputs.json").read_text())["chat_template_kwargs"] == {
        "enable_thinking": False
    }
    monkeypatch.setattr(
        sys, "argv", [*argv, "--chat-template-kwargs", '{"enable_thinking":true}', "--resume"]
    )
    with pytest.raises(SystemExit) as exc:
        command.main()
    assert exc.value.code == 2


def test_local_cli_uses_the_completed_model_selection_record(monkeypatch, tmp_path):
    monkeypatch.setattr(command, "supports_mlx", lambda: True)
    _output, argv = execute(monkeypatch, tmp_path)
    selection = tmp_path / "selection.json"
    model_path = tmp_path / "pinned-model"
    model_path.mkdir()
    (model_path / "config.json").write_text('{"fixture":true}')
    selection.write_text(
        json.dumps(
            {"model": "chosen-local", "revision": "pinned-revision", "model_path": str(model_path)}
        )
    )
    new_output = tmp_path / "selected-runs"
    chosen = [*argv]
    for flag in ("--revision", "--base-url"):
        index = chosen.index(flag)
        del chosen[index : index + 2]
    chosen[chosen.index("--backend") + 1] = "mlx"
    chosen[chosen.index("--output") + 1] = str(new_output)
    chosen += ["--model-selection", str(selection)]
    calls = []

    def generator(path, *, model_id, revision):
        calls.append((path, model_id, revision))
        return EmptyGenerator()

    monkeypatch.setattr(command, "MLXGenerator", generator)
    monkeypatch.setattr(sys, "argv", chosen)
    command.main()
    assert calls == [(model_path, "chosen-local", "pinned-revision")]
    assert audit(runs=new_output, corpus=CORPUS)["complete"]


def test_non_macos_runner_rejects_mlx_with_an_actionable_error(monkeypatch, capsys):
    monkeypatch.setattr(command, "supports_mlx", lambda: False)
    monkeypatch.setattr(
        sys, "argv", ["conditions", "--queries", "unused.jsonl", "--backend", "mlx"]
    )
    with pytest.raises(SystemExit) as exc:
        command.main()
    assert exc.value.code == 2
    assert "On Windows/Linux select --backend llama.cpp or vllm" in capsys.readouterr().err


@pytest.mark.parametrize("changed", ["graph", "log", "source", "retrieval_setting"])
def test_resume_refuses_changed_artifacts_code_and_runtime_settings(monkeypatch, tmp_path, changed):
    output, argv = execute(monkeypatch, tmp_path)
    if changed == "graph":
        path = output / "B1/q.json"
        payload = json.loads(path.read_text())
        payload["graph"]["query_id"] = "different"
        path.write_text(json.dumps(payload))
    elif changed == "log":
        next((output / "B1").glob("*.jsonl")).write_text("changed")
    elif changed == "source":
        monkeypatch.setattr(command, "source_identity", lambda: {"changed_retrieval": True})
    else:
        argv += ["--device", "changed-device"]
    monkeypatch.setattr(sys, "argv", [*argv, "--resume"])
    with pytest.raises(SystemExit) as exc:
        command.main()
    assert exc.value.code == 2


def test_source_hash_includes_retrieval_series_and_schema_resources(tmp_path):
    for name in ("retrieval/search.py", "corpus/series.py", "schema/ontology.yaml"):
        path = tmp_path / name
        path.parent.mkdir(exist_ok=True)
        path.write_text("original")
    original = source_identity(tmp_path)
    for path in tmp_path.rglob("*.*"):
        path.write_text("changed")
        assert source_identity(tmp_path)["sha256"] != original["sha256"]
        path.write_text("original")


def test_empty_and_partial_runs_cannot_pass_completion(monkeypatch, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert not audit(runs=empty, corpus=CORPUS)["passed"]
    output, _ = execute(monkeypatch, tmp_path)
    (output / "B1/q.json").unlink()
    report = audit(runs=output, corpus=CORPUS)
    assert not report["passed"] and any(f["kind"] == "missing_graph" for f in report["failures"])
    partial = audit(runs=output, corpus=CORPUS, allow_partial=True)
    assert partial["passed"] and not partial["complete"]


def test_audit_exits_nonzero_on_failed_gate(monkeypatch, tmp_path):
    from eval import run_audit

    runs = tmp_path / "empty"
    runs.mkdir()
    output = tmp_path / "audit.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["audit", "--runs", str(runs), "--corpus", str(CORPUS), "--output", str(output)],
    )
    with pytest.raises(SystemExit) as exc:
        run_audit.main()
    assert exc.value.code == 1 and not json.loads(output.read_text())["passed"]


def test_actual_worker_searches_twice_and_rejects_future_documents(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    worker = WorkerRetriever(
        python=sys.executable,
        corpus=CORPUS,
        aliases=ALIASES,
        settings={"config": "bm25"},
        timeout=15,
    )
    try:
        hits = worker.search("crude rupee", as_of=date(2026, 3, 20))
        process = worker.process
        assert hits and all(h.passage.visible_at(date(2026, 3, 20)) for h in hits)
        assert worker.search("crude", as_of=date(2026, 3, 20)) and worker.process is process
    finally:
        worker.close()
    assert process.poll() is not None


@pytest.mark.parametrize(
    "scenario",
    ["confirmed", "empty", "late", "opposite", "threshold", "no_window", "missing_endpoint"],
)
def test_anchor_requires_visible_exact_window_and_matching_move(passages, tmp_path, scenario):
    window = {"start": "2026-03-10", "end": "2026-03-12", "minimum_absolute_change": 5}
    if scenario == "threshold":
        window["minimum_absolute_change"] = 50
    q = query(anchor_window=None if scenario == "no_window" else window)
    rows = [
        Observation(
            on=date(2026, 3, d),
            value=v,
            available_on=date(2026, 3, 21) if scenario == "late" else date(2026, 3, d),
            source_url="https://example.org/fixture",
            unit="USD per barrel",
        )
        for d, v in [
            (11 if scenario == "missing_endpoint" else 10, 100),
            (12, 90 if scenario == "opposite" else 110),
        ]
    ]
    series = SeriesStore({} if scenario == "empty" else {"brent_usd_bbl": rows})
    pipeline = Pipeline(
        generator=EmptyGenerator(), retriever=BM25Retriever(passages), series=series
    )
    for c in Condition:
        path = tmp_path / f"{c}.jsonl"
        result = pipeline.run(
            q, condition=c if c != Condition.B1_R else Condition.B1, run_id="fixture", log_path=path
        )
        assert result["graph"]["anchor"]["confirmed_by_series"] == (scenario == "confirmed")
        calls = [r.call for r in iter_run_log(path) if r.event == "tool_call"]
        assert calls[0].tool == "get_series" and result["tool_calls"] <= 12
        if scenario == "confirmed":
            assert len(result["anchor_check"]["observations"]) == 2


def test_configured_aliases_reach_pipeline_verifier(passages, tmp_path, monkeypatch):
    captured = []

    class SpyVerifier:
        def __init__(self, *args, aliases=None, **kwargs):
            captured.append(aliases)

    monkeypatch.setattr("conditions.pipeline.Verifier", SpyVerifier)
    aliases = AliasTable(version="fixture", surface_forms={"BRENT": ("custom crude",)})
    Pipeline(
        generator=EmptyGenerator(),
        retriever=BM25Retriever(passages, aliases=Aliases({})),
        series=SeriesStore({}),
        aliases=aliases,
    ).run(query(), condition="B0", run_id="f", log_path=tmp_path / "run.jsonl")
    assert captured == [aliases]


def test_default_selected_retriever_is_constructed_and_recorded(monkeypatch, tmp_path):
    _output, argv = execute(monkeypatch, tmp_path)
    index = tmp_path / "vectors.json"
    index.write_text("fixture index; construction is spied")
    selected = []

    def factory(passages, **settings):
        selected.append(settings)
        return BM25Retriever(passages, aliases=settings["aliases"])

    monkeypatch.setattr(command, "build_retriever", factory)
    # Remove the helper's explicit BM25 override, exercising the actual default.
    at = argv.index("--retriever")
    argv[at : at + 2] = []
    argv += ["--dense-index", str(index), "--output", str(tmp_path / "dense-run")]
    monkeypatch.setattr(sys, "argv", argv)
    command.main()
    assert selected[0]["config"] == "bge_m3" and selected[0]["dense_backend"] == "faiss"
    assert selected[0]["embedding_revision"] == "5617a9f61b028005a4858fdac845db406aefb181"
    inputs = json.loads((tmp_path / "dense-run/inputs.json").read_text())
    assert inputs["retrieval"]["config"] == "bge_m3" and inputs["dense_index_sha256"]


def test_bad_and_duplicate_artifacts_fail_and_retries_do_not_inflate_compute(monkeypatch, tmp_path):
    output, _ = execute(monkeypatch, tmp_path)
    original = audit(runs=output, corpus=CORPUS)
    bound = next((output / "B1").glob("*.jsonl"))
    (output / "B1/failed-attempt.jsonl").write_text(bound.read_text())
    retried = audit(runs=output, corpus=CORPUS)
    assert retried["compute"] == original["compute"]
    assert retried["unbound_logs"] == ["B1/failed-attempt.jsonl"]
    (output / "B1/duplicate.json").write_text((output / "B1/q.json").read_text())
    (output / "B0/malformed.json").write_text("not json")
    report = audit(runs=output, corpus=CORPUS)
    assert not report["passed"] and len(report["failures"]) == 2


def test_audit_cannot_shrink_bound_run_matrix(monkeypatch, tmp_path):
    output, _ = execute(monkeypatch, tmp_path)
    (output / "B1/q.json").unlink()
    report = audit(runs=output, corpus=CORPUS, expected_conditions=["B0"])
    assert not report["complete"] and not report["passed"]


def test_custom_aliases_are_used_by_actual_verifier_rules(passages):
    from schema import Edge
    from verify.llm_verifier import Verifier

    class Supported:
        def generate(self, *args, **kwargs):
            return Completion(
                '{"verdict":"supported","direction":"up","strength":"direct","reason":"fixture"}',
                "fixture",
                "vllm",
                1,
                1,
                0,
            )

    passage = next(p for p in passages if p.passage_id == "bl-2026-03-12-brent100#p1")
    edge = Edge(
        edge_id="e",
        src_var="BRENT",
        dst_var="INDIAN_BASKET",
        direction="up",
        strength="direct",
        provenance="model_inferred",
        hop=1,
    )
    kwargs = {"passage": passage, "span": passage.text, "as_of": date(2026, 3, 20), "call_id": "v"}
    assert Verifier(Supported(), passages).verify(edge, **kwargs).verdict == "supported"
    custom = AliasTable(
        version="custom", surface_forms={"BRENT": ("a phrase absent from this source",)}
    )
    assert (
        Verifier(Supported(), passages, aliases=custom).verify(edge, **kwargs).verdict
        == "unsupported"
    )


def test_required_anchor_rejects_unconfirmed_event_before_model_calls(passages, tmp_path):
    class NeverGenerate:
        def generate(self, *args, **kwargs):
            pytest.fail("unconfirmed event reached generation")

    pipeline = Pipeline(
        generator=NeverGenerate(),
        retriever=BM25Retriever(passages),
        series=SeriesStore({}),
        require_confirmed_anchors=True,
    )
    with pytest.raises(ValueError, match="anchor confirmation failed"):
        pipeline.run(query(), condition="B0", run_id="f", log_path=tmp_path / "run.jsonl")
    assert iter_run_log(tmp_path / "run.jsonl")[-1].reason == "error"
