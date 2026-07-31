"""index.json persistence: atomic writes, content hashing, id generation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path


def content_hash(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_index(index_file: Path) -> dict:
    if not index_file.is_file():
        return {}
    with open(index_file, encoding="utf-8") as f:
        return json.load(f)


def save_index(index_file: Path, index: dict) -> None:
    """Atomic write: temp file in the same directory, then os.replace."""
    index_file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=index_file.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False, sort_keys=True)
            f.write("\n")
        os.replace(tmp, index_file)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def make_paper_id(title: str, year: int | None = None, fallback: str = "paper") -> str:
    words = re.sub(r"[^a-z0-9 ]+", " ", title.lower()).split()
    stop = {"a", "an", "the", "of", "on", "in", "with", "and", "for", "to", "toy"}
    words = [w for w in words if w not in stop][:4]
    base = "_".join(words) or fallback
    return f"{base}_{year}" if year else base
