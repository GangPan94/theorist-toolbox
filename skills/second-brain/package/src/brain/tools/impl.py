"""The five library tools. Descriptions are prescriptive about WHEN to call —
models reach for tools more reliably when the trigger condition is explicit."""

from __future__ import annotations

import datetime as _dt
import difflib
import re
from pathlib import Path

from ..config import Config
from ..index import store
from ..index.search import Searcher
from .spec import ToolSpec


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _fuzzy_pick(wanted: str, candidates: dict[str, str]) -> str | None:
    """candidates: normalized-name -> canonical id. Exact, then close match.
    Fuzziness tolerates formatting variance only — numbers must match exactly,
    so 'Theorem 99' can never silently resolve to 'Theorem 1'."""
    w = _norm(wanted)
    if w in candidates:
        return candidates[w]
    wanted_digits = re.findall(r"\d+", w)
    pool = candidates
    if wanted_digits:
        pool = {k: v for k, v in candidates.items()
                if re.findall(r"\d+", k) == wanted_digits}
    close = difflib.get_close_matches(w, list(pool), n=1, cutoff=0.6)
    return pool[close[0]] if close else None


class _Library:
    """Stateful backend shared by the tool closures (index is re-read lazily so
    a long-lived MCP server sees new ingestions)."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._index_mtime: float | None = None
        self._index: dict = {}
        self._searcher: Searcher | None = None
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_pad = cfg.scratchpad_dir / "sessions" / f"{ts}.md"

    @property
    def index(self) -> dict:
        f = self.cfg.index_file
        mtime = f.stat().st_mtime if f.is_file() else -1.0
        if mtime != self._index_mtime:
            self._index = store.load_index(f)
            self._searcher = Searcher(self.cfg, self._index)
            self._index_mtime = mtime
        return self._index

    @property
    def searcher(self) -> Searcher:
        _ = self.index
        assert self._searcher is not None
        return self._searcher

    def entry(self, paper_id: str) -> dict | None:
        return self.index.get(paper_id)

    def chunk_path(self, paper_id: str, filename: str) -> Path:
        return self.cfg.parsed_dir / paper_id / "chunks" / filename

    def macro_header(self, entry: dict) -> str:
        macros = entry.get("custom_macros", [])
        if not macros:
            return ""
        return ("### CUSTOM MACROS (auto-injected — these definitions apply to all "
                "LaTeX below)\n" + "\n".join(macros) + "\n\n")

    def review_banner(self, paper_id: str, entry: dict) -> str:
        if entry.get("extraction", {}).get("needs_review"):
            return (f"[WARNING: extraction of {paper_id} is flagged needs_review "
                    f"(qa_score={entry['extraction']['qa_score']}); treat the text "
                    "below with caution and say so when citing it.]\n\n")
        return ""


# --------------------------------------------------------------------------
# tool implementations
# --------------------------------------------------------------------------

def make_tools(cfg: Config) -> list[ToolSpec]:
    lib = _Library(cfg)

    def search_library(query: str) -> str:
        hits = lib.searcher.search(query)
        if not hits:
            return ("No papers matched. The library may be empty (use list_papers "
                    "to check) or try different keywords.")
        out = []
        for h in hits:
            flag = "  [NEEDS_REVIEW: extraction untrusted]" if h.needs_review else ""
            out.append(
                f"- paper_id: {h.paper_id}{flag}\n"
                f"  title: {h.title}" + (f" ({h.year})" if h.year else "") + "\n"
                f"  sections: {', '.join(h.available_sections)}\n"
                f"  items: {', '.join(h.env_chunks) or '(none)'}"
                + (f"\n  key results: {'; '.join(h.key_theorems)}"
                   if h.key_theorems else ""))
        return "\n".join(out)

    def list_papers() -> str:
        idx = lib.index
        if not idx:
            return "The library is empty — no papers have been ingested yet."
        lines = []
        for pid in sorted(idx):
            e = idx[pid]
            year = f" ({e['year']})" if e.get("year") else ""
            flag = "  [NEEDS_REVIEW]" if e.get("extraction", {}).get("needs_review") else ""
            lines.append(f"- {pid}: {e.get('title', pid)}{year}{flag}")
        return "\n".join(lines)

    def read_section(paper_id: str, section_name: str) -> str:
        entry = lib.entry(paper_id)
        if entry is None:
            return (f"Error: paper {paper_id!r} not found. "
                    f"Known papers: {', '.join(sorted(lib.index)) or '(none)'}")
        sections = {cid: c for cid, c in entry["chunks"].items()
                    if c.get("type") == "section"}
        cand = {}
        for cid, c in sections.items():
            cand[_norm(cid)] = cid
            cand[_norm(c.get("title", cid))] = cid
        cid = _fuzzy_pick(section_name, cand)
        if cid is None:
            titles = [c.get("title", k) for k, c in sections.items()]
            return (f"Error: section {section_name!r} not found in {paper_id}. "
                    f"Available sections: {', '.join(titles)}")
        text = lib.chunk_path(paper_id, sections[cid]["file"]).read_text(encoding="utf-8")
        if cid == "references":
            text = _tag_references(text, lib.index, exclude=paper_id)
        return (lib.review_banner(paper_id, entry) + lib.macro_header(entry)
                + f"### {entry['chunks'][cid].get('title', cid)} [{paper_id}]\n\n{text}")

    def read_theorem_or_proof(paper_id: str, item_name: str) -> str:
        entry = lib.entry(paper_id)
        if entry is None:
            return (f"Error: paper {paper_id!r} not found. "
                    f"Known papers: {', '.join(sorted(lib.index)) or '(none)'}")
        envs = {cid: c for cid, c in entry["chunks"].items()
                if c.get("type") != "section"}
        cand = {}
        for cid, c in envs.items():
            cand[_norm(cid)] = cid
            cand[_norm(c.get("title", cid))] = cid
            # also allow bare "Theorem 1" for "Theorem 1 (Some title)"
            bare = re.sub(r"\(.*?\)", "", c.get("title", "")).strip()
            if bare:
                cand[_norm(bare)] = cid
        cid = _fuzzy_pick(item_name, cand)
        if cid is None:
            titles = [c.get("title", k) for k, c in envs.items()]
            return (f"Error: item {item_name!r} not found in {paper_id}. "
                    f"Available items: {', '.join(titles)}")

        parts = [lib.review_banner(paper_id, entry), lib.macro_header(entry)]
        deps = entry["chunks"][cid].get("dependencies", [])
        bundled = [d for d in deps if d in entry["chunks"]]
        if bundled:
            parts.append("### PREREQUISITES (auto-bundled — the requested item "
                         "relies on these)\n\n")
            for dep in bundled:
                dep_file = entry["chunks"][dep]["file"]
                dep_title = entry["chunks"][dep].get("title", dep)
                dep_text = lib.chunk_path(paper_id, dep_file).read_text(encoding="utf-8")
                parts.append(f"#### {dep_title} [{paper_id}]\n{dep_text}\n\n")
        item_title = entry["chunks"][cid].get("title", cid)
        item_text = lib.chunk_path(paper_id, entry["chunks"][cid]["file"]).read_text(
            encoding="utf-8")
        parts.append(f"### REQUESTED ITEM: {item_title} [{paper_id}]\n{item_text}")
        return "".join(parts)

    def write_to_scratchpad(note: str) -> str:
        lib.session_pad.parent.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%H:%M:%S")
        with open(lib.session_pad, "a", encoding="utf-8") as f:
            f.write(f"- [{stamp}] {note.strip()}\n")
        return f"Saved to scratchpad ({lib.session_pad.name})."

    return [
        ToolSpec(
            name="search_library",
            description=(
                "Search the local paper library by topic, method, proof technique, "
                "or result (e.g. 'monotone allocation mechanism', 'minimax lower "
                "bound'). Call this FIRST for any question about the papers — it "
                "returns paper_ids plus each paper's sections and formal items, "
                "which you need for the read tools."),
            input_schema={
                "type": "object",
                "properties": {"query": {
                    "type": "string",
                    "description": "Search keywords or phrase."}},
                "required": ["query"],
                "additionalProperties": False},
            fn=search_library),
        ToolSpec(
            name="list_papers",
            description=(
                "List every paper in the library (paper_id, title, year). Call "
                "this when the user asks what the library contains, or when "
                "search_library found nothing and you want to verify coverage."),
            input_schema={"type": "object", "properties": {},
                          "additionalProperties": False},
            fn=list_papers),
        ToolSpec(
            name="read_section",
            description=(
                "Read a full section of a paper (e.g. 'Introduction', 'Model', "
                "'Main Results') for broad context. Call this to understand a "
                "paper's setup or narrative. For any specific theorem, lemma, "
                "definition, or proof, prefer read_theorem_or_proof instead."),
            input_schema={
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string",
                                 "description": "Paper id from search_library."},
                    "section_name": {"type": "string",
                                     "description": "Section title, e.g. 'Model'."}},
                "required": ["paper_id", "section_name"],
                "additionalProperties": False},
            fn=read_section),
        ToolSpec(
            name="read_theorem_or_proof",
            description=(
                "Fetch the exact LaTeX of a specific theorem, lemma, definition, "
                "assumption, or proof, with the paper's custom macros and all "
                "prerequisite definitions auto-bundled. Call this BEFORE answering "
                "any question about a formal statement or proof step — never "
                "reconstruct mathematics from memory."),
            input_schema={
                "type": "object",
                "properties": {
                    "paper_id": {"type": "string",
                                 "description": "Paper id from search_library."},
                    "item_name": {"type": "string",
                                  "description": "E.g. 'Theorem 1', 'lemma_2', "
                                                 "'Proof of Theorem 1'."}},
                "required": ["paper_id", "item_name"],
                "additionalProperties": False},
            fn=read_theorem_or_proof),
        ToolSpec(
            name="write_to_scratchpad",
            description=(
                "Append a note to your persistent session scratchpad. MANDATORY "
                "whenever you read a Model or Definitions section: record the "
                "formal definitions of variables, environments, and standing "
                "assumptions so later turns can rely on them without re-reading."),
            input_schema={
                "type": "object",
                "properties": {"note": {
                    "type": "string",
                    "description": "The note to persist (notation, definitions, "
                                   "assumptions, partial conclusions)."}},
                "required": ["note"],
                "additionalProperties": False},
            fn=write_to_scratchpad),
    ]


def _tag_references(text: str, index: dict, exclude: str) -> str:
    """Best-effort cross-linking of a References section against the library."""
    titles = {pid: _norm(e.get("title", "")) for pid, e in index.items()
              if pid != exclude and e.get("title")}
    out_lines = []
    for line in text.split("\n"):
        tagged = line
        if line.startswith("- ["):
            nline = _norm(line)
            for pid, t in titles.items():
                # crude containment: enough shared normalized title words
                words = [w for w in t.split() if len(w) > 3]
                if words and sum(w in nline for w in words) >= max(2, len(words) - 1):
                    tagged = f"{line}  [IN LIBRARY: {pid}]"
                    break
        out_lines.append(tagged)
    return "\n".join(out_lines)
