"""Novelty check — Hipatia, ACERO's librarian and the anti-"Erdősgate" gate.

In Oct 2025 an AI lab announced that GPT-5 "solved 10 unsolved Erdős problems". It
hadn't: it ran a large literature search and found ALREADY-PUBLISHED solutions (some 20+
years old) to problems a website merely *labeled* "open". The root error: treating a weak
"open" label as proof of novelty, and calling a *recovery* a *discovery*.

Hipatia is the antidote. BEFORE spending compute on a claim she asks: is this already
resolved somewhere? A weak version (one keyword search of the raw sentence, one source)
almost always answered "uncertain" — useless. This version searches like an expert:

  1. QUERY CRAFT: an LLM turns the claim into several CONCISE scholarly queries (canonical
     object/theorem names, synonyms) — never the raw sentence.
  2. MULTI-SOURCE: OpenAlex + arXiv + Crossref (all free), run in parallel, deduped.
  3. JUDGE: an LLM reads the real hits and classifies — resolves / related / unrelated —
     giving a verdict + confidence + the resolving papers.

Design honesty (unchanged):
  * "not found" is NOT proof of novelty → ceiling is `likely_open`, never `novel`.
  * a paper that resolves the claim → `already_resolved`, high recovery risk.
  * genuine no coverage (search failed) → `uncertain`, never a green light.
Searcher, query-generator and judge are all injectable for offline tests.
"""

from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

VERDICTS = ("already_resolved", "likely_open", "uncertain")
_UA = {"User-Agent": "ACERO-novelty/1.0 (mailto:acero@local)"}
_WORD = re.compile(r"[a-z0-9]+")


def _timeout() -> float:
    return float(os.environ.get("ACERO_NOVELTY_TIMEOUT", "10"))


def _reconstruct_abstract(inv: dict[str, list[int]] | None) -> str:
    if not inv:
        return ""
    positions: dict[int, str] = {}
    for word, idxs in inv.items():
        for i in idxs:
            positions[i] = word
    return " ".join(positions[i] for i in sorted(positions))[:600]


# --- individual sources (each best-effort, [] on any failure) --------------------
def openalex_search(query: str, k: int = 6) -> list[dict[str, Any]]:
    try:
        import httpx
        r = httpx.get("https://api.openalex.org/works",
                      params={"search": query, "per_page": k,
                              "mailto": os.environ.get("ACERO_CONTACT_EMAIL", "acero@local")},
                      timeout=_timeout())
        r.raise_for_status()
        out = []
        for w in (r.json().get("results") or [])[:k]:
            out.append({"title": w.get("title") or "",
                        "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                        "year": w.get("publication_year"),
                        "abstract": _reconstruct_abstract(w.get("abstract_inverted_index")),
                        "url": (w.get("primary_location") or {}).get("landing_page_url")
                        or w.get("id"), "source": "openalex"})
        return out
    except Exception:  # noqa: BLE001
        return []


def arxiv_search(query: str, k: int = 6) -> list[dict[str, Any]]:
    try:
        import xml.etree.ElementTree as ET

        import httpx
        r = httpx.get("http://export.arxiv.org/api/query",
                      params={"search_query": f"all:{query}", "max_results": k},
                      headers=_UA, timeout=_timeout())
        r.raise_for_status()
        ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        out = []
        for e in ET.fromstring(r.text).findall("a:entry", ns)[:k]:
            title = (e.findtext("a:title", "", ns) or "").strip()
            summ = (e.findtext("a:summary", "", ns) or "").strip()
            pub = (e.findtext("a:published", "", ns) or "")[:4]
            doi = e.findtext("arxiv:doi", "", ns) or ""
            out.append({"title": title, "doi": doi,
                        "year": int(pub) if pub.isdigit() else None,
                        "abstract": summ[:600],
                        "url": e.findtext("a:id", "", ns), "source": "arxiv"})
        return out
    except Exception:  # noqa: BLE001
        return []


def crossref_search(query: str, k: int = 6) -> list[dict[str, Any]]:
    try:
        import httpx
        r = httpx.get("https://api.crossref.org/works",
                      params={"query": query, "rows": k,
                              "select": "title,DOI,abstract,issued"},
                      headers=_UA, timeout=_timeout())
        r.raise_for_status()
        out = []
        for it in (r.json().get("message", {}).get("items") or [])[:k]:
            title = (it.get("title") or [""])[0]
            yr = ((it.get("issued") or {}).get("date-parts") or [[None]])[0][0]
            abstract = re.sub(r"<[^>]+>", "", it.get("abstract") or "")[:600]
            out.append({"title": title, "doi": it.get("DOI") or "",
                        "year": yr, "abstract": abstract,
                        "url": f"https://doi.org/{it.get('DOI')}" if it.get("DOI") else "",
                        "source": "crossref"})
        return out
    except Exception:  # noqa: BLE001
        return []


