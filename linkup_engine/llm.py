"""
A tiny, swappable LLM layer.

Linkup is the engine that gets your agent *fresh, real-world facts*. The LLM is
just the reasoning/formatting layer on top. This module keeps that layer behind a
one-method interface so you can swap models without touching agent logic.

Default provider: Anthropic Claude (claude-sonnet-4-6 — fast + cheap + strong at
tool use and synthesis; bump to claude-opus-4-8 for the hardest reasoning).

    from linkup_engine.llm import get_llm
    llm = get_llm()                          # Anthropic by default
    llm = get_llm("openai", model="gpt-...")  # swap providers in one line

Every provider exposes the same call:
    llm.complete(system="...", user="...", max_tokens=1024) -> str

See docs/06-providers.md for the full menu of providers you can drop in here.
"""

from __future__ import annotations

import os
from typing import Protocol


class LLM(Protocol):
    """The only interface an agent depends on."""

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str: ...


class AnthropicLLM:
    """Default. Requires `pip install anthropic` and ANTHROPIC_API_KEY."""

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None):
        from anthropic import Anthropic

        self.model = model
        self.client = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in msg.content if block.type == "text")


class OpenAILLM:
    """Drop-in alternative. Requires `pip install openai` and OPENAI_API_KEY."""

    def __init__(self, model: str = "gpt-4.1", api_key: str | None = None):
        from openai import OpenAI

        self.model = model
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content or ""


_PROVIDERS = {"anthropic": AnthropicLLM, "openai": OpenAILLM}


def get_llm(provider: str | None = None, **kwargs) -> LLM:
    """Factory. `provider` defaults to $LLM_PROVIDER, then 'anthropic'.

    To add Gemini, Mistral, Bedrock, Groq, Ollama, etc.: write a class with a
    `complete(system, user, max_tokens)` method and register it in _PROVIDERS.
    docs/06-providers.md lists concrete options and install snippets.
    """
    name = (provider or os.environ.get("LLM_PROVIDER") or "anthropic").lower()
    if name not in _PROVIDERS:
        raise ValueError(f"Unknown LLM provider {name!r}. Known: {list(_PROVIDERS)}")
    return _PROVIDERS[name](**kwargs)
