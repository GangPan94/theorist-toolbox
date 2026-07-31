#!/usr/bin/env python3
"""PreToolUse hook: enforce co-mathematician discipline on paper.tex edits.

Triggered on Write and Edit. If the target file is paper.tex inside a co-math
project, enforces:

1. Every \\begin{theorem|lemma|proposition|corollary} must have a \\proof block
   nearby OR be wrapped in \\unproven{...}. (Always enforced.)
2. In strict_mode: no hand-waving phrases (clearly, obviously, trivially,
   omitted, left to the reader, etc.) outside an \\unproven block.
3. Every \\cite{key} must correspond to references/<key>/note.md.

Outputs a JSON decision; exit code is always 0.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _lib import (  # noqa: E402
    allow,
    block,
    compute_new_content,
    find_handwaves,
    find_project_root,
    find_theorems_without_proof,
    find_unverified_citations,
    read_config,
    read_hook_input,
)


def main() -> None:
    h = read_hook_input()
    if h.tool_name not in {"Write", "Edit"}:
        allow()

    file_path = h.tool_input.get("file_path", "")
    if not file_path.endswith("paper.tex"):
        allow()

    project_root = find_project_root(file_path)
    if project_root is None:
        # Not inside a co-math project — let it pass.
        allow()

    new_content = compute_new_content(h.tool_name, h.tool_input)
    if new_content is None:
        allow()

    config = read_config(project_root)
    strict_mode = bool(config.get("strict_mode", True))

    issues: list[str] = []

    # 1. Theorem-without-proof check.
    bad_theorems = find_theorems_without_proof(new_content)
    if bad_theorems:
        for line, env in bad_theorems:
            issues.append(
                f"Line {line}: \\begin{{{env}}} has no matching \\proof block "
                f"and is not wrapped in \\unproven{{...}}. Either add a proof "
                f"or wrap the result in \\unproven."
            )

    # 2. Hand-waving check (strict mode only).
    if strict_mode:
        handwaves = find_handwaves(new_content)
        if handwaves:
            shown = handwaves[:5]
            for line, phrase in shown:
                issues.append(
                    f"Line {line}: hand-waving phrase '{phrase}' detected. "
                    f"Strict mode is on for this project. Replace with explicit "
                    f"justification, citation, or \\unproven{{...}}."
                )
            if len(handwaves) > 5:
                issues.append(
                    f"... plus {len(handwaves) - 5} more hand-waving instances."
                )

    # 3. Citation validation.
    missing = find_unverified_citations(new_content, project_root)
    if missing:
        issues.append(
            "These \\cite keys have no corresponding references/<key>/note.md: "
            + ", ".join(missing)
            + ". Add a reference note (the literature-reviewer should populate it) "
            + "before citing."
        )

    if issues:
        reason = (
            "Co-mathematician discipline check failed for paper.tex. Fix the "
            "following before this edit can proceed:\n\n- "
            + "\n- ".join(issues)
            + "\n\nIf you want to relax 'strict_mode' for this project, edit "
            + "co-math-config.json and record the rationale in decisions.md."
        )
        block(reason)

    allow()


if __name__ == "__main__":
    main()
