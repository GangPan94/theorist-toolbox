"""Tier 0: normalize LaTeX source into Markdown-with-LaTeX plus environment records.

Guarantee: math and environment bodies pass through byte-identical. Only the
document *skeleton* (sectioning, theorem environments, bibliography) is
converted; prose and math are never round-tripped through a parser.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path

from .macros import TheoremSpec, build_env_map, extract_preamble_info
from .texutil import (find_command_arg, find_matching_end, inline_inputs,
                      read_group, read_optional, skip_ws, strip_command,
                      strip_comments)


@dataclass
class EnvRecord:
    id: str                      # e.g. "theorem_1", "proof_of_theorem_1"
    env_type: str                # "theorem" | "definition" | ... | "proof"
    display: str                 # "Theorem"
    number: str | None           # "1" (None for proofs / unnumbered)
    title: str                   # "Theorem 1 (Optimality ...)" / "Proof of Theorem 1"
    label: str | None            # first \label{...} inside, if any
    latex: str                   # full \begin...\end source, verbatim
    parent: str | None = None    # for proofs: the id of the proved statement


@dataclass
class NormalizedPaper:
    title: str
    authors: list[str]
    year: int | None
    abstract: str
    markdown: str                          # normalized source.md content
    macros: list[str]                      # full macro definition strings
    macro_names: list[str]
    env_records: list[EnvRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def label_map(self) -> dict[str, str]:
        return {r.label: r.id for r in self.env_records if r.label}

    @property
    def name_map(self) -> dict[tuple[str, str], str]:
        return {(r.display.lower(), r.number): r.id
                for r in self.env_records if r.number is not None}


_SECTION_RE = re.compile(r"\\(section|subsection|subsubsection)\*?\s*(?=\{)")
_BEGIN_RE = re.compile(r"\\begin\s*\{([a-zA-Z*]+)\}")
_DROP_RE = re.compile(r"\\(maketitle|tableofcontents|newpage|clearpage|appendix)(?![a-zA-Z])"
                      r"|\\bibliographystyle\s*\{[^}]*\}|\\bibliography\s*\{[^}]*\}")
_LABEL_RE = re.compile(r"\\label\s*\{([^}]+)\}")
_REF_IN_TITLE_RE = re.compile(r"\\[cC]?ref\s*\{([^}]+)\}|\\autoref\s*\{([^}]+)\}")
_NL_TARGET_RE = re.compile(
    r"\b(Theorem|Lemma|Proposition|Corollary|Definition|Assumption|Claim|Remark|"
    r"Example|Fact|Conjecture|Observation)[~\s]+([0-9]+(?:\.[0-9]+)*)")


def normalize_tex(main_file: Path) -> NormalizedPaper:
    raw = main_file.read_text(encoding="utf-8", errors="replace")
    tex = inline_inputs(raw, main_file.parent)
    tex = strip_comments(tex)

    if "\\begin{document}" in tex:
        preamble, _, rest = tex.partition("\\begin{document}")
        body = rest.split("\\end{document}")[0]
    else:
        preamble, body = "", tex

    info = extract_preamble_info(preamble)
    env_map = build_env_map(info)

    title = _clean_title(find_command_arg(tex, "title") or main_file.stem)
    authors = _parse_authors(find_command_arg(tex, "author") or "")
    year = _parse_year(find_command_arg(tex, "date") or "")

    conv = _BodyConverter(env_map)
    body_md, env_records, warnings = conv.convert(body)
    abstract = conv.abstract_text

    md_parts = [f"# {title}", ""]
    md_parts.append(body_md.strip())
    markdown = "\n".join(md_parts).strip() + "\n"

    return NormalizedPaper(
        title=title, authors=authors, year=year, abstract=abstract,
        markdown=markdown,
        macros=[m.definition for m in info.macros],
        macro_names=[m.name for m in info.macros],
        env_records=env_records, warnings=warnings,
    )


def _clean_title(t: str) -> str:
    t = strip_command(t, "thanks")
    t = t.replace("\\\\", " ")
    return re.sub(r"\s+", " ", t).strip()


def _parse_authors(a: str) -> list[str]:
    a = strip_command(strip_command(a, "thanks"), "footnote")
    parts = re.split(r"\\and(?![a-zA-Z])|,", a)
    out = []
    for p in parts:
        p = re.sub(r"\\[a-zA-Z]+", " ", p)
        p = re.sub(r"[{}$]", "", p)
        p = re.sub(r"\s+", " ", p).strip()
        if p:
            out.append(p)
    return out


def _parse_year(d: str) -> int | None:
    m = re.search(r"(19|20)\d{2}", d)
    return int(m.group(0)) if m else None


class _BodyConverter:
    """Sequential scan over the document body. Text between recognized structural
    tokens is copied verbatim; recognized tokens are converted."""

    def __init__(self, env_map: dict[str, TheoremSpec]):
        self.env_map = env_map
        self.counters: dict[str, int] = {}
        self.records: list[EnvRecord] = []
        self.warnings: list[str] = []
        self.abstract_text = ""
        self._last_statement: EnvRecord | None = None
        self._proof_count = 0
        self._id_seen: set[str] = set()

    def convert(self, body: str) -> tuple[str, list[EnvRecord], list[str]]:
        out: list[str] = []
        i = 0
        n = len(body)
        while i < n:
            sec = _SECTION_RE.search(body, i)
            beg = _BEGIN_RE.search(body, i)
            drop = _DROP_RE.search(body, i)
            candidates = [m for m in (sec, beg, drop) if m]
            if not candidates:
                out.append(body[i:])
                break
            nxt = min(candidates, key=lambda m: m.start())
            out.append(body[i:nxt.start()])

            if nxt is drop:
                i = nxt.end()
            elif nxt is sec:
                level = {"section": 2, "subsection": 3, "subsubsection": 4}[nxt.group(1)]
                j = skip_ws(body, nxt.end())
                heading, j = read_group(body, j)
                heading = re.sub(r"\s+", " ", strip_command(heading, "label")).strip()
                out.append(f"\n{'#' * level} {heading}\n")
                i = j
            else:  # \begin{...}
                env = nxt.group(1)
                if env == "abstract":
                    inner, _, after = find_matching_end(body, env, nxt.end())
                    self.abstract_text = re.sub(r"\s+", " ", inner).strip()
                    out.append(f"\n## Abstract\n\n{inner.strip()}\n")
                    i = after
                elif env == "thebibliography":
                    inner, _, after = find_matching_end(body, env, nxt.end())
                    out.append("\n## References\n\n" + self._bibliography(inner))
                    i = after
                elif env in self.env_map or env == "proof":
                    i = self._environment(body, nxt, env, out)
                else:
                    # unrecognized environment (equation, align, figure, ...): verbatim
                    out.append(body[nxt.start():nxt.end()])
                    i = nxt.end()

        return "".join(out), self.records, self.warnings

    # -- helpers ------------------------------------------------------------

    def _environment(self, body: str, m: re.Match, env: str, out: list[str]) -> int:
        opt, j = read_optional(body, m.end())
        try:
            inner, _, after = find_matching_end(body, env, j)
        except ValueError:
            self.warnings.append(f"unclosed environment {env!r}; left verbatim")
            out.append(body[m.start():m.end()])
            return m.end()
        latex = body[m.start():after]
        label_m = _LABEL_RE.search(inner)
        label = label_m.group(1) if label_m else None

        if env == "proof":
            rec = self._proof_record(opt, label, latex)
        else:
            spec = self.env_map[env]
            number = None
            if spec.numbered:
                self.counters[spec.counter] = self.counters.get(spec.counter, 0) + 1
                number = str(self.counters[spec.counter])
            base = f"{spec.display} {number}" if number else spec.display
            title = f"{base} ({opt.strip()})" if opt else base
            cid = self._unique_id(
                f"{spec.display.lower()}_{number}" if number else spec.display.lower())
            rec = EnvRecord(id=cid, env_type=spec.display.lower(), display=spec.display,
                            number=number, title=title, label=label, latex=latex)
            self._last_statement = rec  # a bare \begin{proof} attaches to this

        self.records.append(rec)
        out.append(self._fence(rec))
        return after

    def _proof_record(self, opt: str | None, label: str | None, latex: str) -> EnvRecord:
        parent: EnvRecord | None = None
        if opt:
            # explicit target: "Proof of Theorem~\ref{thm:main}" or "Proof of Theorem 2"
            ref = _REF_IN_TITLE_RE.search(opt)
            if ref:
                target_label = ref.group(1) or ref.group(2)
                parent = next((r for r in self.records if r.label == target_label), None)
            if parent is None:
                nl = _NL_TARGET_RE.search(opt)
                if nl:
                    parent = next((r for r in self.records
                                   if r.display.lower() == nl.group(1).lower()
                                   and r.number == nl.group(2)), None)
        if parent is None:
            parent = self._last_statement
        if parent is not None:
            cid = self._unique_id(f"proof_of_{parent.id}")
            title = f"Proof of {parent.display} {parent.number}" if parent.number \
                else f"Proof of {parent.title}"
        else:
            self._proof_count += 1
            cid = self._unique_id(f"proof_{self._proof_count}")
            title = "Proof"
            self.warnings.append(f"proof at {cid} has no identifiable statement")
        return EnvRecord(id=cid, env_type="proof", display="Proof", number=None,
                         title=title, label=label, latex=latex,
                         parent=parent.id if parent else None)

    def _unique_id(self, base: str) -> str:
        cid, k = base, 2
        while cid in self._id_seen:
            cid = f"{base}_{k}"
            k += 1
        self._id_seen.add(cid)
        return cid

    def _fence(self, rec: EnvRecord) -> str:
        kv = [f"id={rec.id}"]
        if rec.number:
            kv.append(f"number={rec.number}")
        if rec.label:
            kv.append(f"label={shlex.quote(rec.label)}")
        if rec.parent:
            kv.append(f"parent={rec.parent}")
        kv.append(f"title={shlex.quote(rec.title)}")
        return (f"\n```env:{rec.env_type} {' '.join(kv)}\n"
                f"{rec.latex.strip()}\n```\n")

    def _bibliography(self, inner: str) -> str:
        items = re.split(r"\\bibitem\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}", inner)
        # items = [pre, key1, text1, key2, text2, ...]
        lines = []
        for k in range(1, len(items) - 1, 2):
            key = items[k].strip()
            text = re.sub(r"\s+", " ", items[k + 1]).strip()
            lines.append(f"- [{key}] {text}")
        return "\n".join(lines) + "\n"


def find_main_tex(directory: Path) -> Path:
    """Locate the main .tex file (the one with \\documentclass) in a source tree."""
    candidates = sorted(directory.rglob("*.tex"))
    mains = [p for p in candidates
             if "\\documentclass" in p.read_text(encoding="utf-8", errors="replace")]
    if not mains:
        raise FileNotFoundError(f"no .tex file with \\documentclass under {directory}")
    if len(mains) > 1:
        # prefer conventional names, then the largest file
        for name in ("main.tex", "paper.tex", "ms.tex"):
            for p in mains:
                if p.name == name:
                    return p
        mains.sort(key=lambda p: p.stat().st_size, reverse=True)
    return mains[0]
