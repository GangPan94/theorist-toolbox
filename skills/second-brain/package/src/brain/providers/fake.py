"""Scripted provider for offline end-to-end tests. Executes a fixed sequence of
tool calls (results are recorded but do not influence the script), then returns
a canned final answer. Optionally, the final answer is produced by a callback
that sees all tool results — enough to assert real content flowed through."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from ..tools.spec import ToolSet
from .base import OnEvent, TextEvent, ToolCallEvent, ToolResultEvent


@dataclass
class ScriptedCall:
    name: str
    args: dict


@dataclass
class FakeProvider:
    script: list[ScriptedCall] = field(default_factory=list)
    final: str = "(no answer scripted)"
    finalize: Callable[[list[str]], str] | None = None
    name: str = "fake"
    transcript: list[tuple[str, str, bool]] = field(default_factory=list)

    def run(self, system: str, question: str, tools: ToolSet,
            on_event: OnEvent | None = None) -> str:
        results: list[str] = []
        for call in self.script:
            if on_event:
                on_event(ToolCallEvent(call.name, call.args))
            result, is_error = tools.execute(call.name, call.args)
            self.transcript.append((call.name, result, is_error))
            results.append(result)
            if on_event:
                on_event(ToolResultEvent(call.name, result, is_error))
        answer = self.finalize(results) if self.finalize else self.final
        if on_event:
            on_event(TextEvent(answer))
        return answer

    def complete(self, system: str, prompt: str) -> str:
        return ('{"keywords": ["fake"], "proof_techniques": [], '
                '"key_theorems": []}')
