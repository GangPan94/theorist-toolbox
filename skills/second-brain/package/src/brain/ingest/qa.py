"""Extraction QA gate. Every ingestion produces a report; low scores mark the
paper `needs_review` so downstream consumers know the text is untrusted."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

NEEDS_REVIEW_THRESHOLD = 0.7


@dataclass
class QAReport:
    tier: int
    score: float
    needs_review: bool
    checks: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _unescaped_dollar_count(text: str) -> int:
    count = 0
    i = 0
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "$":
            count += 1
        i += 1
    return count


def _garbage_ratio(text: str) -> float:
    if not text:
        return 1.0
    bad = text.count("�")
    bad += sum(1 for ch in text if ord(ch) < 32 and ch not in "\n\t\r")
    return bad / len(text)


def evaluate(markdown: str, *, tier: int, n_sections: int, n_envs: int,
             pipeline_warnings: list[str] | None = None) -> QAReport:
    warnings = list(pipeline_warnings or [])
    checks: dict = {}

    dollars = _unescaped_dollar_count(markdown)
    checks["math_dollars_balanced"] = (dollars % 2 == 0)
    checks["display_math_balanced"] = (markdown.count("\\[") == markdown.count("\\]"))
    begins = len(re.findall(r"\\begin\s*\{", markdown))
    ends = len(re.findall(r"\\end\s*\{", markdown))
    checks["env_begin_end_balanced"] = (begins == ends)
    gr = _garbage_ratio(markdown)
    checks["garbage_ratio"] = round(gr, 5)
    checks["n_sections"] = n_sections
    checks["n_environments"] = n_envs

    score = 1.0
    if not checks["math_dollars_balanced"]:
        score -= 0.3
        warnings.append("odd number of unescaped $ delimiters")
    if not checks["display_math_balanced"]:
        score -= 0.2
        warnings.append("unbalanced \\[ \\] display math")
    if not checks["env_begin_end_balanced"]:
        score -= 0.3
        warnings.append(f"\\begin/\\end imbalance ({begins} vs {ends})")
    score -= min(0.4, gr * 20)
    if n_sections == 0:
        score -= 0.2
        warnings.append("no sections detected")
    if tier == 2:
        score -= 0.1  # OCR output is never fully trusted
    score = max(0.0, min(1.0, round(score, 3)))

    return QAReport(tier=tier, score=score,
                    needs_review=score < NEEDS_REVIEW_THRESHOLD,
                    checks=checks, warnings=warnings)
