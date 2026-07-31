"""Hybrid search over index *metadata* (never full text).

Rankers:
  - BM25 (rank-bm25) — always on, zero external services.
  - Optional dense retrieval (sentence-transformers) over the same metadata
    strings — enabled via [search].use_dense and the [dense] extra.
Rankings are fused with Reciprocal Rank Fusion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# BM25Plus, not BM25Okapi: Okapi's IDF term is log((N-df+0.5)/(df+0.5)), which is
# exactly 0 for a term appearing in 1 of 2 docs — a tiny personal library would
# score everything 0. BM25Plus keeps IDF strictly positive at any corpus size.
from rank_bm25 import BM25Plus

from ..config import Config

_RRF_K = 60


@dataclass
class SearchHit:
    paper_id: str
    title: str
    score: float
    year: int | None
    needs_review: bool
    available_sections: list[str] = field(default_factory=list)
    env_chunks: list[str] = field(default_factory=list)
    key_theorems: list[str] = field(default_factory=list)


def _doc_for(entry: dict) -> str:
    parts = [
        entry.get("title", ""),
        " ".join(entry.get("authors", [])),
        entry.get("abstract", ""),
        " ".join(entry.get("keywords", [])),
        " ".join(entry.get("proof_techniques", [])),
        " ".join(entry.get("key_theorems", [])),
        " ".join(entry.get("available_sections", [])),
    ]
    return "\n".join(p for p in parts if p)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class Searcher:
    def __init__(self, cfg: Config, index: dict):
        self.cfg = cfg
        self.index = index
        self.paper_ids = sorted(index.keys())
        self.docs = [_doc_for(index[pid]) for pid in self.paper_ids]
        corpus = [_tokenize(d) for d in self.docs]
        self._bm25 = BM25Plus(corpus) if corpus else None
        self._dense = None
        if cfg.search.use_dense and self.docs:
            self._dense = self._try_build_dense()

    def _try_build_dense(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return None
        model = SentenceTransformer("all-MiniLM-L6-v2")
        vectors = model.encode(self.docs, normalize_embeddings=True)
        return (model, vectors)

    def _rank_bm25(self, query: str) -> list[int]:
        scores = self._bm25.get_scores(_tokenize(query))
        return sorted(range(len(scores)), key=lambda i: -scores[i])

    def _rank_dense(self, query: str) -> list[int] | None:
        if self._dense is None:
            return None
        model, vectors = self._dense
        q = model.encode([query], normalize_embeddings=True)[0]
        sims = vectors @ q
        return sorted(range(len(sims)), key=lambda i: -sims[i])

    def search(self, query: str, top_k: int | None = None) -> list[SearchHit]:
        if not self.paper_ids or not query.strip():
            return []
        top_k = top_k or self.cfg.search.top_k
        rankings = [self._rank_bm25(query)]
        dense = self._rank_dense(query)
        if dense is not None:
            rankings.append(dense)

        fused: dict[int, float] = {}
        for ranking in rankings:
            for rank, doc_i in enumerate(ranking):
                fused[doc_i] = fused.get(doc_i, 0.0) + 1.0 / (_RRF_K + rank + 1)

        ordered = sorted(fused, key=lambda i: -fused[i])[:top_k]
        hits = []
        for i in ordered:
            pid = self.paper_ids[i]
            entry = self.index[pid]
            env_chunks = [cid for cid, c in entry.get("chunks", {}).items()
                          if c.get("type") != "section"]
            hits.append(SearchHit(
                paper_id=pid,
                title=entry.get("title", pid),
                score=round(fused[i], 5),
                year=entry.get("year"),
                needs_review=entry.get("extraction", {}).get("needs_review", False),
                available_sections=entry.get("available_sections", []),
                env_chunks=env_chunks,
                key_theorems=entry.get("key_theorems", []),
            ))
        return hits
