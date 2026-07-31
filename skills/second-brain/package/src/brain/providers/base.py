"""Provider protocol. Each adapter owns its native agent loop end-to-end —
there is deliberately no cross-provider message-format normalization layer.
Adapters translate ToolSpec into their wire format and call ToolSet.execute().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol, runtime_checkable

from ..config import Config
from ..tools.spec import ToolSet


@dataclass
class ToolCallEvent:
    name: str
    args: dict


@dataclass
class ToolResultEvent:
    name: str
    result: str
    is_error: bool


@dataclass
class TextEvent:
    text: str


OnEvent = Callable[[Any], None]


@runtime_checkable
class Provider(Protocol):
    name: str

    def run(self, system: str, question: str, tools: ToolSet,
            on_event: OnEvent | None = None) -> str:
        """Drive the agentic loop to completion; return the final answer text."""
        ...

    def complete(self, system: str, prompt: str) -> str:
        """One-shot completion (no tools) — used for index enrichment."""
        ...


def get_provider(cfg: Config) -> Provider:
    name = cfg.provider.name
    if name == "fake":
        from .fake import FakeProvider
        return FakeProvider()
    if name == "claude-code":
        from .claude_code_provider import ClaudeCodeProvider
        return ClaudeCodeProvider(cfg)
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(cfg)
    if name in ("openai", "compat"):
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(cfg)
    raise ValueError(f"unknown provider {name!r} "
                     "(expected claude-code | anthropic | openai | compat | fake)")
