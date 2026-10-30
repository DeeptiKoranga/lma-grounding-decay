import json
from urllib.error import URLError

import pytest

import llm.generate as gen


class FakeResponse:
    def __init__(self, data):
        self.data = json.dumps(data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=-1):
        return self.data[:limit]


def test_completion_includes_optional_revision():
    item = gen.Completion("ok", "model", "test", 2, 3, 1.0, "rev-1")
    assert item.revision == "rev-1"


def test_claude_requires_key_without_calling_network(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        gen.AnthropicGenerator()


def test_claude_uses_native_messages_api_and_actual_usage(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = {k.lower(): v for k, v in request.header_items()}
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return FakeResponse(
            {
                "content": [
                    {"type": "text", "text": '{"edges":'},
                    {"type": "text", "text": " []}"},
                ],
                "usage": {"input_tokens": 17, "output_tokens": 9},
            }
        )

    monkeypatch.setattr(gen, "urlopen", fake_urlopen)
    result = gen.AnthropicGenerator(api_key="test-secret").generate("hello", max_tokens=50)

    assert captured["url"] == gen.ANTHROPIC_MESSAGES_URL
    assert captured["headers"]["x-api-key"] == "test-secret"
    assert captured["headers"]["anthropic-version"] == gen.ANTHROPIC_API_VERSION
    assert captured["payload"]["model"] == gen.ANTHROPIC_HAIKU_45
    assert captured["payload"]["max_tokens"] == 50
    assert result.text == '{"edges": []}'
    assert (result.prompt_tokens, result.completion_tokens) == (17, 9)
    assert result.backend == "claude"
    assert result.revision == gen.ANTHROPIC_HAIKU_45


def test_claude_rejects_missing_or_invalid_usage(monkeypatch):
    monkeypatch.setattr(
        gen,
        "urlopen",
        lambda *a, **k: FakeResponse(
            {
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": "unknown", "output_tokens": 1},
            }
        ),
    )
    with pytest.raises(ValueError, match="token usage"):
        gen.AnthropicGenerator(api_key="test").generate("hello")


def test_claude_wraps_transport_errors_without_leaking_key(monkeypatch):
    def fail(*args, **kwargs):
        raise URLError("network unavailable")

    monkeypatch.setattr(gen, "urlopen", fail)
    with pytest.raises(RuntimeError, match="Claude Messages API request failed"):
        gen.AnthropicGenerator(api_key="never-print-this").generate("hello")


def test_chat_completions_requires_real_token_counts(monkeypatch):
    monkeypatch.setattr(
        gen,
        "urlopen",
        lambda *a, **k: FakeResponse(
            {
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 2},
            }
        ),
    )
    backend = gen.ChatCompletionsGenerator(
        base_url="http://127.0.0.1:8000/v1", model="local", revision="rev"
    )
    with pytest.raises(ValueError, match="invalid chat-completions"):
        backend.generate("hello")


@pytest.mark.parametrize(
    "prompt,max_tokens",
    [
        ("", 5),
        ("hello", 0),
        ("hello", -1),
        ("hello", True),
    ],
)
def test_generation_rejects_invalid_prompt_or_token_budget(prompt, max_tokens):
    with pytest.raises(ValueError):
        gen._validate_request(prompt, max_tokens)


def test_chat_completions_success_records_model_revision_and_usage(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data)
        return FakeResponse(
            {
                "choices": [{"message": {"content": '{"ok": true}'}}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 4},
            }
        )

    monkeypatch.setattr(gen, "urlopen", fake_urlopen)
    backend = gen.ChatCompletionsGenerator(
        base_url="http://127.0.0.1:8000/v1",
        model="test-model",
        backend="vllm",
        revision="commit-123",
    )
    result = backend.generate("hello", max_tokens=20)

    assert captured["url"] == "http://127.0.0.1:8000/v1/chat/completions"
    assert captured["payload"]["temperature"] == 0
    assert captured["payload"]["max_tokens"] == 20
    assert result.text == '{"ok": true}'
    assert result.model == "test-model"
    assert result.revision == "commit-123"
    assert result.backend == "vllm"
    assert (result.prompt_tokens, result.completion_tokens) == (11, 4)


def test_response_reader_rejects_non_object_json():
    class ListResponse(FakeResponse):
        def __init__(self):
            self.data = b"[]"

    with pytest.raises(ValueError, match="JSON object"):
        gen._read_json_response(ListResponse())


def test_response_reader_rejects_response_over_byte_budget(monkeypatch):
    class OversizedResponse:
        def read(self, limit=-1):
            return b"x" * (limit + 1)

    monkeypatch.setattr(gen, "MAX_RESPONSE_BYTES", 8)
    with pytest.raises(ValueError, match="byte budget"):
        gen._read_json_response(OversizedResponse())


def test_claude_rejects_response_without_text_blocks(monkeypatch):
    monkeypatch.setattr(
        gen,
        "urlopen",
        lambda *a, **k: FakeResponse(
            {
                "content": [{"type": "tool_use", "id": "tool-1", "name": "example", "input": {}}],
                "usage": {"input_tokens": 2, "output_tokens": 1},
            }
        ),
    )
    with pytest.raises(ValueError, match="no text blocks"):
        gen.AnthropicGenerator(api_key="test").generate("hello")


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/model",
        "http://user:pass@localhost:8000/v1",
        "http://localhost:8000/v1?secret=value",
    ],
)
def test_chat_completions_rejects_unsafe_endpoint_urls(url):
    with pytest.raises(ValueError, match="invalid model endpoint"):
        gen.ChatCompletionsGenerator(
            base_url=url,
            model="local",
            revision="rev",
        )
