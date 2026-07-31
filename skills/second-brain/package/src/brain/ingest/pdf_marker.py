"""Tier 2 (last resort): PDF → Markdown via Marker OCR.

Heavy optional dependency; install with `pip install -e ".[ocr]"`. Output is
never fully trusted — the QA gate applies a tier penalty and typically flags
these papers `needs_review`.
"""

from __future__ import annotations

import re
from pathlib import Path

from .latex_source import NormalizedPaper


def normalize_pdf(path: Path) -> NormalizedPaper:
    try:
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.output import text_from_rendered
    except ImportError as exc:
        raise RuntimeError(
            "Tier-2 PDF ingestion needs Marker. Install it with:\n"
            '    pip install -e ".[ocr]"\n'
            "or provide the paper's LaTeX source / arXiv id instead (preferred)."
        ) from exc

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(str(path))
    text, _, _ = text_from_rendered(rendered)

    lines = text.split("\n")
    title = next((re.sub(r"^#+\s*", "", ln).strip() for ln in lines
                  if ln.strip().startswith("#")), path.stem)
    # Demote the title heading; promote every other heading level to start at h2.
    markdown = f"# {title}\n\n" + "\n".join(
        ln for ln in lines if re.sub(r"^#+\s*", "", ln).strip() != title)
    if "\n## " not in markdown:
        markdown = re.sub(r"^### ", "## ", markdown, flags=re.MULTILINE)

    return NormalizedPaper(title=title, authors=[], year=None, abstract="",
                           markdown=markdown, macros=[], macro_names=[],
                           env_records=[], warnings=["tier-2 Marker OCR output"])
