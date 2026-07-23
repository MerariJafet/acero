"""Semantic index over the project's literature (embeddings).

Turns every indexed paper (abstract + full-text excerpt) into a vector with a
local sentence-transformer, so you can SEARCH your accumulated literature by
meaning, not just keywords — the "make the vault searchable" ask. The model is
lazy-loaded once and cached; if it cannot load (offline/no weights), we fall
back to a transparent keyword score so search still works and never crashes.

The index is rebuilt from the ledger on demand (the ledger is the source of
truth); vectors are cached in memory per process.
"""

from __future__ import annotations

import math
import os
import re
import threading
from typing import Any

from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

_MODEL: Any = None
_MODEL_TRIED = False
_LOCK = threading.Lock()
_CACHE: dict[str, dict[str, Any]] = {}     # project_id → {sig, vecs, docs, backend}


def _load_model() -> Any:
    global _MODEL, _MODEL_TRIED
    with _LOCK:
        if _MODEL_TRIED:
            return _MODEL
        _MODEL_TRIED = True
        if os.environ.get("ACERO_EMBEDDINGS_DISABLED") == "1":
            return None
        try:
            from sentence_transformers import SentenceTransformer
            _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:  # noqa: BLE001 - degrade to keyword search
            _MODEL = None
        return _MODEL


def _doc_text(p: dict[str, Any]) -> str:
    return " ".join(filter(None, [
        p.get("title", ""), " ".join(p.get("topics", []) or []),
        p.get("abstract", ""), p.get("fulltext_excerpt", "")]))[:4000]


def _tokens(s: str) -> list[str]:
    return re.findall(r"[a-záéíóúñ0-9]{3,}", (s or "").lower())


def build_index(project_id: str, session_factory: Any | None = None,
                *, force: bool = False) -> dict[str, Any]:
    sf = session_factory or default_session_factory()
    store = DiscoveryStore(sf, ResearchLedger(sf))
    lits = [p for p in store.list_objects(project_id, kind="literature")
            if p.get("title")]
    sig = str(len(lits)) + ":" + ",".join(sorted(p.get("id", "") for p in lits))[:200]
    cached = _CACHE.get(project_id)
    if cached and cached["sig"] == sig and not force:
        return cached
    docs = [{"id": p.get("id"), "title": p.get("title", ""),
             "doi": p.get("doi", ""), "url": p.get("url", ""),
             "source": p.get("source", ""), "hyp_id": p.get("hyp_id", ""),
             "has_fulltext": bool(p.get("fulltext_excerpt")),
             "text": _doc_text(p)} for p in lits]
    model = _load_model()
    backend = "embeddings" if model is not None else "keyword"
    vecs = None
    if model is not None and docs:
        vecs = model.encode([d["text"] for d in docs], normalize_embeddings=True)
    entry = {"sig": sig, "docs": docs, "vecs": vecs, "backend": backend}
    _CACHE[project_id] = entry
    return entry


def search(project_id: str, query: str, *, k: int = 8,
           session_factory: Any | None = None) -> dict[str, Any]:
    idx = build_index(project_id, session_factory)
    docs = idx["docs"]
    if not docs:
        return {"backend": idx["backend"], "results": [],
                "note": "aún no hay literatura indexada"}
    if idx["vecs"] is not None:
        model = _load_model()
        qv = model.encode([query], normalize_embeddings=True)[0]
        scores = [float(sum(a * b for a, b in zip(qv, dv, strict=False)))
                  for dv in idx["vecs"]]
    else:
        qt = set(_tokens(query))
        scores = []
        for d in docs:
            dt = _tokens(d["text"])
            if not dt or not qt:
                scores.append(0.0)
                continue
            hits = sum(1 for t in dt if t in qt)
            scores.append(hits / math.sqrt(len(dt)))
    order = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:k]
    results = [{**{kk: docs[i][kk] for kk in
                   ("id", "title", "doi", "url", "source", "hyp_id", "has_fulltext")},
                "score": round(scores[i], 4)} for i in order if scores[i] > 0]
    return {"backend": idx["backend"], "results": results,
            "n_indexed": len(docs)}
