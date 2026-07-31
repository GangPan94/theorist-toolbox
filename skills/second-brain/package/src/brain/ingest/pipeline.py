"""Ingestion orchestration: source → normalize → chunk → deps → QA → index.

Idempotent (content-hash skip) and atomic (chunks land in a temp dir that is
swapped into place together with the index update).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config
from ..index import store
from .chunker import chunk_sections
from .deps import compute_dependencies
from .latex_source import NormalizedPaper, find_main_tex, normalize_tex
from .macros import THEOREM_LIKE_DISPLAYS
from . import qa as qa_mod


@dataclass
class IngestResult:
    paper_id: str
    skipped: bool = False
    needs_review: bool = False
    qa_score: float = 1.0
    n_chunks: int = 0
    warnings: list[str] = field(default_factory=list)


def _resolve_tier0_input(source: Path) -> Path:
    if source.is_dir():
        return find_main_tex(source)
    if source.suffix == ".tex":
        return source
    raise ValueError(f"not a Tier-0 (LaTeX) input: {source}")


def ingest_path(cfg: Config, source: Path, *, paper_id: str | None = None,
                force: bool = False, enrich: bool = True) -> IngestResult:
    """Ingest a local source. Tier is chosen by input type:
    .tex / source directory → Tier 0; .html → Tier 1; .pdf → Tier 2."""
    cfg.ensure_dirs()
    source = source.resolve()

    if source.is_dir() or source.suffix == ".tex":
        main = _resolve_tier0_input(source)
        normalized = normalize_tex(main)
        tier = 0
        hash_basis = main.read_bytes()
    elif source.suffix in (".html", ".htm"):
        from .html_source import normalize_html
        normalized = normalize_html(source)
        tier = 1
        hash_basis = source.read_bytes()
    elif source.suffix == ".pdf":
        from .pdf_marker import normalize_pdf
        normalized = normalize_pdf(source)
        tier = 2
        hash_basis = source.read_bytes()
    else:
        raise ValueError(f"unsupported input type: {source}")

    return _ingest_normalized(cfg, normalized, tier=tier, hash_basis=hash_basis,
                              paper_id=paper_id, force=force, enrich=enrich,
                              fallback_id=source.stem)


def _ingest_normalized(cfg: Config, normalized: NormalizedPaper, *, tier: int,
                       hash_basis: bytes, paper_id: str | None, force: bool,
                       enrich: bool, fallback_id: str) -> IngestResult:
    index = store.load_index(cfg.index_file)
    chash = store.content_hash(hash_basis)

    pid = paper_id or store.make_paper_id(normalized.title, normalized.year,
                                          fallback=fallback_id)
    existing = index.get(pid)
    if existing and not force and existing.get("content_hash") == chash:
        return IngestResult(paper_id=pid, skipped=True,
                            qa_score=existing["extraction"]["qa_score"],
                            needs_review=existing["extraction"]["needs_review"],
                            n_chunks=len(existing.get("chunks", {})))

    env_ids = {r.id for r in normalized.env_records}
    sections = chunk_sections(normalized.markdown, taken_ids=set(env_ids))
    deps = compute_dependencies(normalized.env_records, normalized.label_map,
                                normalized.name_map)
    report = qa_mod.evaluate(normalized.markdown, tier=tier,
                             n_sections=len(sections),
                             n_envs=len(normalized.env_records),
                             pipeline_warnings=normalized.warnings)

    # --- write parsed_papers/<pid>/ atomically -----------------------------
    final_dir = cfg.parsed_dir / pid
    tmp_dir = cfg.parsed_dir / f".tmp-{pid}"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    (tmp_dir / "chunks").mkdir(parents=True)
    (tmp_dir / "source.md").write_text(normalized.markdown, encoding="utf-8")
    for rec in normalized.env_records:
        (tmp_dir / "chunks" / f"{rec.id}.md").write_text(rec.latex, encoding="utf-8")
    for sec in sections:
        (tmp_dir / "chunks" / f"{sec.id}.md").write_text(sec.text, encoding="utf-8")
    (tmp_dir / "qa_report.json").write_text(
        json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    if final_dir.exists():
        shutil.rmtree(final_dir)
    tmp_dir.rename(final_dir)

    # --- index entry -------------------------------------------------------
    chunks_entry = {}
    for rec in normalized.env_records:
        chunks_entry[rec.id] = {"file": f"{rec.id}.md", "type": rec.env_type,
                                "title": rec.title,
                                "dependencies": deps.get(rec.id, [])}
    for sec in sections:
        chunks_entry[sec.id] = {"file": f"{sec.id}.md", "type": "section",
                                "title": sec.title, "dependencies": []}

    entry = {
        "title": normalized.title,
        "authors": normalized.authors,
        "year": normalized.year,
        "abstract": normalized.abstract,
        "keywords": [],
        "proof_techniques": [],
        "key_theorems": [r.title for r in normalized.env_records
                         if r.display in THEOREM_LIKE_DISPLAYS],
        "custom_macros": normalized.macros,
        "available_sections": [s.title for s in sections],
        "chunks": chunks_entry,
        "extraction": {"tier": tier, "qa_score": report.score,
                       "needs_review": report.needs_review},
        "content_hash": chash,
    }

    result = IngestResult(paper_id=pid, qa_score=report.score,
                          needs_review=report.needs_review,
                          n_chunks=len(chunks_entry),
                          warnings=list(report.warnings))

    if enrich:
        try:
            from ..enrich import enrich_entry
            overrides = enrich_entry(cfg, entry)
            entry.update({k: v for k, v in overrides.items() if v})
        except Exception as exc:  # enrichment is best-effort, never blocks ingestion
            result.warnings.append(f"LLM enrichment skipped: {exc}")

    index[pid] = entry
    store.save_index(cfg.index_file, index)
    return result
