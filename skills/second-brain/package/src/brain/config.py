"""Configuration loading. All paths resolve relative to the config file's directory."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_NAME = "config.toml"


@dataclass
class ProviderConfig:
    name: str = "claude-code"
    model: str = ""
    base_url: str = ""
    api_key_env: dict[str, str] = field(default_factory=dict)

    def api_key(self) -> str | None:
        env_name = self.api_key_env.get(self.name, "")
        return os.environ.get(env_name) if env_name else None


@dataclass
class AgentConfig:
    max_turns: int = 25
    max_tool_result_chars: int = 30000


@dataclass
class SearchConfig:
    top_k: int = 5
    use_dense: bool = False


@dataclass
class Config:
    root: Path
    provider: ProviderConfig
    agent: AgentConfig
    search: SearchConfig
    papers_dir: Path
    parsed_dir: Path
    index_dir: Path
    scratchpad_dir: Path

    @property
    def index_file(self) -> Path:
        return self.index_dir / "index.json"

    @property
    def embeddings_file(self) -> Path:
        return self.index_dir / "embeddings.npz"

    def ensure_dirs(self) -> None:
        for d in (self.papers_dir, self.parsed_dir, self.index_dir,
                  self.scratchpad_dir, self.scratchpad_dir / "sessions"):
            d.mkdir(parents=True, exist_ok=True)


def find_config(start: Path | None = None) -> Path | None:
    """Walk up from `start` (default: cwd) looking for config.toml."""
    cur = (start or Path.cwd()).resolve()
    for candidate in (cur, *cur.parents):
        p = candidate / DEFAULT_CONFIG_NAME
        if p.is_file():
            return p
    return None


def load_config(path: Path | None = None) -> Config:
    """Load config.toml; missing file or missing keys fall back to defaults rooted at cwd."""
    if path is None:
        path = find_config()
    if path is not None and path.is_file():
        root = path.parent.resolve()
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    else:
        root = Path.cwd().resolve()
        raw = {}

    prov = raw.get("provider", {})
    provider = ProviderConfig(
        name=prov.get("name", "claude-code"),
        model=prov.get("model", ""),
        base_url=prov.get("base_url", ""),
        api_key_env=dict(prov.get("api_keys", {})),
    )
    ag = raw.get("agent", {})
    agent = AgentConfig(
        max_turns=int(ag.get("max_turns", 25)),
        max_tool_result_chars=int(ag.get("max_tool_result_chars", 30000)),
    )
    se = raw.get("search", {})
    search = SearchConfig(
        top_k=int(se.get("top_k", 5)),
        use_dense=bool(se.get("use_dense", False)),
    )
    paths = raw.get("paths", {})

    def _p(key: str, default: str) -> Path:
        val = Path(paths.get(key, default))
        return val if val.is_absolute() else root / val

    return Config(
        root=root,
        provider=provider,
        agent=agent,
        search=search,
        papers_dir=_p("papers", "papers"),
        parsed_dir=_p("parsed", "parsed_papers"),
        index_dir=_p("index", "index"),
        scratchpad_dir=_p("scratchpad", "scratchpad"),
    )