def multi_source_search(query: str, k: int = 6) -> list[dict[str, Any]]:
    """Default searcher: OpenAlex + arXiv + Crossref in parallel, merged."""
    sources = (openalex_search, arxiv_search, crossref_search)
    hits: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futs = [pool.submit(s, query, k) for s in sources]
        for f in as_completed(futs):
            try:
                hits.extend(f.result() or [])
            except Exception:  # noqa: BLE001
                continue
    return hits


def _key(h: dict[str, Any]) -> str:
    doi = (h.get("doi") or "").strip().lower()
    if doi:
        return "doi:" + doi
    return "t:" + " ".join(_WORD.findall((h.get("title") or "").lower()))


# --- LLM helpers -----------------------------------------------------------------
QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "queries": {"type": "array", "items": {"type": "string"}},
        "key_terms": {"type": "array", "items": {"type": "string"}},
        "canonical_claim": {"type": "string"},
    },
    "required": ["queries", "key_terms", "canonical_claim"], "additionalProperties": False,
}

_QGEN_SYS = (
    "Eres HIPATIA, la bibliotecaria de ACERO. Convierte esta AFIRMACIÓN en 3-5 CONSULTAS "
    "de búsqueda académica CONCISAS (5-8 palabras): usa los nombres técnicos canónicos de "
    "los objetos/teoremas, sinónimos y variantes con que un experto buscaría si esto YA se "
    "hizo. NO uses la frase completa ni rangos numéricos concretos (p.ej. '6<=n<=14'). "
    "Piensa en el concepto general. Da también key_terms y una reformulación canónica breve."
)

_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string"},
        "recovery_risk": {"type": "number"},
        "confidence": {"type": "number"},
        "resolving_papers": {"type": "array", "items": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "doi": {"type": "string"},
                           "why": {"type": "string"}},
            "required": ["title", "doi", "why"], "additionalProperties": False}},
        "related_papers": {"type": "array", "items": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "doi": {"type": "string"},
                           "why": {"type": "string"}},
            "required": ["title", "doi", "why"], "additionalProperties": False}},
        "rationale": {"type": "string"},
        "recommendation": {"type": "string"},
    },
    "required": ["verdict", "recovery_risk", "confidence", "resolving_papers",
                 "related_papers", "rationale", "recommendation"],
    "additionalProperties": False,
}

_JUDGE_SYS = (
    "Eres HIPATIA juzgando NOVEDAD en ACERO. Te doy una AFIRMACIÓN y PAPERS reales (con su "
    "fuente). Clasifica honestamente: (1) verdict='already_resolved' SOLO si algún paper "
    "RESUELVE o ENUNCIA la afirmación — ponlo en resolving_papers con el porqué; "
    "recovery_risk alto. (2) Si hay papers claramente RELACIONADOS pero ninguno la "
    "resuelve, verdict='likely_open' (los relacionados van en related_papers); recuerda "
    "que NO encontrar no prueba novedad. (3) Reserva 'uncertain' SOLO si de verdad no hay "
    "señal utilizable. Con una búsqueda amplia multi-fuente, PREFIERE decidir entre "
    "'already_resolved' y 'likely_open'. NUNCA declares 'novedoso'; el techo es "
    "'probablemente abierto'. Da confidence (0..1) y una recomendación accionable."
)


