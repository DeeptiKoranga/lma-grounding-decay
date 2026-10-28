"""One measured generation interface; optional backends are imported on demand."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    backend: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float


class Generator(Protocol):
    def generate(self, prompt: str, *, max_tokens: int = 1500) -> Completion: ...


def json_object(text: str) -> dict:
    """Allow a JSON code fence, never silently select JSON from arbitrary prose."""
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    result = json.loads(text)
    if not isinstance(result, dict):
        raise ValueError("model response must be a JSON object")
    return result


class MLXGenerator:
    def __init__(self, path: str | Path, *, model_id: str, revision: str, max_input_tokens=12000):
        path = Path(path)
        if not path.is_dir() or not revision.strip():
            raise ValueError("MLX requires an existing local model and a recorded revision")
        from mlx_lm import load

        self.model, self.tokenizer = load(str(path))
        self.model_id, self.revision = model_id, revision
        self.max_input_tokens = max_input_tokens

    def generate(self, prompt: str, *, max_tokens: int = 1500) -> Completion:
        from mlx_lm import stream_generate
        from mlx_lm.sample_utils import make_sampler

        rendered = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        if len(self.tokenizer.encode(rendered)) > self.max_input_tokens:
            raise ValueError("prompt exceeds the recorded model input budget")
        started, pieces, final = time.monotonic(), [], None
        for response in stream_generate(
            self.model,
            self.tokenizer,
            prompt=rendered,
            max_tokens=max_tokens,
            sampler=make_sampler(temp=0),
        ):
            pieces.append(response.text)
            final = response
        if final is None:
            raise RuntimeError("local model returned no tokens")
        return Completion(
            "".join(pieces),
            f"{self.model_id}@{self.revision}",
            "mlx",
            final.prompt_tokens,
            final.generation_tokens,
            (time.monotonic() - started) * 1000,
        )


class ChatCompletionsGenerator:
    """llama.cpp/vLLM or an explicitly configured compatible API; no automatic fallback."""

    def __init__(self, *, base_url: str, model: str, backend="vllm", allow_remote=False):
        parts = urlsplit(base_url)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username:
            raise ValueError("invalid model endpoint")
        if not allow_remote and parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("remote inference requires explicit allow_remote authorization")
        if backend not in {"vllm", "llama.cpp", "api"}:
            raise ValueError("unsupported generation backend")
        self.url, self.model, self.backend = (
            base_url.rstrip("/") + "/chat/completions",
            model,
            backend,
        )

    def generate(self, prompt: str, *, max_tokens: int = 1500) -> Completion:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if key := os.environ.get("LMA_API_KEY"):
            headers["Authorization"] = f"Bearer {key}"
        started = time.monotonic()
        with urlopen(
            Request(self.url, data=json.dumps(payload).encode(), headers=headers), timeout=180
        ) as response:
            raw = response.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ValueError("generation response exceeds byte budget")
        result = json.loads(raw)
        usage = result.get("usage", {})
        if not {"prompt_tokens", "completion_tokens"} <= usage.keys():
            raise ValueError("backend must provide actual token usage for run logging")
        return Completion(
            result["choices"][0]["message"]["content"],
            self.model,
            self.backend,
            usage["prompt_tokens"],
            usage["completion_tokens"],
            (time.monotonic() - started) * 1000,
        )
