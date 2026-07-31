#!/usr/bin/env python3
"""PreToolUse hook: block workstream completion without reviewer approval.

Triggered on Write and Edit. If the target file is
workstreams/W{NNN}-*/status.md inside a co-math project, and the new content
sets the status to 'complete', this hook checks for an approval file at
.co-math/approvals/<workstream-id>-*.md with `Verdict: APPROVE`. If none
exists, the edit is blocked.

This implements section 3.4 of the AI Co-Mathematician paper (Zheng et al., 2026):
'Before a report can be marked as finalized and the workstream completed, the
report must be submitted to a paper review process ... which only concludes
once all reviewers have formally approved the report.'
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import (  # noqa: E402
    allow,
    block,
    compute_new_content,
    find_project_root,
    read_hook_input,
)


WORKSTREAM_PATH_RE = re.compile(r"workstreams/(W\d+-[^/]+)/status\.md$")
COMPLETE_RE = re.compile(r"^\s*(status\s*[:=]\s*)?complete\s*$", re.IGNORECASE | re.MULTILINE)
APPROVE_RE = re.compile(r"verdict\s*[:=]\s*APPROVE\b", re.IGNORECASE)


def main() -> None:
    h = read_hook_input()
    if h.tool_name not in {"Write", "Edit"}:
        allow()

    file_path = h.tool_input.get("file_path", "")
    m = WORKSTREAM_PATH_RE.search(file_path)
    if not m:
        allow()

    workstream_id = m.group(1)

    project_root = find_project_root(file_path)
    if project_root is None:
        allow()

    new_content = compute_new_content(h.tool_name, h.tool_input)
    if new_content is None:
        allow()

    if not COMPLETE_RE.search(new_content):
        # Not transitioning to 'complete'; nothing to enforce.
        allow()

    approvals_dir = project_root / ".co-math" / "approvals"
    if not approvals_dir.exists():
        block(
            f"Cannot mark workstream {workstream_id} as 'complete': "
            f"no approvals directory at {approvals_dir}. The paper-reviewer "
            f"agent must review this workstream and write an approval file "
            f"with 'Verdict: APPROVE' before completion."
        )

    found_approve = False
    matching_files: list[Path] = []
    for f in approvals_dir.glob(f"{workstream_id}-*.md"):
        matching_files.append(f)
        try:
            text = f.read_text()
        except Exception:
            continue
        if APPROVE_RE.search(text):
            found_approve = True
            break

    if not found_approve:
        if matching_files:
            list_str = ", ".join(p.name for p in matching_files)
            block(
                f"Cannot mark workstream {workstream_id} as 'complete': "
                f"approval file(s) found ({list_str}) but none contain "
                f"'Verdict: APPROVE'. The paper-reviewer agent must approve "
                f"the workstream before it can be completed."
            )
        else:
            block(
                f"Cannot mark workstream {workstream_id} as 'complete': "
                f"no approval file at {approvals_dir}/{workstream_id}-*.md. "
                f"Invoke the paper-reviewer agent to review this workstream "
                f"first."
            )

    allow()


if __name__ == "__main__":
    main()
