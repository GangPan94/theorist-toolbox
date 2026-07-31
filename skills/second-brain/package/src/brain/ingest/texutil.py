"""Low-level LaTeX scanning helpers shared by the ingestion modules.

These operate on source *strings* with explicit brace/environment matching —
no "regex over the whole paper" chunking. The higher-level structure decisions
live in latex_source.py.
"""

from __future__ import annotations

import re
from pathlib import Path

MAX_INPUT_DEPTH = 10


def strip_comments(tex: str) -> str:
    """Remove % comments to end of line, preserving escaped \\%."""
    out_lines = []
    for line in tex.split("\n"):
        i = 0
        cut = None
        while i < len(line):
            ch = line[i]
            if ch == "\\":
                i += 2  # skip escaped char (covers \% and \\)
                continue
            if ch == "%":
                cut = i
                break
            i += 1
        out_lines.append(line if cut is None else line[:cut].rstrip())
    return "\n".join(out_lines)


def read_group(s: str, i: int) -> tuple[str, int]:
    """Read a {...} group starting at s[i] == '{'. Returns (content, index after '}')."""
    if i >= len(s) or s[i] != "{":
        raise ValueError(f"expected '{{' at index {i}")
    depth = 0
    j = i
    while j < len(s):
        ch = s[j]
        if ch == "\\":
            j += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced braces")


def read_optional(s: str, i: int) -> tuple[str | None, int]:
    """Read an optional [...] group at s[i] if present (nesting-aware for braces)."""
    i = skip_ws(s, i)
    if i >= len(s) or s[i] != "[":
        return None, i
    depth_brace = 0
    j = i
    while j < len(s):
        ch = s[j]
        if ch == "\\":
            j += 2
            continue
        if ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace -= 1
        elif ch == "]" and depth_brace == 0:
            return s[i + 1:j], j + 1
        j += 1
    return None, i


def skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i] in " \t\n":
        i += 1
    return i


def find_matching_end(body: str, env: str, start: int) -> tuple[str, int, int]:
    """Given `start` pointing just after `\\begin{env}`'s closing brace, find the
    matching `\\end{env}`. Returns (inner_content, inner_end, index_after_end)."""
    begin_tok = "\\begin{" + env + "}"
    end_tok = "\\end{" + env + "}"
    depth = 1
    i = start
    while i < len(body):
        nb = body.find(begin_tok, i)
        ne = body.find(end_tok, i)
        if ne == -1:
            raise ValueError(f"unclosed environment {env!r}")
        if nb != -1 and nb < ne:
            depth += 1
            i = nb + len(begin_tok)
        else:
            depth -= 1
            if depth == 0:
                return body[start:ne], ne, ne + len(end_tok)
            i = ne + len(end_tok)
    raise ValueError(f"unclosed environment {env!r}")


def inline_inputs(tex: str, base_dir: Path, depth: int = 0) -> str:
    """Recursively inline \\input{...} and \\include{...} from base_dir."""
    if depth > MAX_INPUT_DEPTH:
        return tex
    pattern = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")

    def repl(m: re.Match) -> str:
        name = m.group(1).strip()
        for cand in (base_dir / name, base_dir / f"{name}.tex"):
            if cand.is_file():
                child = cand.read_text(encoding="utf-8", errors="replace")
                return inline_inputs(child, base_dir, depth + 1)
        return m.group(0)  # leave unresolved includes in place

    return pattern.sub(repl, tex)


def find_command_arg(tex: str, command: str) -> str | None:
    """Return the {...} argument of the first occurrence of \\command{...}."""
    pat = re.compile(r"\\" + re.escape(command) + r"(?![a-zA-Z])\s*")
    m = pat.search(tex)
    if not m:
        return None
    i = skip_ws(tex, m.end())
    if i < len(tex) and tex[i] == "{":
        try:
            content, _ = read_group(tex, i)
            return content
        except ValueError:
            return None
    return None


def strip_command(text: str, command: str) -> str:
    """Remove all \\command{...} occurrences (with their argument) from text."""
    pat = re.compile(r"\\" + re.escape(command) + r"(?![a-zA-Z])\s*")
    out = []
    i = 0
    while True:
        m = pat.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        j = skip_ws(text, m.end())
        if j < len(text) and text[j] == "{":
            try:
                _, j = read_group(text, j)
            except ValueError:
                j = m.end()
        i = j
    return "".join(out)
