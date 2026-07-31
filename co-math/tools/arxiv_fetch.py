#!/usr/bin/env python3
"""Fetch arxiv metadata for an ID or URL and stash it into the current
co-mathematician project's references/ directory.

Usage:
    python3 arxiv_fetch.py <arxiv-id-or-url> [--pdf] [--key <citekey>]

Output:
    Creates references/<key>/note.md with title, authors, abstract, source URL,
    and a "Verified by literature-reviewer" timestamp.

    With --pdf, also downloads the PDF to references/<key>/paper.pdf.

This script is invoked by the literature-reviewer sub-agent. It uses only the
stdlib so there is nothing to install.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
from _lib import find_project_root  # noqa: E402


ARXIV_API = "http://export.arxiv.org/api/query?id_list={ids}"
ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

ID_RE = re.compile(r"(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)


def normalize_id(raw: str) -> str:
    """Accept an arxiv ID, abs URL, or pdf URL and return the bare ID
    (e.g., '2605.06651')."""
    m = ID_RE.search(raw)
    if not m:
        raise ValueError(f"Could not recognise arxiv id in '{raw}'")
    return m.group(1)


def fetch_metadata(arxiv_id: str) -> dict:
    url = ARXIV_API.format(ids=arxiv_id)
    req = urllib.request.Request(url, headers={"User-Agent": "co-math/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    root = ET.fromstring(body)
    entry = root.find("atom:entry", ARXIV_NS)
    if entry is None:
        raise RuntimeError(f"No arxiv entry found for {arxiv_id}")
    title = (entry.findtext("atom:title", default="", namespaces=ARXIV_NS) or "").strip()
    abstract = (entry.findtext("atom:summary", default="", namespaces=ARXIV_NS) or "").strip()
    published = (entry.findtext("atom:published", default="", namespaces=ARXIV_NS) or "").strip()
    authors = []
    for a in entry.findall("atom:author", ARXIV_NS):
        name = a.findtext("atom:name", default="", namespaces=ARXIV_NS)
        if name:
            authors.append(name.strip())
    abs_link = ""
    pdf_link = ""
    for link in entry.findall("atom:link", ARXIV_NS):
        if link.get("rel") == "alternate":
            abs_link = link.get("href", "")
        if link.get("title") == "pdf":
            pdf_link = link.get("href", "")
    return {
        "id": arxiv_id,
        "title": " ".join(title.split()),
        "authors": authors,
        "abstract": " ".join(abstract.split()),
        "published": published[:10] if published else "",
        "abs_url": abs_link,
        "pdf_url": pdf_link,
    }


def default_key(meta: dict) -> str:
    """Generate a default citekey like 'lastname-2026-arxiv-2605-06651'."""
    last = "anon"
    if meta["authors"]:
        # Last token of first author's name.
        last = meta["authors"][0].split()[-1].lower()
        last = re.sub(r"[^a-z0-9]+", "", last) or "anon"
    year = meta["published"][:4] if meta["published"] else "noyear"
    short_id = meta["id"].replace(".", "-")
    return f"{last}-{year}-arxiv-{short_id}"


def write_note(refs_dir: Path, key: str, meta: dict) -> Path:
    note_dir = refs_dir / key
    note_dir.mkdir(parents=True, exist_ok=True)
    note_path = note_dir / "note.md"
    authors_str = ", ".join(meta["authors"]) if meta["authors"] else "(unknown)"
    today = date.today().isoformat()
    body = f"""# {meta["title"]}

- Citekey: `{key}`
- Authors: {authors_str}
- Published: {meta["published"] or "(unknown)"}
- arXiv ID: {meta["id"]}
- Source: {meta["abs_url"]}
- PDF: {meta["pdf_url"]}
- Verified by literature-reviewer on {today}

## Abstract

{meta["abstract"]}

## Relevance to this workstream

_(literature-reviewer: fill in one paragraph on why this paper matters to the
current workstream's scope.)_

## Key claims used in paper.tex

_(literature-reviewer: list specific results — with section/theorem references
— that the project paper relies on. Add a bullet per claim. Do NOT list
results you have not opened the paper to verify.)_

## Open questions

_(literature-reviewer: anything left unclear from the paper that bears on the
project, or that may require contacting the author / reading a follow-up.)_
"""
    note_path.write_text(body)
    return note_path


def fetch_pdf(pdf_url: str, dest: Path) -> None:
    req = urllib.request.Request(pdf_url, headers={"User-Agent": "co-math/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="arxiv id, abs URL, or pdf URL")
    ap.add_argument("--pdf", action="store_true", help="also download the PDF")
    ap.add_argument("--key", help="override the generated citekey")
    args = ap.parse_args()

    try:
        arxiv_id = normalize_id(args.source)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    project_root = find_project_root(Path(os.getcwd()))
    if project_root is None:
        print(
            "error: not inside a co-math project (no co-math-config.json in any ancestor).",
            file=sys.stderr,
        )
        return 2

    try:
        meta = fetch_metadata(arxiv_id)
    except (urllib.error.URLError, RuntimeError) as e:
        print(f"error fetching metadata for {arxiv_id}: {e}", file=sys.stderr)
        return 1

    key = args.key or default_key(meta)
    note_path = write_note(project_root / "references", key, meta)
    print(f"wrote {note_path.relative_to(project_root)} (citekey: {key})")

    if args.pdf and meta["pdf_url"]:
        pdf_path = project_root / "references" / key / "paper.pdf"
        try:
            fetch_pdf(meta["pdf_url"], pdf_path)
            print(f"wrote {pdf_path.relative_to(project_root)}")
        except urllib.error.URLError as e:
            print(f"warning: could not download PDF: {e}", file=sys.stderr)

    print(f"cite with: \\cite{{{key}}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
