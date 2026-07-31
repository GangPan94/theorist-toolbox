"""Shared helpers for co-mathematician hooks.

Hooks read a JSON payload from stdin describing the tool call and write a JSON
decision on stdout. See the individual hook scripts for usage.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HookInput:
    tool_name: str
    tool_input: dict
    raw: dict


def read_hook_input() -> HookInput:
    raw = json.load(sys.stdin)
    return HookInput(
        tool_name=raw.get("tool_name", ""),
        tool_input=raw.get("tool_input", {}),
        raw=raw,
    )


def allow() -> None:
    """Default decision: do nothing, let the tool call proceed."""
    sys.exit(0)


def block(reason: str) -> None:
    """Block the tool call and surface a reason to Claude."""
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def warn(message: str) -> None:
    """Surface a non-blocking message back to Claude."""
    print(json.dumps({"decision": "approve", "reason": message}))
    sys.exit(0)


def find_project_root(file_path: str | os.PathLike) -> Path | None:
    """Walk up from file_path until we find a co-math-config.json. Returns
    the directory containing it, or None if we are not inside a co-math project."""
    p = Path(file_path).resolve()
    if p.is_file() or not p.exists():
        p = p.parent
    for ancestor in [p, *p.parents]:
        if (ancestor / "co-math-config.json").exists():
            return ancestor
    return None


def read_config(project_root: Path) -> dict:
    try:
        with (project_root / "co-math-config.json").open() as f:
            return json.load(f)
    except Exception:
        return {}


def compute_new_content(tool_name: str, tool_input: dict) -> str | None:
    """For Write, return the content directly. For Edit, read the existing
    file and apply the substitution. Returns None if we cannot determine the
    new content."""
    file_path = tool_input.get("file_path")
    if not file_path:
        return None
    if tool_name == "Write":
        return tool_input.get("content", "")
    if tool_name == "Edit":
        old = tool_input.get("old_string", "")
        new = tool_input.get("new_string", "")
        replace_all = tool_input.get("replace_all", False)
        try:
            current = Path(file_path).read_text()
        except FileNotFoundError:
            return None
        if replace_all:
            return current.replace(old, new)
        return current.replace(old, new, 1)
    return None


HANDWAVE_PATTERNS = [
    re.compile(r"\bclearly\b", re.IGNORECASE),
    re.compile(r"\bobviously\b", re.IGNORECASE),
    re.compile(r"\bit\s+is\s+easy\s+to\s+see\b", re.IGNORECASE),
    re.compile(r"\bit\s+is\s+trivial\b", re.IGNORECASE),
    re.compile(r"\btrivially\b", re.IGNORECASE),
    re.compile(r"\bby\s+a\s+similar\s+argument\b", re.IGNORECASE),
    re.compile(r"\bsimilarly,?\s+(we|one|it)\b", re.IGNORECASE),
    re.compile(r"\bomitted\s+for\s+brevity\b", re.IGNORECASE),
    re.compile(r"\bomitted\b\s*\.", re.IGNORECASE),
    re.compile(r"\bleft\s+to\s+the\s+reader\b", re.IGNORECASE),
    re.compile(r"\bstraightforward\b", re.IGNORECASE),
]


def find_handwaves(text: str) -> list[tuple[int, str]]:
    """Return [(line_number, matched_phrase), ...] for hand-waving phrases.
    Skips lines that are inside an \\unproven{...} block (rough heuristic:
    skip lines containing the literal '\\unproven{')."""
    findings = []
    for i, line in enumerate(text.splitlines(), start=1):
        if r"\unproven{" in line:
            continue
        # Skip comments
        stripped = line.lstrip()
        if stripped.startswith("%"):
            continue
        for pat in HANDWAVE_PATTERNS:
            m = pat.search(line)
            if m:
                findings.append((i, m.group(0)))
                break
    return findings


THEOREM_BEGIN = re.compile(r"\\begin\{(theorem|lemma|proposition|corollary)\}")
THEOREM_END_PATTERN = r"\\end\{{{}}}"


def find_theorems_without_proof(text: str) -> list[tuple[int, str]]:
    """Find \\begin{theorem|lemma|...} environments that are not followed by
    a \\proof block (or by a wrapping \\unproven). Returns [(line, env_name)]."""
    findings = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = THEOREM_BEGIN.search(lines[i])
        if not m:
            i += 1
            continue
        env = m.group(1)
        start_line = i + 1
        # Find the end of this environment
        end_pat = re.compile(THEOREM_END_PATTERN.format(env))
        j = i
        while j < len(lines) and not end_pat.search(lines[j]):
            j += 1
        # Check that the body or what follows contains \proof, OR is closed by
        # a \leanproved (machine-verified), OR is wrapped in \unproven.
        body = "\n".join(lines[i:j + 1])
        # Look at the next ~30 lines after the theorem env for a proof.
        following = "\n".join(lines[j + 1:min(j + 31, len(lines))])
        has_proof = (
            r"\proof" in body
            or r"\begin{proof}" in following
            or r"\proof" in following
        )
        has_lean = (r"\leanproved{" in body) or (r"\leanproved{" in following)
        wrapped_unproven = r"\unproven{" in body
        if not (has_proof or has_lean or wrapped_unproven):
            findings.append((start_line, env))
        i = j + 1
    return findings


def find_unverified_citations(text: str, project_root: Path) -> list[str]:
    """Find \\cite{key} entries whose corresponding references/<key>/note.md
    does not exist. If references/ itself doesn't exist, every cited key is
    treated as unverified."""
    refs_dir = project_root / "references"
    keys = re.findall(r"\\cite\{([^}]+)\}", text)
    missing = []
    seen = set()
    for keylist in keys:
        for key in (k.strip() for k in keylist.split(",")):
            if not key or key in seen:
                continue
            seen.add(key)
            note = refs_dir / key / "note.md"
            if not note.exists():
                missing.append(key)
    return missing
