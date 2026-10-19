"""Shared fixtures. Everything here reads `tests/fixtures/`, never the real corpus."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from schema import Graph, Passage, RunLogLine, parse_run_log_line

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixture_dir() -> Path:
    return FIXTURE_DIR


@pytest.fixture(scope="session")
def raw_passages() -> list[dict]:
    text = (FIXTURE_DIR / "passages.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


@pytest.fixture(scope="session")
def passages(raw_passages: list[dict]) -> list[Passage]:
    return [Passage.model_validate(row) for row in raw_passages]


@pytest.fixture(scope="session")
def documents() -> dict[str, str]:
    return json.loads((FIXTURE_DIR / "documents.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def raw_graph() -> dict:
    return json.loads((FIXTURE_DIR / "graph_brent_hormuz.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def graph(raw_graph: dict) -> Graph:
    return Graph.model_validate(raw_graph)


@pytest.fixture(scope="session")
def raw_run_log() -> list[dict]:
    text = (FIXTURE_DIR / "run_log.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


@pytest.fixture(scope="session")
def run_log(raw_run_log: list[dict]) -> list[RunLogLine]:
    return [parse_run_log_line(row) for row in raw_run_log]
