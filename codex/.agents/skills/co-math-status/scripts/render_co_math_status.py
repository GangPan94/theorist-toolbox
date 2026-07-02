#!/usr/bin/env python3
"""Render a compact status view for a co-math project."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from textwrap import shorten


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Project path or a child path inside the project.",
    )
    return parser.parse_args()


def find_project_root(start: Path) -> Path | None:
    current = start.expanduser().resolve()
    if current.is_file():
        current = current.parent
    for path in [current, *current.parents]:
        if (path / "co-math-config.json").exists():
            return path
    return None


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return default


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def extract_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"^## {re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^## ", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()


def approval_status(goals_text: str) -> str:
    match = re.search(r"Goals approved by user:\s*\*\*(YES|NO)\*\*", goals_text, re.I)
    if match:
        return match.group(1).upper()
    match = re.search(r"Goals approved by user:\s*(YES|NO)", goals_text, re.I)
    return match.group(1).upper() if match else "UNKNOWN"


def workstream_rows(root: Path, registry: dict) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    by_id = {str(item.get("id", "")): item for item in registry.get("workstreams", [])}
    workstreams_dir = root / "workstreams"
    if not workstreams_dir.exists():
        return rows

    for child in sorted(p for p in workstreams_dir.iterdir() if p.is_dir()):
        match = re.match(r"W(\d+)-(.+)", child.name)
        wid = match.group(1) if match else child.name
        meta = by_id.get(str(int(wid)) if wid.isdigit() else wid, {})
        status = read_text(child / "status.md", "planned").strip().splitlines()
        rows.append(
            {
                "id": child.name,
                "status": status[0] if status else "planned",
                "agent": str(meta.get("agent", "-")),
                "goal": str(meta.get("goal", "")),
            }
        )
    return rows


def recent_decisions(text: str, limit: int = 3) -> list[str]:
    lines = []
    for line in text.splitlines():
        if line.startswith("## "):
            lines.append(line[3:].strip())
    return lines[:limit]


def main() -> None:
    args = parse_args()
    root = find_project_root(Path(args.path))
    if root is None:
        print("Not inside a co-math project.")
        return

    config = read_json(root / "co-math-config.json", {})
    registry = read_json(root / ".co-math" / "workstream-registry.json", {})
    goals_text = read_text(root / "goals.md")
    decisions_text = read_text(root / "decisions.md")
    paper_text = read_text(root / "paper.tex")
    rows = workstream_rows(root, registry)

    print(f"Project: {config.get('project', root.name)}")
    print(
        "Created: {created} | Strict mode: {strict} | Paper format: {fmt}".format(
            created=config.get("created", "unknown"),
            strict="ON" if config.get("strict_mode", True) else "OFF",
            fmt=config.get("paper_format", "unknown"),
        )
    )
    print(f"Path: {root}")
    print()

    question = extract_section(goals_text, "Research question")
    print("Research question:")
    print(f"  {shorten(question or '(missing)', width=100, placeholder='...')}")
    print()

    print(f"Goals approved: {approval_status(goals_text)}")
    print()

    if rows:
        print("Workstreams")
        print(f"{'id':32} {'status':12} {'agent':28} goal")
        for row in rows:
            print(
                f"{row['id'][:32]:32} {row['status'][:12]:12} "
                f"{row['agent'][:28]:28} {shorten(row['goal'], width=50, placeholder='...')}"
            )
    else:
        print("Workstreams: none")
    print()

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"].lower()] = counts.get(row["status"].lower(), 0) + 1
    if counts:
        summary = ", ".join(f"{key}: {counts[key]}" for key in sorted(counts))
        print(f"Status counts: {summary}")

    unproven_count = len(re.findall(r"\\unproven\{", paper_text))
    print(f"Open obligations in paper.tex: {unproven_count} \\unproven blocks")

    pending_reviews = [row["id"] for row in rows if row["status"].lower() == "review"]
    blocked = [row["id"] for row in rows if row["status"].lower() == "blocked"]
    if pending_reviews:
        print("Pending reviews: " + ", ".join(pending_reviews))
    if blocked:
        print("Blocked: " + ", ".join(blocked))

    decisions = recent_decisions(decisions_text)
    if decisions:
        print()
        print("Recent decisions")
        for item in decisions:
            print(f"  - {item}")


if __name__ == "__main__":
    main()
