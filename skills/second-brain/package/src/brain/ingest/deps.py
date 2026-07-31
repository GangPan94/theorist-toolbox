"""Dependency mapping: which definitions/assumptions/statements does each
environment chunk rely on?  Sources of evidence:
  1. explicit \\ref / \\cref / \\Cref / \\autoref / \\eqref targets whose labels
     belong to an environment chunk;
  2. natural-language references ("by Definition 2", "Assumption 1");
  3. a proof's parent statement (always its first dependency).
"""

from __future__ import annotations

import re

from .latex_source import EnvRecord, _NL_TARGET_RE

_REF_RE = re.compile(r"\\(?:[cC]ref|ref|autoref|eqref)\s*\{([^}]+)\}")


def compute_dependencies(records: list[EnvRecord],
                         label_map: dict[str, str],
                         name_map: dict[tuple[str, str], str]) -> dict[str, list[str]]:
    deps: dict[str, list[str]] = {}
    for rec in records:
        found: list[str] = []

        def add(cid: str | None) -> None:
            if cid and cid != rec.id and cid not in found:
                found.append(cid)

        if rec.parent:
            add(rec.parent)
        # merge explicit-\ref and natural-language hits in first-appearance order
        hits: list[tuple[int, str | None]] = []
        for m in _REF_RE.finditer(rec.latex):
            for label in m.group(1).split(","):
                hits.append((m.start(), label_map.get(label.strip())))
        for m in _NL_TARGET_RE.finditer(rec.latex):
            hits.append((m.start(), name_map.get((m.group(1).lower(), m.group(2)))))
        for _, cid in sorted(hits, key=lambda h: h[0]):
            add(cid)
        deps[rec.id] = found
    return deps
