"""Build and audit a pinned offline dense index, reusing only identical inputs."""

import argparse
import gc
import hashlib
import json
import time
from pathlib import Path

from retrieval.bm25 import Aliases, BM25Retriever
from retrieval.dense import BGEEmbedder, _embedding_identity
from retrieval.factory import build_retriever
from schema import Passage

REVISION = "5617a9f61b028005a4858fdac845db406aefb181"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(corpus, output, seed, report):
    if output.exists() or report.exists():
        raise ValueError("preserve existing indexes and choose new paths")
    started = time.monotonic()
    passages = [Passage.model_validate_json(line) for line in corpus.read_text().splitlines()]
    embedder = BGEEmbedder(revision=REVISION, device="cpu", batch_size=8, local_files_only=True)
    previous = json.loads(seed.read_text())
    if previous["version"] != 2 or previous["embedding_id"] != _embedding_identity(embedder):
        raise ValueError("seed embedding identity/preprocessing mismatch")
    by_text = {row["text_sha256"]: row["vector"] for row in previous["entries"]}
    entries = []
    for passage in passages:
        text_hash = hashlib.sha256((passage.title + "\n" + passage.text).encode()).hexdigest()
        if text_hash in by_text:
            entries.append(
                {
                    "passage_id": passage.passage_id,
                    "text_sha256": text_hash,
                    "vector": by_text[text_hash],
                }
            )
    reused = len(entries)
    output.mkdir(parents=True)
    checkpoint = output / "bge_m3_checkpoint.json"
    checkpoint.write_text(
        json.dumps({"version": 2, "embedding_id": previous["embedding_id"], "entries": entries})
        + "\n"
    )
    del entries, previous, by_text
    gc.collect()
    print(
        json.dumps(
            {
                "passages": len(passages),
                "reused_exact_inputs": reused,
                "encode_new_inputs": len(passages) - reused,
            }
        ),
        flush=True,
    )
    dense = build_retriever(
        passages,
        aliases=Aliases.load(Path("data/aliases.yaml")),
        config="bge_m3",
        embedding_revision=REVISION,
        device="cpu",
        local_files_only=True,
        dense_backend="faiss",
        dense_index=output / "bge_m3_vectors.json",
        embedding_checkpoint=checkpoint,
        embedding_batch_size=8,
        checkpoint_every=200,
    )
    dense.embedder.unload()
    lexical = BM25Retriever(passages, aliases=Aliases.load(Path("data/aliases.yaml")))
    queries = [("crude oil and rupee", "2026-03-12"), ("inflation and bond yields", "2026-09-24")]
    for query, cutoff in queries:
        hits = lexical.search(query, as_of=cutoff, k=10)
        assert hits and all(p.passage.published_at.date().isoformat() <= cutoff for p in hits)
    result = {
        "corpus_sha256": digest(corpus),
        "index_sha256": digest(output / "bge_m3_vectors.json"),
        "index": str(output / "bge_m3_vectors.json"),
        "passages": len(passages),
        "reused_exact_title_text_inputs": reused,
        "new_inputs_encoded": len(passages) - reused,
        "embedding_revision": REVISION,
        "device": "cpu",
        "max_length": 1024,
        "batch_size": 8,
        "phase_wall_s": round(time.monotonic() - started, 2),
        "all_passages_match_snapshot": list(dense.passages) == passages,
        "lexical_date_checks_passed": True,
        "research_acceptance": False,
    }
    assert result["all_passages_match_snapshot"]
    report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument(
        "--seed", type=Path, default=Path("data/interim/corpus_v3_20261023/bge_m3_checkpoint.json")
    )
    p.add_argument("--report", type=Path, required=True)
    a = p.parse_args()
    build(a.corpus, a.output, a.seed, a.report)


if __name__ == "__main__":
    main()
