"""Optional LLM enrichment of index metadata (keywords, proof techniques,
key-theorem summaries). One short completion per paper at ingest time.
Best-effort: any failure is reported as a warning and ingestion proceeds."""

from __future__ import annotations

import json
import re

from .config import Config

_PROMPT = """You are indexing an academic paper for a search index. Based on the
metadata below, return ONLY a JSON object with keys:
  "keywords": 5-10 short search keywords (topics, methods, subfields),
  "proof_techniques": up to 5 named proof techniques used or likely used,
  "key_theorems": up to 5 one-line summaries of the main formal results.
No prose, no markdown fences — just the JSON object.

Title: {title}
Abstract: {abstract}
Theorem titles: {theorems}
Sections: {sections}
"""


def enrich_entry(cfg: Config, entry: dict) -> dict:
    from .providers import get_provider

    provider = get_provider(cfg)
    prompt = _PROMPT.format(
        title=entry.get("title", ""),
        abstract=(entry.get("abstract", "") or "")[:2000],
        theorems="; ".join(entry.get("key_theorems", [])[:10]),
        sections=", ".join(entry.get("available_sections", [])),
    )
    text = provider.complete(
        system="You produce strict JSON for a paper search index.",
        prompt=prompt,
    )
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("enrichment response contained no JSON object")
    data = json.loads(m.group(0))
    out: dict = {}
    for key in ("keywords", "proof_techniques", "key_theorems"):
        val = data.get(key)
        if isinstance(val, list) and all(isinstance(x, str) for x in val):
            out[key] = val
    return out
