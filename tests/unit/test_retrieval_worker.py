"""The persistent retrieval worker must work when pipe selectors are unavailable."""

import selectors
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from retrieval.worker import WorkerRetriever

ROOT = Path(__file__).parents[2]


def test_worker_reads_two_responses_without_selecting_on_pipe(monkeypatch):
    def unavailable():
        raise OSError("Windows selectors cannot watch subprocess pipes")

    monkeypatch.setattr(selectors, "DefaultSelector", unavailable)
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    worker = WorkerRetriever(
        python=sys.executable,
        corpus=ROOT / "tests/fixtures/passages.jsonl",
        aliases=ROOT / "data/aliases.yaml",
        settings={"config": "bm25"},
        timeout=15,
    )
    try:
        assert worker.search("crude rupee", as_of=date(2026, 3, 20))
        process = worker.process
        assert worker.search("crude", as_of=date(2026, 3, 20))
        assert worker.process is process
    finally:
        worker.close()


def test_worker_timeout_terminates_a_child_that_never_replies(monkeypatch):
    real_popen = subprocess.Popen

    def silent_worker(_command, **options):
        return real_popen([sys.executable, "-u", "-c", "import time; time.sleep(30)"], **options)

    monkeypatch.setattr("retrieval.worker.subprocess.Popen", silent_worker)
    worker = WorkerRetriever(
        python=sys.executable,
        corpus=ROOT / "tests/fixtures/passages.jsonl",
        aliases=ROOT / "data/aliases.yaml",
        settings={"config": "bm25"},
        timeout=0.1,
    )
    with pytest.raises(RuntimeError, match="retrieval worker timed out"):
        worker.search("crude", as_of=date(2026, 3, 20))
    assert worker.process is None


def test_worker_restarts_after_a_failed_child_without_reusing_stale_responses(monkeypatch):
    real_popen = subprocess.Popen
    attempts = []

    def first_child_fails(command, **options):
        attempts.append(command)
        if len(attempts) == 1:
            return real_popen([sys.executable, "-c", "raise SystemExit(1)"], **options)
        return real_popen(command, **options)

    monkeypatch.setattr("retrieval.worker.subprocess.Popen", first_child_fails)
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    worker = WorkerRetriever(
        python=sys.executable,
        corpus=ROOT / "tests/fixtures/passages.jsonl",
        aliases=ROOT / "data/aliases.yaml",
        settings={"config": "bm25"},
        timeout=15,
    )
    with pytest.raises(RuntimeError, match="exited"):
        worker.search("crude", as_of=date(2026, 3, 20))
    assert worker.process is None
    try:
        assert worker.search("crude", as_of=date(2026, 3, 20))
        assert len(attempts) == 2
    finally:
        worker.close()
