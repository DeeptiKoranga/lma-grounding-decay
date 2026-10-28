import hashlib
import json

import pytest

from corpus.bindings import recorded_corpus_sha256, require_run_corpus
from eval.prose_review import prepare as prepare_prose
from eval.review import prepare as prepare_support
from eval.run_audit import audit


@pytest.mark.parametrize(
    "manifest", ["inputs.json", "phases.json", "prose_correction_receipt.json"]
)
@pytest.mark.parametrize("consumer", ["prose", "support", "audit"])
def test_review_and_audit_refuse_changed_corpus_before_creating_output(
    tmp_path, manifest, consumer
):
    runs = tmp_path / "runs"
    runs.mkdir()
    binding = {"corpus_sha256": hashlib.sha256(b"original corpus").hexdigest()}
    (runs / manifest).write_text(
        json.dumps({"shared_inputs": binding} if manifest == "phases.json" else binding)
    )
    corpus = tmp_path / "changed.jsonl"
    corpus.write_text("a different corpus, even with reused passage IDs")
    output = tmp_path / "review"
    with pytest.raises(ValueError, match="archived corpus"):
        if consumer == "prose":
            prepare_prose(runs, output, corpus=corpus)
        elif consumer == "support":
            prepare_support(runs=runs, corpus=corpus, output=output)
        else:
            audit(runs=runs, corpus=corpus)
    assert not output.exists()


def test_archived_matching_corpus_and_legacy_fixtures_remain_usable(tmp_path):
    corpus = tmp_path / "old.jsonl"
    corpus.write_text("original")
    assert recorded_corpus_sha256(tmp_path) is None
    require_run_corpus(tmp_path, corpus)
    (tmp_path / "inputs.json").write_text(
        json.dumps({"corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest()})
    )
    require_run_corpus(tmp_path, corpus)
    (tmp_path / "phases.json").write_text(
        json.dumps({"shared_inputs": {"corpus_sha256": "0" * 64}})
    )
    with pytest.raises(ValueError, match="disagree"):
        require_run_corpus(tmp_path, corpus)
