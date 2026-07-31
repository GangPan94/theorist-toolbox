#!/usr/bin/env python3
"""Render a compact status view of the current AI co-mathematician project."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
from _lib import find_project_root, read_config  # noqa: E402


STATUS_ORDER = [
    "running",
    "blocked",
    "interrupted",
    "review",
    "planned",
    "complete",
    "failed",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text()
    except Exception:
        return ""


def parse_workstream(ws_dir: Path) -> dict:
    """Read the workstream's status.md, log.md, and instructions.md and
    extract a small summary dict."""
    status_text = read_text(ws_dir / "status.md").strip().lower()
    # Take the first non-empty token-ish thing that matches a known status.
    status = "unknown"
    for s in STATUS_ORDER:
        if s in status_text:
            status = s
            break

    # Try to infer the agent and last-update date from log.md.
    log_text = read_text(ws_dir / "log.md")
    last_date = ""
    date_matches = re.findall(r"\b(20\d{2}-\d{2}-\d{2})\b", log_text)
    if date_matches:
        last_date = date_matches[-1]

    agent = ""
    agent_match = re.search(r"agent[:=]\s*([\w-]+)", log_text, re.IGNORECASE)
    if agent_match:
        agent = agent_match.group(1)

    return {
        "id": ws_dir.name,
        "status": status,
        "last_update": last_date,
        "agent": agent,
    }


def render_project(root: Path) -> str:
    cfg = read_config(root)
    project = cfg.get("project", root.name)
    created = cfg.get("created", "?")
    strict = "ON" if cfg.get("strict_mode", True) else "off"
    fmt = cfg.get("paper_format", "?")

    lines = []
    lines.append(f"Project: {project}")
    lines.append(f"Created: {created}  |  Strict mode: {strict}  |  Paper format: {fmt}")
    lines.append("")

    # Research question + goals
    goals_text = read_text(root / "goals.md")
    if goals_text:
        rq_match = re.search(
            r"##\s*Research question\s*\n+(.*?)(?:\n##|\Z)",
            goals_text,
            re.DOTALL,
        )
        if rq_match:
            rq = rq_match.group(1).strip()
            if rq:
                lines.append("Research question:")
                for ln in rq.splitlines():
                    if ln.strip():
                        lines.append(f"  {ln.strip()}")
                lines.append("")

        approval_match = re.search(
            r"Approval[^\n:]*:\s*\**\s*(YES|NO)", goals_text, re.IGNORECASE
        )
        approval = approval_match.group(1).upper() if approval_match else "NO"
        lines.append(f"Goals (approved: {approval})")

    # Workstreams
    ws_root = root / "workstreams"
    workstreams: list[dict] = []
    if ws_root.is_dir():
        for ws_dir in sorted(ws_root.iterdir()):
            if ws_dir.is_dir() and ws_dir.name.startswith("W"):
                workstreams.append(parse_workstream(ws_dir))

    lines.append("")
    lines.append(f"Workstreams ({len(workstreams)} total)")
    if not workstreams:
        lines.append("  (none yet)")
    else:
        header = f"  {'id':<32} {'status':<10} {'agent':<22} {'last update':<12}"
        lines.append(header)
        for w in workstreams:
            marker = "  <-- needs attention" if w["status"] in {"blocked", "failed", "interrupted"} else ""
            lines.append(
                f"  {w['id']:<32} {w['status'].upper():<10} "
                f"{(w['agent'] or '-'):<22} {(w['last_update'] or '-'):<12}{marker}"
            )

    # Pending reviews
    in_review = [w for w in workstreams if w["status"] == "review"]
    if in_review:
        lines.append("")
        lines.append("Pending reviews")
        for w in in_review:
            lines.append(f"  {w['id']}  -- waiting for paper-reviewer approval")

    # Open obligations in paper.tex
    paper_text = read_text(root / "paper.tex")
    if paper_text:
        unproven_count = paper_text.count(r"\unproven{")
        if unproven_count:
            lines.append("")
            lines.append(f"Open obligations in paper.tex: {unproven_count} \\unproven blocks")

    # Recent decisions
    decisions_text = read_text(root / "decisions.md")
    if decisions_text:
        entries = re.findall(
            r"##\s*(20\d{2}-\d{2}-\d{2})[^\n]*\n+(.*?)(?=\n##|\Z)",
            decisions_text,
            re.DOTALL,
        )
        if entries:
            lines.append("")
            lines.append(f"Recent decisions (showing last {min(3, len(entries))} of {len(entries)})")
            for date, body in entries[:3]:
                first_line = next(
                    (ln.strip().lstrip("-* ") for ln in body.splitlines() if ln.strip()),
                    "",
                )
                if len(first_line) > 80:
                    first_line = first_line[:77] + "..."
                lines.append(f"  {date}  {first_line}")

    # Failed explorations
    failed_dir = root / "failed-explorations"
    if failed_dir.is_dir():
        failed = [
            p for p in failed_dir.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        ]
        if failed:
            lines.append("")
            lines.append(f"Failed explorations: {len(failed)} (see failed-explorations/)")

    return "\n".join(lines)


def main() -> None:
    cwd = Path(os.getcwd())
    root = find_project_root(cwd)
    if root is None:
        print("Not inside a co-mathematician project (no co-math-config.json found).")
        sys.exit(0)
    print(render_project(root))


if __name__ == "__main__":
    main()
