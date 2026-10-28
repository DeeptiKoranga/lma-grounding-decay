"""Shared fixtures. Everything here reads `tests/fixtures/`, never the real corpus."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from schema import Edge, Graph, Passage, RunLogLine, parse_run_log_line

if TYPE_CHECKING:
    from verify import AliasTable

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


# ---------------------------------------------------------------------------
# Verifier fixtures (B6). test_verify_rules.py defines its own module-scoped
# copies of these; dedupe them into here once the Track A and Track B branches
# are integrated.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def aliases() -> AliasTable:
    from verify import load_aliases

    return load_aliases()


@pytest.fixture(scope="session")
def by_passage(passages: list[Passage]) -> dict[str, Passage]:
    return {p.passage_id: p for p in passages}


@pytest.fixture(scope="session")
def corpus_doc_ids(passages: list[Passage]) -> frozenset[str]:
    """Stands in for the frozen-corpus manifest (A4)."""
    return frozenset(p.doc_id for p in passages)


@pytest.fixture(scope="session")
def cited(graph: Graph, by_passage: dict[str, Passage]) -> list[tuple[Edge, Passage]]:
    """Every source-asserted fixture edge paired with the passage it quotes."""
    return [
        (edge, by_passage[edge.evidence_passage_id])
        for edge in graph.edges
        if edge.is_asserted and edge.evidence_passage_id
    ]
