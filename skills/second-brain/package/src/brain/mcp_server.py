"""MCP stdio server exposing the library tools to any MCP client.

Inside Claude Code (billed to your Claude subscription):
    claude mcp add second-brain -- /path/to/.venv/bin/python -m brain.mcp_server
Codex CLI and other MCP clients: register the same command in their MCP config.

The server resolves config.toml by walking up from the working directory, or
from $BRAIN_CONFIG if set — pass the project root as the server's cwd, or set
BRAIN_CONFIG=/path/to/config.toml in the registration.
"""

from __future__ import annotations

import os
from pathlib import Path

from .config import load_config
from .tools.spec import build_toolset


def build_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            'MCP server mode needs the mcp package: pip install -e ".[mcp]"'
        ) from exc

    env_cfg = os.environ.get("BRAIN_CONFIG")
    cfg = load_config(Path(env_cfg) if env_cfg else None)
    cfg.ensure_dirs()
    tools = build_toolset(cfg)
    mcp = FastMCP("second-brain")

    # Explicit typed wrappers: FastMCP derives each tool's schema from the
    # signature; descriptions come from our ToolSpecs so all front doors
    # (CLI agent, MCP) present identical guidance.
    def _desc(name: str) -> str:
        spec = tools.get(name)
        assert spec is not None
        return spec.description

    @mcp.tool(description=_desc("search_library"))
    def search_library(query: str) -> str:
        return tools.execute("search_library", {"query": query})[0]

    @mcp.tool(description=_desc("list_papers"))
    def list_papers() -> str:
        return tools.execute("list_papers", {})[0]

    @mcp.tool(description=_desc("read_section"))
    def read_section(paper_id: str, section_name: str) -> str:
        return tools.execute("read_section", {"paper_id": paper_id,
                                              "section_name": section_name})[0]

    @mcp.tool(description=_desc("read_theorem_or_proof"))
    def read_theorem_or_proof(paper_id: str, item_name: str) -> str:
        return tools.execute("read_theorem_or_proof", {"paper_id": paper_id,
                                                       "item_name": item_name})[0]

    @mcp.tool(description=_desc("write_to_scratchpad"))
    def write_to_scratchpad(note: str) -> str:
        return tools.execute("write_to_scratchpad", {"note": note})[0]

    return mcp


def main() -> None:
    build_server().run()  # stdio transport


if __name__ == "__main__":
    main()
