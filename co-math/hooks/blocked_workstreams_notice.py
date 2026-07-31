#!/usr/bin/env python3
"""Stop hook: surface blocked workstreams to the user before the assistant
finishes its turn.

Reads workstreams/*/status.md and, if any workstream has status 'blocked',
prints a notice on stderr. Exit code remains 0 — this is informational.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import find_project_root  # noqa: E402


def main() -> None:
    cwd = Path(os.getcwd())
    project_root = find_project_root(cwd)
    if project_root is None:
        return

    workstreams_dir = project_root / "workstreams"
    if not workstreams_dir.is_dir():
        return

    blocked: list[str] = []
    for status_file in workstreams_dir.glob("*/status.md"):
        try:
            text = status_file.read_text().strip().lower()
        except Exception:
            continue
        if "blocked" in text:
            blocked.append(status_file.parent.name)

    if blocked:
        msg = (
            "[co-math] Blocked workstreams need attention: "
            + ", ".join(blocked)
            + ". Read .co-math/approvals/<id>-escalation.md or the workstream's "
            + "report.md for details."
        )
        # Emit on stderr so it surfaces back to Claude without altering the
        # tool decision.
        print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()
