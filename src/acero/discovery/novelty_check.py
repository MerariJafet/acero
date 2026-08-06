"""Novelty check — the anti-"Erdősgate" gate.

In Oct 2025 an AI lab announced that GPT-5 "solved 10 unsolved Erdős problems".
It hadn't: it ran a large literature search and found ALREADY-PUBLISHED solutions
(some 20+ years old) to problems a website merely *labeled* "open". The website's
own maintainer called it "a dramatic misrepresentation". The root error: treating
a weak "open" label as proof of novelty, and calling a *recovery* a *discovery*.

This module is ACERO's antidote. BEFORE spending compute on a claim, it searches
real literature and asks: is this already resolved somewhere? It returns a novelty
verdict + a RECOVERY RISK, so the loop can skip already-solved work and — just as
important — never dress up a literature find as a new discovery.

Design honesty:
  * A "not found" is NOT proof of novelty (absence of evidence). We say `likely_open`
    with explicit caveats, never `novel`.
  * A found paper that resolves the claim → `already_resolved`, high recovery risk.
  * If we couldn't search (no network / no results) → `uncertain`, never a green light.
Both the literature searcher and the judging LLM are injectable for offline tests.
"""

from __future__ import annotations

import os
from typing import Any

VERDICTS = ("already_resolved", "likely_open", "uncertain")


def openalex_search(query: str, k: int = 6) -> list[dict[str, Any]]:
    """Default searcher: OpenAlex (free, no key). Best-effort; [] on any failure."""
    try:
        import httpx
        r = httpx.get("https://api.openalex.org/works",
                      params={"search": query, "per_page": k,
                              "mailto": os.environ.get("ACERO_CONTACT_EMAIL", "acero@local")},
                      timeout=float(os.environ.get("ACERO_NOVELTY_TIMEOUT", "10")))
        r.raise_for_status()
        out = []
        for w in (r.json().get("results") or [])[:k]:
            out.append({
                "title": w.get("title") or "",
                "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                "year": w.get("publication_year"),
                "abstract": _reconstruct_abstract(w.get("abstract_inverted_index")),
                "url": (w.get("primary_location") or {}).get("landing_page_url") or w.get("id"),
            })
        return out
    except Exception:  # noqa: BLE001 - offline / API down → no results, honest uncertainty
        return []


def _reconstruct_abstract(inv: dict[str, list[int]] | None) -> str:
    if not inv:
        return ""
    positions: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))[:600]


_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string"},          # already_resolved|likely_open|uncertain
        "recovery_risk": {"type": "number"},     # 0..1: prob. this is a known result
        "resolving_papers": {"type": "array", "items": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "doi": {"type": "string"},
                           "why": {"type": "string"}},
            "required": ["title", "doi", "why"], "additionalProperties": False}},
        "rationale": {"type": "string"},
        "recommendation": {"type": "string"},
    },
    "required": ["verdict", "recovery_risk", "resolving_papers", "rationale",
                 "recommendation"],
    "additionalProperties": False,
}

_JUDGE_SYS = (
    "Eres el CHECADOR DE NOVEDAD de ACERO. Te doy una AFIRMACIÓN científica y una lista "
    "de PAPERS reales encontrados en la literatura. Decide HONESTAMENTE si la afirmación "
    "ya está RESUELTA/publicada. Reglas: (1) 'ya resuelto' SOLO si un paper concreto "
    "responde la afirmación (cítalo en resolving_papers con por qué); recovery_risk alto. "
    "(2) Si nada la resuelve, verdict='likely_open' pero recuerda que NO encontrar no "
    "prueba novedad — recovery_risk moderado y recomienda buscar más. (3) Si los papers "
    "no bastan para juzgar, 'uncertain'. NUNCA declares 'novedoso'; el techo es "
    "'probablemente abierto'. Da una recomendación accionable (correr / no correr / "
    "reformular / buscar en otra base)."
)


class NoveltyChecker:
    """searcher(query,k)->hits and provider are injectable for tests."""

    def __init__(self, provider: Any = None, searcher: Any = None) -> None:
        self._provider = provider
        self._searcher = searcher or openalex_search

    def _prov(self) -> Any:
        if self._provider is not None:
            return self._provider
        from ..llm.providers import CodexCliProvider
        return CodexCliProvider(timeout_sec=120)

    def check(self, claim: str, *, query: str | None = None, k: int = 6) -> dict[str, Any]:
        hits = self._searcher(query or claim, k) or []
        if not hits:
            return {"verdict": "uncertain", "recovery_risk": 0.5,
                    "resolving_papers": [], "hits": [],
                    "rationale": "no se pudo buscar literatura (sin red/o sin resultados)",
                    "recommendation": "reintentar la búsqueda o buscar en otra base "
                                      "antes de afirmar novedad", "searched": False}
        prov = self._prov()
        if prov is None or not getattr(prov, "available", lambda: False)():
            # no judge: report the raw hits, stay uncertain (never green-light novelty)
            return {"verdict": "uncertain", "recovery_risk": 0.5,
                    "resolving_papers": [], "hits": hits,
                    "rationale": f"{len(hits)} papers hallados pero sin IA para juzgar",
                    "recommendation": "revisa los papers manualmente", "searched": True}
        lit = "\n".join(f"- {h['title']} ({h.get('year')}, doi:{h.get('doi') or '—'}): "
                        f"{(h.get('abstract') or '')[:280]}" for h in hits)
        prompt = (f"{_JUDGE_SYS}\n\nAFIRMACIÓN: {claim}\n\nPAPERS ENCONTRADOS:\n{lit}\n\n"
                  "Devuelve el juicio.")
        try:
            out = prov.complete_json(prompt, _JUDGE_SCHEMA, temperature=0.1)
            v = str(out.get("verdict") or "uncertain")
            return {"verdict": v if v in VERDICTS else "uncertain",
                    "recovery_risk": float(out.get("recovery_risk") or 0.5),
                    "resolving_papers": (out.get("resolving_papers") or [])[:5],
                    "rationale": str(out.get("rationale") or "")[:500],
                    "recommendation": str(out.get("recommendation") or "")[:300],
                    "hits": hits, "searched": True}
        except Exception:  # noqa: BLE001
            return {"verdict": "uncertain", "recovery_risk": 0.5,
                    "resolving_papers": [], "hits": hits,
                    "rationale": "el juez falló", "recommendation": "revisión manual",
                    "searched": True}
