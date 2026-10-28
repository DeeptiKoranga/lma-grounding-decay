"""Recall cannot use unreviewed, stale or ungrounded reference graphs."""

import json
from pathlib import Path

import pytest

from eval.challenge import build as build_challenge
from eval.references import digest, prepare, validate
from eval.review import evaluate
from eval.review import prepare as prepare_support
from schema import Graph
from verify.paths import rebuild

FIXTURES = Path(__file__).parents[1] / "fixtures"


def reference(tmp_path):
    corpus = tmp_path / "passages.jsonl"
    corpus.write_bytes((FIXTURES / "passages.jsonl").read_bytes())
    source = Graph.model_validate_json((FIXTURES / "graph_brent_hormuz.json").read_text())
    graph = rebuild(
        query_id=source.query_id,
        anchor=source.anchor,
        as_of=source.as_of,
        edges=[source.edges[0]],
        condition="M",
    )
    folder = tmp_path / "references"
    folder.mkdir()
    path = folder / f"{graph.query_id}.json"
    path.write_text(graph.model_dump_json(indent=2))
    return folder, path, corpus


def attest(folder):
    path = folder / "review_receipt.json"
    review = json.loads(path.read_text())
    review.update(
        reviewer="Synthetic test reviewer",
        reviewed_on="2026-10-23",
        independent_review=True,
        all_relations_and_strengths_reviewed=True,
    )
    path.write_text(json.dumps(review))


def test_blank_receipt_cannot_establish_reference_review(tmp_path):
    folder, _, corpus = reference(tmp_path)
    assert prepare(references=folder, corpus=corpus)["graphs"] == 1
    with pytest.raises(ValueError, match="attestation"):
        validate(references=folder, corpus=corpus, expected_corpus_sha256=digest(corpus))
    with pytest.raises(ValueError, match="attestation"):
        build_challenge(gold=folder, corpus=corpus, output=tmp_path / "challenge.jsonl")


def test_completed_receipt_binds_both_reference_files_and_support_corpus(tmp_path):
    folder, path, corpus = reference(tmp_path)
    prepare(references=folder, corpus=corpus)
    attest(folder)
    graphs, receipt_hash = validate(
        references=folder, corpus=corpus, expected_corpus_sha256=digest(corpus)
    )
    assert set(graphs) == {path.stem}
    assert receipt_hash == digest(folder / "review_receipt.json")
    # Rescoped from 25 to 12 by D-21; one gold edge is still far too few.
    with pytest.raises(ValueError, match="at least 12 eligible"):
        build_challenge(gold=folder, corpus=corpus, output=tmp_path / "challenge.jsonl")
    with pytest.raises(ValueError, match="corpus hash"):
        validate(references=folder, corpus=corpus, expected_corpus_sha256="0" * 64)
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="changed"):
        validate(references=folder, corpus=corpus, expected_corpus_sha256=digest(corpus))


@pytest.mark.parametrize(
    "field,value", [("evidence_span", "invented quote"), ("evidence_doc_id", "other")]
)
def test_reference_citation_must_match_eligible_trusted_bytes(tmp_path, field, value):
    folder, path, corpus = reference(tmp_path)
    graph = json.loads(path.read_text())
    graph["edges"][0][field] = value
    path.write_text(json.dumps(graph))
    with pytest.raises(ValueError, match="exact eligible"):
        prepare(references=folder, corpus=corpus)
    assert not (folder / "review_receipt.json").exists()


def test_support_evaluator_requires_the_recorded_reference_review(tmp_path):
    folder, path, corpus = reference(tmp_path)
    graph = json.loads(path.read_text())
    runs = tmp_path / "runs/M"
    runs.mkdir(parents=True)
    (runs / path.name).write_text(
        json.dumps({"graph": graph, "established_edge_ids": [graph["edges"][0]["edge_id"]]})
    )
    support = tmp_path / "support"
    prepare_support(runs=runs.parent, corpus=corpus, output=support)
    judgments = json.loads((support / "judgments.json").read_text())
    judgments.update(
        reviewer="Synthetic support reviewer",
        reviewed_on="2026-10-23",
        independent_review=True,
        blinded_to_condition=True,
    )
    for row in judgments["judgments"]:
        row.update(supported=True, evidence_strength=graph["edges"][0]["strength"])
    (support / "judgments.json").write_text(json.dumps(judgments))
    prepare(references=folder, corpus=corpus)
    with pytest.raises(ValueError, match="reference-review attestation"):
        evaluate(review_dir=support, reference_dir=folder, corpus=corpus)
    attest(folder)
    scored = evaluate(review_dir=support, reference_dir=folder, corpus=corpus)
    assert scored["reference_review_receipt_sha256"] == digest(folder / "review_receipt.json")
    assert scored["per_query"]["M"][path.stem]["overall"]["reference_edge_recall"] == 1
