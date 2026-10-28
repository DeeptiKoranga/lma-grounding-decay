"""Measured generation interface for local and hosted inference backends."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ANTHROPIC_HAIKU_45 = "claude-haiku-4-5-20251001"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
MAX_RESPONSE_BYTES = 4_000_000


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    backend: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    revision: str | None = None


class Generator(Protocol):
    def generate(self, prompt: str, *, max_tokens: int = 1500) -> Completion: ...


def _validate_request(prompt: str, max_tokens: int) -> None:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a nonempty string")
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
        raise ValueError("max_tokens must be a positive integer")


def _read_json_response(response) -> dict:
    raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("generation response exceeds byte budget")
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("generation response must be a JSON object")
    return result


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
    def __init__(
        self,
        path: str | Path,
        *,
        model_id: str,
        revision: str,
        max_input_tokens: int = 12000,
    ):
        path = Path(path)
        if not path.is_dir() or not revision.strip():
            raise ValueError("MLX requires an existing local model and a recorded revision")
        if max_input_tokens < 1:
            raise ValueError("max_input_tokens must be positive")
        from mlx_lm import load

        self.model, self.tokenizer = load(str(path))
        self.model_id, self.revision = model_id, revision
        self.max_input_tokens = max_input_tokens

    def generate(self, prompt: str, *, max_tokens: int = 1500) -> Completion:
        _validate_request(prompt, max_tokens)
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
            text="".join(pieces),
            model=self.model_id,
            backend="mlx",
            prompt_tokens=final.prompt_tokens,
            completion_tokens=final.generation_tokens,
            latency_ms=(time.monotonic() - started) * 1000,
            revision=self.revision,
        )


class ChatCompletionsGenerator:
    """OpenAI-compatible llama.cpp/vLLM endpoint; remote calls require authorization."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        backend: str = "vllm",
        allow_remote: bool = False,
        revision: str | None = None,
        chat_template_kwargs: dict | None = None,
        response_format: dict | None = None,
    ):
        parts = urlsplit(base_url)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
        ):
            raise ValueError("invalid model endpoint")
        if not allow_remote and parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("remote inference requires explicit allow_remote authorization")
        if backend not in {"vllm", "llama.cpp", "api"}:
            raise ValueError("unsupported generation backend")
        if not model.strip():
            raise ValueError("model must be nonempty")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model, self.backend, self.revision = model, backend, revision
        self.chat_template_kwargs = (
            dict(chat_template_kwargs) if chat_template_kwargs is not None else None
        )
        self.response_format = (
        dict(response_format) if response_format is not None else None
        )

    def generate(self, prompt: str, *, max_tokens: int = 1500) -> Completion:
        _validate_request(prompt, max_tokens)
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        if self.chat_template_kwargs is not None:
            payload["chat_template_kwargs"] = self.chat_template_kwargs
        if self.response_format is not None:
            payload["response_format"] = self.response_format
        headers = {"Content-Type": "application/json"}
        if key := os.environ.get("LMA_API_KEY"):
            headers["Authorization"] = f"Bearer {key}"
        started = time.monotonic()
        request = Request(self.url, data=json.dumps(payload).encode(), headers=headers)
        try:
            with urlopen(request, timeout=180) as response:
                result = _read_json_response(response)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise RuntimeError(f"{self.backend} generation request failed") from exc

        try:
            message = result["choices"][0]["message"]["content"]
            usage = result["usage"]
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("backend returned an invalid chat-completions response") from exc
        if not isinstance(message, str):
            raise ValueError("backend response content must be text")
        if (
            isinstance(prompt_tokens, bool)
            or not isinstance(prompt_tokens, int)
            or prompt_tokens < 0
            or isinstance(completion_tokens, bool)
            or not isinstance(completion_tokens, int)
            or completion_tokens < 0
        ):
            raise ValueError("backend must provide valid actual token counts")
        return Completion(
            text=message,
            model=self.model,
            backend=self.backend,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=(time.monotonic() - started) * 1000,
            revision=self.revision,
        )


class AnthropicGenerator:
    """Native Anthropic Messages API integration; no OpenAI compatibility assumption."""

    def __init__(
        self,
        *,
        model: str = ANTHROPIC_HAIKU_45,
        api_key: str | None = None,
        revision: str | None = None,
    ):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key or not key.strip():
            raise ValueError("Claude requires ANTHROPIC_API_KEY")
        if not model.strip():
            raise ValueError("Claude model identifier must be nonempty")
        self.model = model
        self.revision = revision or model
        self.api_key = key

    def generate(self, prompt: str, *, max_tokens: int = 1500) -> Completion:
        _validate_request(prompt, max_tokens)
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": 0,
            "messages": [{"role": "user", "content": prompt}],
        }
        headers = {
            "content-type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
        }
        request = Request(
            ANTHROPIC_MESSAGES_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        started = time.monotonic()
        try:
            with urlopen(request, timeout=180) as response:
                result = _read_json_response(response)
        except (HTTPError, URLError, TimeoutError) as exc:
            # Do not include request headers or credentials in the error.
            raise RuntimeError("Claude Messages API request failed") from exc

        try:
            content = result["content"]
            usage = result["usage"]
            prompt_tokens = usage["input_tokens"]
            completion_tokens = usage["output_tokens"]
        except (KeyError, TypeError) as exc:
            raise ValueError("Claude returned an invalid Messages API response") from exc
        if not isinstance(content, list):
            raise ValueError("Claude response content must be a list")
        text_blocks = [
            block["text"] for block in content
            if isinstance(block, dict) and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        ]
        if not text_blocks:
            raise ValueError("Claude response contained no text blocks")
        if (
            isinstance(prompt_tokens, bool)
            or not isinstance(prompt_tokens, int)
            or prompt_tokens < 0
            or isinstance(completion_tokens, bool)
            or not isinstance(completion_tokens, int)
            or completion_tokens < 0
        ):
            raise ValueError("Claude response has invalid token usage")
        return Completion(
            text="".join(text_blocks),
            model=self.model,
            backend="claude",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=(time.monotonic() - started) * 1000,
            revision=self.revision,
        )
