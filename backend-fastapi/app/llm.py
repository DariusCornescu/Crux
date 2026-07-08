"""LLM provider abstraction (spec 2026-07-05-hosting-and-openrouter-design).

One entry point, complete(), dispatches to OpenRouter (default, OpenAI-compatible)
or the Anthropic SDK based on settings.llm_provider. When the selected provider
has no API key, is_configured() returns False and callers use their existing
deterministic offline fallback.
"""
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def is_configured() -> bool:
    s = get_settings()
    if s.llm_provider == "anthropic":
        return bool(s.anthropic_api_key)
    return bool(s.openrouter_api_key)


def complete(system: str, messages: list[dict], max_tokens: int = 1000) -> str:
    """Return the assistant's text for `system` + `messages` via the configured provider.

    `messages` items are {"role": "user"|"assistant", "content": str}.
    """
    s = get_settings()
    if s.llm_provider == "anthropic":
        return _anthropic_complete(s, system, messages, max_tokens)
    return _openrouter_complete(s, system, messages, max_tokens)


def _openai_client(s):
    from openai import OpenAI

    return OpenAI(api_key=s.openrouter_api_key, base_url=_OPENROUTER_BASE_URL)


def _openrouter_complete(s, system, messages, max_tokens):
    client = _openai_client(s)
    resp = client.chat.completions.create(
        model=s.openrouter_model,
        max_tokens=max_tokens,
        messages=[{"role": "system", "content": system}, *messages],
    )
    return resp.choices[0].message.content or ""


def _anthropic_complete(s, system, messages, max_tokens):
    import anthropic

    client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    resp = client.messages.create(
        model=s.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def stream(system: str, messages: list[dict], max_tokens: int = 1000):
    """Yield text deltas from the configured provider."""
    s = get_settings()
    if s.llm_provider == "anthropic":
        yield from _anthropic_stream(s, system, messages, max_tokens)
    else:
        yield from _openrouter_stream(s, system, messages, max_tokens)


def _openrouter_stream(s, system, messages, max_tokens):
    client = _openai_client(s)
    resp = client.chat.completions.create(
        model=s.openrouter_model, max_tokens=max_tokens, stream=True,
        messages=[{"role": "system", "content": system}, *messages],
    )
    for chunk in resp:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def _anthropic_stream(s, system, messages, max_tokens):
    import anthropic

    client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    with client.messages.stream(model=s.anthropic_model, max_tokens=max_tokens,
                                system=system, messages=messages) as stream:
        yield from stream.text_stream
