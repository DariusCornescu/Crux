"""Provider dispatch for app.llm. No network — SDK clients are monkeypatched."""
import pytest

from app import llm
from app.config import get_settings


@pytest.fixture(autouse=True)
def _settings_cache_hygiene():
    """monkeypatch restores env on teardown, but the lru_cache would keep the
    patched Settings alive for later tests — clear it after each test here."""
    yield
    get_settings.cache_clear()


def _reload_settings(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()


def test_is_configured_openrouter(monkeypatch):
    _reload_settings(monkeypatch, LLM_PROVIDER="openrouter", OPENROUTER_API_KEY="sk-or-x")
    assert llm.is_configured() is True


def test_is_not_configured_openrouter_without_key(monkeypatch):
    _reload_settings(monkeypatch, LLM_PROVIDER="openrouter", OPENROUTER_API_KEY="")
    assert llm.is_configured() is False


def test_is_configured_anthropic(monkeypatch):
    _reload_settings(monkeypatch, LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY="sk-ant-x")
    assert llm.is_configured() is True


def test_complete_openrouter_builds_payload(monkeypatch):
    _reload_settings(monkeypatch, LLM_PROVIDER="openrouter",
                     OPENROUTER_API_KEY="sk-or-x", OPENROUTER_MODEL="anthropic/claude-sonnet-4.6")
    captured = {}

    class FakeMsg:
        content = "hello from openrouter"

    class FakeChoice:
        message = FakeMsg()

    class FakeResp:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResp()

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, **kwargs):
            captured["init"] = kwargs
            self.chat = FakeChat()

    monkeypatch.setattr(llm, "_openai_client", lambda s: FakeClient(
        api_key=s.openrouter_api_key, base_url="https://openrouter.ai/api/v1"))

    out = llm.complete("SYS", [{"role": "user", "content": "hi"}], max_tokens=42)
    assert out == "hello from openrouter"
    assert captured["model"] == "anthropic/claude-sonnet-4.6"
    assert captured["max_tokens"] == 42
    assert captured["messages"][0] == {"role": "system", "content": "SYS"}
    assert captured["messages"][1] == {"role": "user", "content": "hi"}


def test_complete_dispatches_to_anthropic(monkeypatch):
    _reload_settings(monkeypatch, LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY="sk-ant-x")
    monkeypatch.setattr(llm, "_anthropic_complete",
                        lambda s, system, messages, max_tokens: "from anthropic")
    out = llm.complete("SYS", [{"role": "user", "content": "hi"}])
    assert out == "from anthropic"


def test_stream_relays_openrouter_deltas(monkeypatch):
    from app import llm

    class _Delta:
        def __init__(self, c): self.content = c
    class _Choice:
        def __init__(self, c): self.delta = _Delta(c)
    class _Chunk:
        def __init__(self, c): self.choices = [_Choice(c)]
    class _Completions:
        def create(self, **kw):
            assert kw.get("stream") is True
            return iter([_Chunk("Hel"), _Chunk(None), _Chunk("lo")])
    class _Chat:
        completions = _Completions()
    class _Client:
        chat = _Chat()
    monkeypatch.setattr(llm, "_openai_client", lambda s: _Client())
    out = list(llm.stream(system="s", messages=[{"role": "user", "content": "x"}]))
    assert "".join(out) == "Hello"
