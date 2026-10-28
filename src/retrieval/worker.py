"""Persistent offline retrieval worker for an isolated MLX generator environment."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import queue
import subprocess
import sys
import threading
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
        self._responses = None
        self._reader = None
        self._lock = threading.RLock()

    @staticmethod
    def _read_responses(stream, responses):
        try:
            for line in stream:
                responses.put(line)
        except (OSError, ValueError):
            pass  # Closing a failed worker can also close its stdout pipe.
        finally:
            responses.put(None)

    def search(self, query, *, as_of, k=10, source_kind="any", must_mention=None):
        with self._lock:
            args = validate_query(
                query,
                as_of=as_of,
                k=k,
                source_kind=source_kind,
                must_mention=must_mention,
                aliases=self.aliases,
            )
            try:
                if self.process is None:
                    self._responses = queue.Queue()
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
                        encoding="utf-8",
                        env={
                            **os.environ,
                            "HF_HUB_OFFLINE": "1",
                            "PYTHONUTF8": "1",
                            "PYTHONIOENCODING": "utf-8",
                        },
                    )
                    self._reader = threading.Thread(
                        target=self._read_responses,
                        args=(self.process.stdout, self._responses),
                        daemon=True,
                    )
                    self._reader.start()
                self.process.stdin.write(args.model_dump_json() + "\n")
                self.process.stdin.flush()
                try:
                    line = self._responses.get(timeout=self.timeout)
                except queue.Empty as exc:
                    raise RuntimeError("retrieval worker timed out") from exc
                if line is None:
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
        with self._lock:
            if self.process is not None:
                process = self.process
                if process.poll() is None:
                    with contextlib.suppress(OSError):
                        process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                with contextlib.suppress(OSError):
                    process.stdin.close()
                process.stdout.close()
                if self._reader is not None:
                    self._reader.join(timeout=1)
                self.process = self._responses = self._reader = None


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
