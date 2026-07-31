"""Claude via the official `anthropic` SDK and a metered API key.

Native Messages API tool use — never an OpenAI-compatibility shim:
- tools passed flat as {name, description, input_schema};
- loop on stop_reason == "tool_use"; ALL tool_result blocks for a turn go back
  in a single user message (splitting them degrades parallel tool use);
- adaptive thinking; no temperature/top_p/top_k (rejected on Opus 4.7+);
- prompt caching: the system block carries cache_control so the stable prefix
  (tools + system + growing history) is cached across loop iterations.
"""

from __future__ import annotations

from ..config import Config
from ..tools.spec import ToolSet
from .base import OnEvent, TextEvent, ToolCallEvent, ToolResultEvent

DEFAULT_MODEL = "claude-opus-4-8"
MAX_TOKENS = 16000


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, cfg: Config):
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                'The anthropic SDK is not installed: pip install -e ".[providers]"'
            ) from exc
        key = cfg.provider.api_key()
        # No explicit key → the SDK resolves ANTHROPIC_API_KEY / `ant auth login`.
        self._client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
        self.model = cfg.provider.model or DEFAULT_MODEL
        self.max_turns = cfg.agent.max_turns
        self.turns = 0
        self.cache_read_tokens = 0

    # -- helpers ------------------------------------------------------------

    def _wire_tools(self, tools: ToolSet) -> list[dict]:
        return [{"name": s.name, "description": s.description,
                 "input_schema": s.input_schema} for s in tools]

    def _system_block(self, system: str) -> list[dict]:
        return [{"type": "text", "text": system,
                 "cache_control": {"type": "ephemeral"}}]

    def _create(self, system: str, messages: list, wire_tools: list | None):
        kwargs = dict(
            model=self.model,
            max_tokens=MAX_TOKENS,
            thinking={"type": "adaptive"},
            system=self._system_block(system),
            messages=messages,
        )
        if wire_tools:
            kwargs["tools"] = wire_tools
        resp = self._client.messages.create(**kwargs)
        usage = getattr(resp, "usage", None)
        if usage is not None:
            self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        return resp

    @staticmethod
    def _text_of(resp) -> str:
        return "\n".join(b.text for b in resp.content if b.type == "text").strip()

    # -- Provider protocol --------------------------------------------------

    def run(self, system: str, question: str, tools: ToolSet,
            on_event: OnEvent | None = None) -> str:
        wire_tools = self._wire_tools(tools)
        messages: list = [{"role": "user", "content": question}]
        self.turns = 0

        while True:
            self.turns += 1
            resp = self._create(system, messages, wire_tools)

            if resp.stop_reason != "tool_use" or self.turns >= self.max_turns:
                answer = self._text_of(resp)
                if resp.stop_reason == "refusal":
                    answer = answer or "(request declined by the model's safety layer)"
                if on_event:
                    on_event(TextEvent(answer))
                return answer

            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                if on_event:
                    on_event(ToolCallEvent(block.name, dict(block.input)))
                result, is_error = tools.execute(block.name, dict(block.input))
                if on_event:
                    on_event(ToolResultEvent(block.name, result, is_error))
                tr: dict = {"type": "tool_result", "tool_use_id": block.id,
                            "content": result}
                if is_error:
                    tr["is_error"] = True
                tool_results.append(tr)
            # all results for the turn in ONE user message
            messages.append({"role": "user", "content": tool_results})

    def complete(self, system: str, prompt: str) -> str:
        resp = self._create(system, [{"role": "user", "content": prompt}], None)
        return self._text_of(resp)