class NoveltyChecker:
    """searcher(query,k)->hits, provider and query_gen are injectable for tests."""

    def __init__(self, provider: Any = None, searcher: Any = None,
                 query_gen: Any = None) -> None:
        self._provider = provider
        self._searcher = searcher or multi_source_search
        self._query_gen = query_gen

    def _prov(self) -> Any:
        if self._provider is not None:
            return self._provider
        from ..llm.providers import CodexCliProvider
        # Let it THINK. A short cap here (the old 120s) cut Codex off mid-reasoning; the
        # Codex→Claude fallback is built in. Patient but bounded so Codex+Claude ≤ ~40 min.
        secs = int(os.environ.get("ACERO_NOVELTY_LLM_TIMEOUT", "1200"))
        return CodexCliProvider(timeout_sec=secs)

    def _available(self, prov: Any) -> bool:
        return prov is not None and getattr(prov, "available", lambda: False)()

    def _json(self, prov: Any, prompt: str, schema: dict[str, Any],
              temperature: float, tries: int = 1) -> dict[str, Any] | None:
        """One PATIENT structured call (the provider already retries Codex→Claude on
        failure). We don't add outer retries that would double a long, legitimate think."""
        for _ in range(max(1, tries)):
            try:
                out = prov.complete_json(prompt, schema, temperature=temperature)
                if isinstance(out, dict):
                    return out
            except Exception:  # noqa: BLE001
                continue
        return None

    # --- craft several scholarly queries from the claim -----------------------
    def _gen_queries(self, claim: str) -> list[str]:
        if self._query_gen is not None:
            return list(self._query_gen(claim) or [])[:5] or [claim]
        prov = self._prov()
        if not self._available(prov):
            return [claim]
        out = self._json(prov, f"{_QGEN_SYS}\n\nAFIRMACIÓN: {claim}", QUERY_SCHEMA, 0.3)
        if not out:
            return [claim]
        qs = [q for q in (out.get("queries") or []) if isinstance(q, str) and q.strip()]
        return qs[:5] or [claim]

    # --- run every query across sources, dedup --------------------------------
    def _search_all(self, queries: list[str], k: int) -> list[dict[str, Any]]:
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        with ThreadPoolExecutor(max_workers=min(4, max(1, len(queries)))) as pool:
            futs = [pool.submit(self._searcher, q, k) for q in queries]
            for f in as_completed(futs):
                try:
                    for h in (f.result() or []):
                        kk = _key(h)
                        if kk not in seen:
                            seen.add(kk)
                            merged.append(h)
                except Exception:  # noqa: BLE001
                    continue
        return merged[:14]

    def check(self, claim: str, *, query: str | None = None, k: int = 6) -> dict[str, Any]:
        queries = [query] if query else self._gen_queries(claim)
        hits = self._search_all(queries, k)
        sources = sorted({str(h["source"]) for h in hits if h.get("source")})
        if not hits:
            return {"verdict": "uncertain", "recovery_risk": 0.5, "confidence": 0.2,
                    "resolving_papers": [], "related_papers": [], "hits": [],
                    "queries": queries, "sources": sources,
                    "rationale": "no se hallaron resultados en ninguna fuente",
                    "recommendation": "reintentar con otros términos antes de afirmar novedad",
                    "searched": False}
        prov = self._prov()
        if not self._available(prov):
            return {"verdict": "uncertain", "recovery_risk": 0.5, "confidence": 0.3,
                    "resolving_papers": [], "related_papers": [], "hits": hits,
                    "queries": queries, "sources": sources,
                    "rationale": f"{len(hits)} papers hallados pero sin IA para juzgar",
                    "recommendation": "revisa los papers manualmente", "searched": True}
        lit = "\n".join(f"- [{h.get('source')}] {h['title']} ({h.get('year')}, "
                        f"doi:{h.get('doi') or '—'}): {(h.get('abstract') or '')[:260]}"
                        for h in hits)
        prompt = f"{_JUDGE_SYS}\n\nAFIRMACIÓN: {claim}\n\nPAPERS ({len(hits)}):\n{lit}"
        out = self._json(prov, prompt, _JUDGE_SCHEMA, 0.1)
        if not out:
            return {"verdict": "uncertain", "recovery_risk": 0.5, "confidence": 0.3,
                    "resolving_papers": [], "related_papers": [], "hits": hits,
                    "queries": queries, "sources": sources,
                    "rationale": "el juez no respondió (timeout de IA); búsqueda OK, "
                                 "reintentar el juicio", "recommendation": "reintentar",
                    "searched": True}
        resolving = (out.get("resolving_papers") or [])[:5]
        v = str(out.get("verdict") or "uncertain")
        v = v if v in VERDICTS else "uncertain"
        if resolving:                       # a concrete resolver is decisive
            v = "already_resolved"
        return {"verdict": v,
                "recovery_risk": float(out.get("recovery_risk") or 0.5),
                "confidence": float(out.get("confidence") or 0.5),
                "resolving_papers": resolving,
                "related_papers": (out.get("related_papers") or [])[:5],
                "rationale": str(out.get("rationale") or "")[:500],
                "recommendation": str(out.get("recommendation") or "")[:300],
                "hits": hits, "queries": queries, "sources": sources, "searched": True}
