"""Lexical retrieval baseline: a self-contained BM25 index (pure Python).

This is the Sprint 3 baseline. It requires no external service and no paid API.
Vector/hybrid retrieval is a documented Sprint-3+ extension (needs a local
embedding model, e.g. via Ollama) — we do NOT claim its superiority without a
benchmark, so BM25 is the honest default.

Every retrieval result carries the fragment's provenance (document + location),
so no answer can be produced without citable provenance.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from .documents import SourceFragment

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "of", "to", "and", "in", "is", "are", "for", "on", "with",
    "as", "by", "that", "this", "it", "be", "at", "or", "from", "we", "can",
    "el", "la", "los", "las", "de", "y", "en", "es", "un", "una", "que", "con",
}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOP and len(t) > 1]


@dataclass
class RetrievalHit:
    fragment: SourceFragment
    score: float
    provenance: dict[str, object] = field(default_factory=dict)


class BM25Index:
    """Okapi BM25. k1 and b are standard defaults."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._frags: list[SourceFragment] = []
        self._docs_tokens: list[list[str]] = []
        self._df: Counter[str] = Counter()
        self._avgdl: float = 0.0
        self._built = False

    def add(self, fragment: SourceFragment) -> None:
        toks = tokenize(fragment.text)
        self._frags.append(fragment)
        self._docs_tokens.append(toks)
        for term in set(toks):
            self._df[term] += 1
        self._built = False

    def add_many(self, fragments: list[SourceFragment]) -> None:
        for f in fragments:
            self.add(f)
        self.build()

    def build(self) -> None:
        total = sum(len(t) for t in self._docs_tokens)
        self._avgdl = (total / len(self._docs_tokens)) if self._docs_tokens else 0.0
        self._built = True

    @property
    def size(self) -> int:
        return len(self._frags)

    def _idf(self, term: str) -> float:
        n = len(self._frags)
        df = self._df.get(term, 0)
        # BM25 idf with +1 to stay non-negative.
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int = 5) -> list[RetrievalHit]:
        if not self._built:
            self.build()
        if not self._frags:
            return []
        q_terms = tokenize(query)
        scored: list[RetrievalHit] = []
        for frag, toks in zip(self._frags, self._docs_tokens, strict=True):
            if not toks:
                continue
            tf = Counter(toks)
            dl = len(toks)
            score = 0.0
            for term in q_terms:
                if term not in tf:
                    continue
                idf = self._idf(term)
                freq = tf[term]
                denom = freq + self.k1 * (1 - self.b + self.b * dl / (self._avgdl or 1))
                score += idf * (freq * (self.k1 + 1)) / denom
            if score > 0:
                scored.append(
                    RetrievalHit(
                        fragment=frag,
                        score=round(score, 6),
                        provenance={
                            "document_id": frag.document_id,
                            "fragment_id": frag.id,
                            "section": frag.section,
                            "char_span": [frag.char_start, frag.char_end],
                            "hash": frag.hash,
                            "parser": frag.parser,
                        },
                    )
                )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:top_k]
