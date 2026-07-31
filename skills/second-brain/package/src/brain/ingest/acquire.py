"""Source acquisition: resolve an arXiv id / URL / local path to a local input,
preferring the cleanest tier (LaTeX source > HTML > PDF)."""

from __future__ import annotations

import io
import re
import tarfile
from pathlib import Path

ARXIV_ID_RE = re.compile(r"^(?:arxiv:)?(\d{4}\.\d{4,5})(v\d+)?$", re.IGNORECASE)


def looks_like_arxiv_id(spec: str) -> bool:
    return bool(ARXIV_ID_RE.match(spec.strip()))


def fetch_arxiv_source(arxiv_id: str, dest_root: Path) -> Path:
    """Download the arXiv e-print tarball (Tier 0) and unpack it.
    Returns the directory containing the LaTeX source."""
    import requests  # lazy: only needed for network acquisition

    m = ARXIV_ID_RE.match(arxiv_id.strip())
    if not m:
        raise ValueError(f"not an arXiv id: {arxiv_id!r}")
    clean = m.group(1) + (m.group(2) or "")
    out_dir = dest_root / f"arxiv_{clean.replace('.', '_')}"
    if out_dir.is_dir() and any(out_dir.iterdir()):
        return out_dir  # already fetched

    url = f"https://arxiv.org/e-print/{clean}"
    resp = requests.get(url, timeout=60,
                        headers={"User-Agent": "second-brain/0.1 (personal library)"})
    resp.raise_for_status()
    out_dir.mkdir(parents=True, exist_ok=True)
    data = resp.content
    try:
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            tf.extractall(out_dir, filter="data")
    except tarfile.ReadError:
        # single-file submissions arrive as a bare (possibly gzipped) .tex
        import gzip
        try:
            data = gzip.decompress(data)
        except OSError:
            pass
        (out_dir / "main.tex").write_bytes(data)
    return out_dir


def resolve_source(spec: str, papers_dir: Path) -> Path:
    """Turn a user-supplied spec (path, arXiv id, or URL) into a local path."""
    p = Path(spec).expanduser()
    if p.exists():
        return p
    if looks_like_arxiv_id(spec):
        return fetch_arxiv_source(spec, papers_dir)
    if spec.startswith(("http://", "https://")):
        arxiv = re.search(r"arxiv\.org/(?:abs|pdf|e-print)/(\d{4}\.\d{4,5})", spec)
        if arxiv:
            return fetch_arxiv_source(arxiv.group(1), papers_dir)
        import requests
        resp = requests.get(spec, timeout=60)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        suffix = ".pdf" if "pdf" in ctype else ".html"
        name = re.sub(r"[^a-zA-Z0-9]+", "_", spec.split("/")[-1])[:60] or "download"
        dest = papers_dir / f"{name}{suffix}"
        dest.write_bytes(resp.content)
        return dest
    raise FileNotFoundError(f"cannot resolve source: {spec!r}")
