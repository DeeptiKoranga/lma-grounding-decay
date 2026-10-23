"""Append-only, schema-validated execution records with full prompts and usage."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from schema import parse_run_log_line


class RunLogger:
    def __init__(self, path: Path, *, run_id: str, query_id: str, condition: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = path.open("x", encoding="utf-8")
        self.context = {"run_id": run_id, "query_id": query_id, "condition": condition}
        self.step = 0

    def write(self, event: str, **fields):
        record = parse_run_log_line(
            {**self.context, "step": self.step, "ts": datetime.now(UTC), "event": event, **fields}
        )
        self.stream.write(record.model_dump_json() + "\n")
        self.stream.flush()

    def model(self, purpose, prompt, completion, json_valid):
        self.write(
            "model_call",
            purpose=purpose,
            model=completion.model,
            backend=completion.backend,
            temperature=0,
            prompt=prompt,
            prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
            completion=completion.text,
            prompt_tokens=completion.prompt_tokens,
            completion_tokens=completion.completion_tokens,
            latency_ms=completion.latency_ms,
            json_valid=json_valid,
        )

    def close(self):
        self.stream.close()
