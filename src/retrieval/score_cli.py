"""Offline native cross-encoder worker for an isolated generator environment."""

import argparse
import json
import sys

from .rerank import BGEReranker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    payload = json.loads(sys.stdin.read(2_000_001))
    if not isinstance(payload.get("texts"), list) or not 1 <= len(payload["texts"]) <= 50:
        raise ValueError("worker expects 1..50 candidate texts")
    scorer = BGEReranker(revision=args.revision, local_files_only=True, device="cpu", batch_size=1)
    print(json.dumps(scorer.score(payload["query"], payload["texts"])))


if __name__ == "__main__":
    main()
