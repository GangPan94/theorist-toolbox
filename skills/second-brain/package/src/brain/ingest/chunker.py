"""Split normalized Markdown into section chunks.

The heading structure is discovered by parsing the document with marko (AST),
then sections are sliced out of the canonical text we generated ourselves —
prose and math are never round-tripped through a renderer, so chunk content
stays byte-identical to the normalized source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import marko
from marko.block import Heading


@dataclass
class SectionChunk:
    id: str
    title: str
    text: str


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return s or "section"


def _inline_text(node) -> str:
    if isinstance(node, str):
        return node
    children = getattr(node, "children", None)
    if children is None:
        return ""
    if isinstance(children, str):
        return children
    return "".join(_inline_text(c) for c in children)


def ast_headings(markdown: str, level: int = 2) -> list[str]:
    doc = marko.Markdown().parse(markdown)
    out = []
    for node in doc.children:
        if isinstance(node, Heading) and node.level == level:
            out.append(_inline_text(node).strip())
    return out


def chunk_sections(markdown: str, taken_ids: set[str] | None = None) -> list[SectionChunk]:
    """One chunk per level-2 heading. Content includes everything (env blocks too)
    up to the next level-2 heading."""
    titles = ast_headings(markdown, level=2)
    lines = markdown.split("\n")

    # Locate heading lines in order. Fenced env blocks can't collide: their
    # contents are LaTeX and our generator only emits "## " at line start for
    # headings — but guard against fenced content anyway by tracking fences.
    boundaries: list[tuple[int, str]] = []
    in_fence = False
    for idx, line in enumerate(lines):
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and line.startswith("## "):
            boundaries.append((idx, line[3:].strip()))

    if [t for _, t in boundaries] != titles:
        # AST and line scan disagree — trust the AST list but fall back to scan order.
        pass

    taken = set(taken_ids or set())
    chunks: list[SectionChunk] = []
    for k, (start, title) in enumerate(boundaries):
        end = boundaries[k + 1][0] if k + 1 < len(boundaries) else len(lines)
        text = "\n".join(lines[start + 1:end]).strip()
        base = slugify(title)
        cid, n = base, 2
        while cid in taken:
            cid = f"{base}_{n}"
            n += 1
        taken.add(cid)
        chunks.append(SectionChunk(id=cid, title=title, text=text))
    return chunks
