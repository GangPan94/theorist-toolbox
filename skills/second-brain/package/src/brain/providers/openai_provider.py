"""OpenAI (GPT / Codex-family models) via the official `openai` SDK, using
Chat Completions tool calling. The same adapter serves any OpenAI-compatible
endpoint (Ollama, vLLM, Groq, Gemini compat, DeepSeek, ...) through the
config's base_url — provider name "compat"."""

from __future__ import annotations

import json

from ..config import Config
from ..tools.spec import ToolSet
from .base import OnEvent, TextEvent, ToolCallEvent, ToolResultEvent

DEFAULT_MODEL = "gpt-5.1"


class OpenAIProvider:
    def __init__(self, cfg: Config):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                'The openai SDK is not installed: pip install -e ".[providers]"'
            ) from exc
        self.name = cfg.provider.name  # "openai" or "compat"
        kwargs = {}
        key = cfg.provider.api_key()
        if key:
            kwargs["api_key"] = key
        if cfg.provider.base_url:
            kwargs["base_url"] = cfg.provider.base_url
            kwargs.setdefault("api_key", key or "not-needed")  # local endpoints
        self._client = OpenAI(**kwargs)
        self.model = cfg.provider.model or DEFAULT_MODEL
        self.max_turns = cfg.agent.max_turns

    def _wire_tools(self, tools: ToolSet) -> list[dict]:
        return [{"type": "function",
                 "function": {"name": s.name, "description": s.description,
                              "parameters": s.input_schema}}
                for s in tools]

    def run(self, system: str, question: str, tools: ToolSet,
            on_event: OnEvent | None = None) -> str:
        wire_tools = self._wire_tools(tools)
        messages: list = [{"role": "system", "content": system},
                          {"role": "user", "content": question}]

        for _ in range(self.max_turns):
            resp = self._client.chat.completions.create(
                model=self.model, messages=messages, tools=wire_tools)
            msg = resp.choices[0].message

            if not msg.tool_calls:
                answer = (msg.content or "").strip()
                if on_event:
                    on_event(TextEvent(answer))
                return answer

            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
            })
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                if on_event:
                    on_event(ToolCallEvent(tc.function.name, args))
                result, is_error = tools.execute(tc.function.name, args)
                if on_event:
                    on_event(ToolResultEvent(tc.function.name, result, is_error))
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": result})

        return "(agent stopped: max_turns reached before a final answer)"

    def complete(self, system: str, prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}])
        return (resp.choices[0].message.content or "").strip()
