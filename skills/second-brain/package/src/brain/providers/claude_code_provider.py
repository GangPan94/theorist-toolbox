"""Claude via your Claude subscription — no API key, no per-token billing.

Built on the Claude Agent SDK (`claude-agent-sdk`), which drives the locally
installed Claude Code and authenticates with its stored login. The SDK owns the
agent loop; we only supply the system prompt and our five tools, exposed as an
in-process MCP server. The toolset is restricted to those five tools so the
agent stays a pure reader of the library.

Prerequisites: Claude Code installed and logged in (`claude` → `/login`).
Leave ANTHROPIC_API_KEY unset in this shell — if set, it overrides the
subscription login and bills the API instead.
"""

from __future__ import annotations

import asyncio

from ..config import Config
from ..tools.spec import ToolSet
from .base import OnEvent, TextEvent, ToolCallEvent, ToolResultEvent

SERVER_NAME = "brain"


def _sdk():
    try:
        import claude_agent_sdk
        return claude_agent_sdk
    except ImportError as exc:
        raise RuntimeError(
            "The Claude Agent SDK is not installed. Install it with:\n"
            '    pip install -e ".[providers]"\n'
            "and make sure Claude Code itself is installed and logged in "
            "(run `claude`, then /login)."
        ) from exc


class ClaudeCodeProvider:
    name = "claude-code"

    def __init__(self, cfg: Config):
        self._sdk = _sdk()
        self.model = cfg.provider.model or None  # None → Claude Code's default
        self.max_turns = cfg.agent.max_turns

    # -- tool bridging ------------------------------------------------------

    def _mcp_server(self, tools: ToolSet, on_event: OnEvent | None):
        sdk = self._sdk

        def make_handler(spec):
            async def handler(args: dict) -> dict:
                if on_event:
                    on_event(ToolCallEvent(spec.name, dict(args)))
                result, is_error = tools.execute(spec.name, dict(args))
                if on_event:
                    on_event(ToolResultEvent(spec.name, result, is_error))
                out: dict = {"content": [{"type": "text", "text": result}]}
                if is_error:
                    out["is_error"] = True
                return out
            return handler

        sdk_tools = [
            sdk.tool(spec.name, spec.description, spec.input_schema)(
                make_handler(spec))
            for spec in tools
        ]
        server = sdk.create_sdk_mcp_server(name=SERVER_NAME, version="0.1.0",
                                           tools=sdk_tools)
        allowed = [f"mcp__{SERVER_NAME}__{spec.name}" for spec in tools]
        return server, allowed

    # -- Provider protocol --------------------------------------------------

    def run(self, system: str, question: str, tools: ToolSet,
            on_event: OnEvent | None = None) -> str:
        sdk = self._sdk
        server, allowed = self._mcp_server(tools, on_event)
        options = sdk.ClaudeAgentOptions(
            system_prompt=system,
            mcp_servers={SERVER_NAME: server},
            allowed_tools=allowed,
            max_turns=self.max_turns,
            **({"model": self.model} if self.model else {}),
        )
        return asyncio.run(self._run_async(question, options, on_event))

    async def _run_async(self, question: str, options, on_event: OnEvent | None) -> str:
        sdk = self._sdk
        final_text: list[str] = []
        result_text: str | None = None
        async for message in sdk.query(prompt=question, options=options):
            if isinstance(message, sdk.AssistantMessage):
                for block in message.content:
                    if isinstance(block, sdk.TextBlock):
                        final_text.append(block.text)
            elif isinstance(message, sdk.ResultMessage):
                result_text = getattr(message, "result", None)
        answer = (result_text or "\n".join(final_text)).strip()
        if on_event:
            on_event(TextEvent(answer))
        return answer

    def complete(self, system: str, prompt: str) -> str:
        sdk = self._sdk
        options = sdk.ClaudeAgentOptions(
            system_prompt=system,
            allowed_tools=[],
            max_turns=1,
            **({"model": self.model} if self.model else {}),
        )
        return asyncio.run(self._run_async(prompt, options, None))
