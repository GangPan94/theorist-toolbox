"""Tier 1: HTML (ar5iv / publisher pages) → normalized Markdown.

Best-effort: keeps LaTeX from MathML ``alttext`` where present. Output goes
through the same chunker/QA path as Tier 0; theorem environments are only
recovered when the HTML marks them up as such (ar5iv does).
"""

from __future__ import annotations

import re
from pathlib import Path

from .latex_source import NormalizedPaper


def normalize_html(path: Path) -> NormalizedPaper:
    from bs4 import BeautifulSoup  # lazy: [web] extra

    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="replace"),
                         "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    # Replace MathML nodes with their LaTeX alttext when available.
    for math in soup.find_all("math"):
        alt = math.get("alttext")
        math.replace_with(f"${alt}$" if alt else math.get_text(" ", strip=True))

    title_tag = soup.find(["h1"]) or soup.find("title")
    title = title_tag.get_text(" ", strip=True) if title_tag else path.stem

    parts: list[str] = [f"# {title}", ""]
    abstract = ""
    for el in soup.find_all(["h2", "h3", "p", "li", "blockquote"]):
        text = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        if not text:
            continue
        if el.name == "h2":
            parts.append(f"\n## {text}\n")
        elif el.name == "h3":
            parts.append(f"\n### {text}\n")
        else:
            parts.append(text + "\n")
            if not abstract and "abstract" in (el.get("class") or [""])[0].lower():
                abstract = text

    markdown = "\n".join(parts).strip() + "\n"
    if "## " not in markdown:  # give the chunker at least one section
        markdown = markdown.replace("# " + title, f"# {title}\n\n## Body", 1)

    return NormalizedPaper(title=title, authors=[], year=None, abstract=abstract,
                           markdown=markdown, macros=[], macro_names=[],
                           env_records=[], warnings=["tier-1 HTML extraction"])
