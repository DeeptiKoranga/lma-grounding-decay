"""Persistent offline retrieval worker for an isolated MLX generator environment."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import selectors
import subprocess
import sys
from pathlib import Path

from schema.tools import SearchCorpusArgs

from .bm25 import Aliases, BM25Retriever, Hit
from .factory import build_retriever
from .filters import checked_hits, validate_query


class WorkerRetriever:
    """Keep the selected index/model in one worker, checking all returned identities."""

    def __init__(self, *, python, corpus: Path, aliases: Path, settings: dict, timeout=600):
        self.python, self.corpus_path, self.aliases_path = python, corpus, aliases
        self.settings, self.timeout = settings, timeout
        self.passages = BM25Retriever.from_jsonl(corpus).passages
        self.aliases = Aliases.load(aliases)
        self.corpus = {p.passage_id: p for p in self.passages}
        self.process = None

    def search(self, query, *, as_of, k=10, source_kind="any", must_mention=None):
        args = validate_query(
            query,
            as_of=as_of,
            k=k,
            source_kind=source_kind,
            must_mention=must_mention,
            aliases=self.aliases,
        )
        if self.process is None:
            self.process = subprocess.Popen(
                [
                    self.python,
                    "-u",
                    "-m",
                    "retrieval.worker",
                    "--corpus",
                    str(self.corpus_path),
                    "--aliases",
                    str(self.aliases_path),
                    "--settings",
                    json.dumps(self.settings),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                env={**os.environ, "HF_HUB_OFFLINE": "1"},
            )
        try:
            self.process.stdin.write(args.model_dump_json() + "\n")
            self.process.stdin.flush()
            with selectors.DefaultSelector() as selector:
                selector.register(self.process.stdout, selectors.EVENT_READ)
                if not selector.select(self.timeout):
                    raise RuntimeError("retrieval worker timed out")
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("retrieval worker exited before returning results")
            result = json.loads(line)
            if "error" in result:
                raise RuntimeError(result["error"])
            hits = [Hit(self.corpus[row["passage_id"]], row["score"]) for row in result["hits"]]
            return checked_hits(hits, self.corpus, args, self.aliases)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            self.close()
            raise RuntimeError(f"retrieval worker failed: {exc}") from exc

    def close(self):
        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process.stdin.close()
            self.process.stdout.close()
            self.process = None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--aliases", type=Path, required=True)
    parser.add_argument("--settings", required=True)
    args = parser.parse_args()
    settings = json.loads(args.settings)
    if settings.get("dense_index"):
        settings["dense_index"] = Path(settings["dense_index"])
    with contextlib.redirect_stdout(sys.stderr):
        retriever = build_retriever(
            list(BM25Retriever.from_jsonl(args.corpus).passages),
            aliases=Aliases.load(args.aliases),
            **settings,
        )
    for line in sys.stdin:
        try:
            query = SearchCorpusArgs.model_validate_json(line)
            with contextlib.redirect_stdout(sys.stderr):
                hits = retriever.search(**query.model_dump())
            result = {
                "hits": [{"passage_id": h.passage.passage_id, "score": h.score} for h in hits]
            }
        except (OSError, ValueError, RuntimeError) as exc:
            result = {"error": str(exc)}
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
