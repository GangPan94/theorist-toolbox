"""Neutral tool specification. Providers translate ToolSpec into their native
wire format; the functions themselves are plain Python returning strings.

Hardening rules (enforced in execute()):
- tools never raise to the agent loop — failures come back as "Error: ..." text;
- results larger than the configured budget are truncated with an explicit
  marker so the model knows to ask for something narrower.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

from ..config import Config

TRUNCATION_NOTE = ("\n\n[TRUNCATED: result exceeded the tool output budget. "
                   "Request a narrower item — a specific theorem, lemma, or "
                   "subsection — instead of this larger unit.]")


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    fn: Callable[..., str]
    is_error_marker: str = "Error:"


@dataclass
class ToolSet:
    specs: list[ToolSpec]
    max_result_chars: int = 30000
    _by_name: dict[str, ToolSpec] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._by_name = {s.name: s for s in self.specs}

    def __iter__(self):
        return iter(self.specs)

    def get(self, name: str) -> ToolSpec | None:
        return self._by_name.get(name)

    def execute(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        """Run a tool. Returns (result_text, is_error). Never raises."""
        spec = self.get(name)
        if spec is None:
            return f"Error: unknown tool {name!r}", True
        try:
            result = spec.fn(**args)
        except TypeError as exc:
            return f"Error: bad arguments for {name}: {exc}", True
        except Exception:
            short = traceback.format_exc(limit=2)
            return f"Error: tool {name} failed internally:\n{short}", True
        is_error = result.startswith(spec.is_error_marker)
        if len(result) > self.max_result_chars:
            result = result[: self.max_result_chars] + TRUNCATION_NOTE
        return result, is_error


def build_toolset(cfg: Config) -> ToolSet:
    from .impl import make_tools
    return ToolSet(specs=make_tools(cfg),
                   max_result_chars=cfg.agent.max_tool_result_chars)
