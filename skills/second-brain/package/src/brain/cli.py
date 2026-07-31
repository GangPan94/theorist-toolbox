"""Command-line interface: brain ingest | search | ask | repl | status."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .index import store
from .index.search import Searcher
from .providers.base import TextEvent, ToolCallEvent, ToolResultEvent


def _cfg(args):
    cfg = load_config(Path(args.config) if args.config else None)
    if getattr(args, "provider", None):
        cfg.provider.name = args.provider
    if getattr(args, "model", None):
        cfg.provider.model = args.model
    cfg.ensure_dirs()
    return cfg


def _event_printer(verbose: bool):
    def on_event(ev):
        if isinstance(ev, ToolCallEvent):
            print(f"  -> {ev.name}({ev.args})", file=sys.stderr)
        elif isinstance(ev, ToolResultEvent) and verbose:
            preview = ev.result[:400].replace("\n", "\n     ")
            flag = " [ERROR]" if ev.is_error else ""
            print(f"  <- {ev.name}{flag}: {preview}", file=sys.stderr)
        elif isinstance(ev, TextEvent):
            pass  # final answer printed by the command
    return on_event


def cmd_ingest(args) -> int:
    cfg = _cfg(args)
    from .ingest.acquire import resolve_source
    from .ingest.pipeline import ingest_path

    rc = 0
    for spec in args.sources:
        try:
            source = resolve_source(spec, cfg.papers_dir)
            result = ingest_path(cfg, source, paper_id=args.id,
                                 force=args.force, enrich=not args.no_llm)
        except Exception as exc:
            print(f"[FAIL] {spec}: {exc}", file=sys.stderr)
            rc = 1
            continue
        state = "skipped (unchanged)" if result.skipped else \
                f"ingested ({result.n_chunks} chunks, qa={result.qa_score})"
        flag = "  ⚠ NEEDS REVIEW" if result.needs_review else ""
        print(f"[ok] {result.paper_id}: {state}{flag}")
        for w in result.warnings:
            print(f"     warning: {w}", file=sys.stderr)
    return rc


def cmd_search(args) -> int:
    cfg = _cfg(args)
    hits = Searcher(cfg, store.load_index(cfg.index_file)).search(
        args.query, top_k=args.k)
    if not hits:
        print("no results")
        return 1
    for h in hits:
        year = f" ({h.year})" if h.year else ""
        flag = "  ⚠ needs_review" if h.needs_review else ""
        print(f"{h.score:8.5f}  {h.paper_id}: {h.title}{year}{flag}")
        if args.verbose:
            print(f"          sections: {', '.join(h.available_sections)}")
            print(f"          items:    {', '.join(h.env_chunks)}")
    return 0


def cmd_ask(args) -> int:
    cfg = _cfg(args)
    from .agent import run_agent
    answer = run_agent(cfg, args.question,
                       on_event=_event_printer(args.verbose))
    print(answer)
    return 0


def cmd_repl(args) -> int:
    cfg = _cfg(args)
    from .agent import run_agent
    from .providers.base import get_provider
    from .tools.spec import build_toolset

    provider = get_provider(cfg)
    tools = build_toolset(cfg)  # one toolset → one session scratchpad
    print(f"second-brain repl — provider: {cfg.provider.name}"
          f"{' (' + cfg.provider.model + ')' if cfg.provider.model else ''}. "
          "Empty line or Ctrl-D to exit.")
    while True:
        try:
            question = input("\n? ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            break
        answer = run_agent(cfg, question, provider=provider, tools=tools,
                           on_event=_event_printer(args.verbose))
        print(f"\n{answer}")
    return 0


def cmd_status(args) -> int:
    cfg = _cfg(args)
    index = store.load_index(cfg.index_file)
    print(f"library root:  {cfg.root}")
    print(f"papers:        {len(index)}")
    tiers: dict[int, int] = {}
    flagged = []
    for pid, e in sorted(index.items()):
        tier = e.get("extraction", {}).get("tier", -1)
        tiers[tier] = tiers.get(tier, 0) + 1
        if e.get("extraction", {}).get("needs_review"):
            flagged.append((pid, e["extraction"]["qa_score"]))
    for tier in sorted(tiers):
        label = {0: "tier 0 (LaTeX source)", 1: "tier 1 (HTML)",
                 2: "tier 2 (Marker OCR)"}.get(tier, f"tier {tier}")
        print(f"  {label}: {tiers[tier]}")
    if flagged:
        print("needs review:")
        for pid, score in flagged:
            print(f"  ⚠ {pid} (qa_score={score})")
    else:
        print("needs review:  none")
    print(f"provider:      {cfg.provider.name}"
          f"{' / ' + cfg.provider.model if cfg.provider.model else ''}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="brain",
        description="Agentic second brain over a local library of papers.")
    parser.add_argument("--config", help="path to config.toml "
                        "(default: walk up from cwd)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="ingest papers (path, .tex dir, arXiv id, URL)")
    p.add_argument("sources", nargs="+")
    p.add_argument("--id", help="explicit paper_id (single source only)")
    p.add_argument("--force", action="store_true", help="re-ingest even if unchanged")
    p.add_argument("--no-llm", action="store_true",
                   help="skip LLM metadata enrichment")
    p.set_defaults(fn=cmd_ingest)

    p = sub.add_parser("search", help="query the index (no LLM)")
    p.add_argument("query")
    p.add_argument("-k", type=int, default=None, help="number of results")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(fn=cmd_search)

    p = sub.add_parser("ask", help="ask the agent a question")
    p.add_argument("question")
    p.add_argument("--provider", choices=["claude-code", "anthropic",
                                          "openai", "compat", "fake"])
    p.add_argument("--model")
    p.add_argument("-v", "--verbose", action="store_true",
                   help="print tool calls and results")
    p.set_defaults(fn=cmd_ask)

    p = sub.add_parser("repl", help="multi-turn session with a shared scratchpad")
    p.add_argument("--provider", choices=["claude-code", "anthropic",
                                          "openai", "compat", "fake"])
    p.add_argument("--model")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(fn=cmd_repl)

    p = sub.add_parser("status", help="library overview and flagged papers")
    p.set_defaults(fn=cmd_status)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
