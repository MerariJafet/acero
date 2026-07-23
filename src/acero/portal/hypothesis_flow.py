"""Hypothesis-centric research flow: approve → literature (confront) → experiments.

Once a hypothesis is APPROVED, the next stages run PER HYPOTHESIS:
  - literature: a real Crossref search seeded by the hypothesis, then a Codex
    confrontation that argues for/against and proposes an IMPROVED hypothesis,
    citing only the REAL papers found (by index — never invented DOIs).
  - experiments: Codex proposes concrete experiments (what/how/data/controls).
    Running one executes a REAL analysis when ACERO has the code (Kepler, Hubble);
    otherwise it produces a reproducible EXECUTION PLAN marked PLANNED (pending real
    data) — it never fabricates a result.

Everything is a candidate to test; nothing is a discovery.
"""

from __future__ import annotations

import os
from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger
from ..provenance.events import ProvenanceAction

CONFRONT_SCHEMA = {
    "type": "object",
    "properties": {
        "stance": {"type": "string"},                  # supports|challenges|mixed
        "argument_for": {"type": "string"},
        "argument_against": {"type": "string"},
        "improved_hypothesis": {"type": "string"},
        "citation_idx": {"type": "array", "items": {"type": "integer"}},
        "experiment_ideas": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "approach": {"type": "string"},      # qué haríamos, breve
                "data_source": {"type": "string"},   # dataset público real, o teórico
                "method_type": {"type": "string"},   # download_data|math_analysis|
                                                     # theoretical|simulation
                "feasible_local": {"type": "boolean"},  # ¿corre en nuestra máquina?
            },
            "required": ["title", "approach", "data_source", "method_type",
                         "feasible_local"],
            "additionalProperties": False}},
    },
    "required": ["stance", "argument_for", "argument_against", "improved_hypothesis",
                 "citation_idx", "experiment_ideas"],
    "additionalProperties": False,
}

EXP_SCHEMA = {
    "type": "object",
    "properties": {
        "experiments": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "what": {"type": "string"},
                "how": {"type": "string"},
                "data_source": {"type": "string"},
                "method_type": {"type": "string"},   # download_data|math_analysis|
                                                     # theoretical|simulation
                "controls": {"type": "string"},
                "discriminator": {"type": "string"},
            },
            "required": ["title", "what", "how", "data_source", "method_type",
                         "controls", "discriminator"],
            "additionalProperties": False}},
    },
    "required": ["experiments"],
    "additionalProperties": False,
}


class HypothesisFlow:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)

    # --- approve / reject --------------------------------------------------
    def set_status(self, project_id: str, hyp_id: str, status: str, reason: str = ""
                   ) -> dict[str, Any]:
        h = self.store.get(hyp_id)
        if not h:
            return {"ok": False, "error": "hypothesis not found"}
        status = status.upper()
        if status not in {"APPROVED", "REJECTED", "PROPOSED"}:
            return {"ok": False, "error": "invalid status"}
        if status == "APPROVED" and not reason.strip():
            return {"ok": False, "error": "aprobar requiere una razón"}
        self.store.update_payload(hyp_id, {"status": status,
                                           "approval_reason": reason}, status=status)
        self.ledger.record_event(project_id, ProvenanceAction.UPDATE, "human",
                                 f"hipótesis {h.get('tag')} → {status}: {reason}"[:150],
                                 {"status": status}, entity_id=hyp_id)
        return {"ok": True, "hyp_id": hyp_id, "status": status}

    def approved(self, project_id: str) -> list[dict[str, Any]]:
        return [h for h in self.store.list_objects(project_id, kind="candidate")
                if (h.get("status") or "").upper() == "APPROVED"]

    # --- literature per hypothesis ----------------------------------------
    def _english_query(self, h: dict[str, Any], domain: str, *, use_ai: bool) -> str:
        """Turn the (Spanish) hypothesis into an English scientific search query."""
        base = f"{h.get('title','')} {h.get('trigger_question','')}".strip()
        if use_ai:
            try:
                from ..llm.providers import CodexCliProvider
                prov = CodexCliProvider(timeout_sec=90)
                if prov.available():
                    schema = {"type": "object",
                              "properties": {"query": {"type": "string"},
                                             "keywords": {"type": "array",
                                                          "items": {"type": "string"}}},
                              "required": ["query", "keywords"],
                              "additionalProperties": False}
                    out = prov.complete_json(
                        f"Dominio: {domain}. Convierte esta hipótesis en una CONSULTA de "
                        "búsqueda académica EN INGLÉS con los términos técnicos correctos "
                        f"(no traducción literal): «{base}». Devuelve query (una línea de "
                        "6-12 términos clave en inglés) y keywords (lista). Sin comillas.",
                        schema, temperature=0.1)
                    q = (out.get("query") or "").strip()
                    if q:
                        return q[:240]
            except Exception:  # noqa: BLE001
                pass
        return base[:240]

    def investigate(self, project_id: str, hyp_id: str, *, use_ai: bool = True,
                    via: str = "") -> dict[str, Any]:
        h = self.store.get(hyp_id)
        if not h:
            return {"ok": False, "error": "hypothesis not found"}
        p = self.ledger.get_project(project_id)
        domain = p.domain if p else ""
        query = self._english_query(h, domain, use_ai=use_ai)
        from ..knowledge_mesh import mesh
        rows = int(os.environ.get("ACERO_LIT_ROWS", "10"))     # broader by default
        try:
            found = mesh.topical_search(query, domain=domain, rows=rows)
        except Exception:  # noqa: BLE001
            found = []
        papers = []
        for o in found:
            lid = new_id("lit")
            rec = {"id": lid, "angle": h.get("tag", ""), "hyp_id": hyp_id,
                   "title": o["title"], "doi": o.get("doi", ""),
                   "type": o["type"], "integrity": o["integrity"],
                   "url": o["url"], "authors": o["authors"],
                   "abstract": o.get("abstract", ""), "source": o.get("source", ""),
                   "topics": o.get("topics", []), "relevance": o.get("relevance"),
                   "openalex_id": o.get("openalex_id", ""),
                   "is_oa": o.get("is_oa", False), "pdf_url": o.get("pdf_url", ""),
                   "referenced_works": o.get("referenced_works", []),
                   "via": via, "hyp_version": int(h.get("version", 1)),
                   "query_used": query}
            self.store.put(project_id, "literature", lid, rec, status="INDEXED",
                           actor="knowledge_mesh",
                           summary=f"paper para {h.get('tag')}: {(o['title'] or '')[:50]}")
            papers.append(rec)

        confront = self._confront(h, papers, use_ai=use_ai)
        confront["query_used"] = query
        confront["hyp_version"] = int(h.get("version", 1))
        self.store.update_payload(hyp_id, {
            "lit_status": "DONE", "lit_count": len(papers),
            "confrontation": confront})
        from .obsidian_sync import sync_project_best_effort
        sync_project_best_effort(project_id, self._sf)
        from .critic import critique_async
        critique_async(project_id, hyp_id, "literatura",
                       f"Hipótesis: {h.get('title','')}\n"
                       f"Postura: {confront.get('stance','')}\n"
                       f"A favor: {confront.get('argument_for','')}\n"
                       f"En contra: {confront.get('argument_against','')}\n"
                       f"Mejorada: {confront.get('improved_hypothesis','')}\n"
                       f"Papers: " + "; ".join(p['title'] for p in papers[:6]),
                       self._sf)
        return {"ok": True, "hyp_id": hyp_id, "tag": h.get("tag"),
                "n_papers": len(papers), "papers": papers, "confrontation": confront}

    @staticmethod
    def _cite(p: dict[str, Any]) -> dict[str, Any]:
        return {"title": p["title"], "doi": p.get("doi", ""),
                "source": p.get("source", ""), "url": p.get("url", ""),
                "relevance": p.get("relevance"),
                "abstract": (p.get("abstract") or "")[:280],
                "has_fulltext": bool(p.get("fulltext_excerpt")),
                "integrity": p.get("integrity", "")}

    def _confront(self, h: dict[str, Any], papers: list[dict[str, Any]], *, use_ai: bool
                  ) -> dict[str, Any]:
        if not use_ai or not papers:
            return {"provider": "none",
                    "argument_for": "", "argument_against": "",
                    "improved_hypothesis": h.get("title", ""), "stance": "unassessed",
                    "experiment_ideas": [],
                    "citations": [self._cite(p) for p in papers[:3]]}
        try:
            from ..llm.providers import CodexCliProvider
            prov = CodexCliProvider(timeout_sec=200)
            if not prov.available():
                raise RuntimeError("codex unavailable")
            def _content(p: dict[str, Any]) -> str:
                if p.get("fulltext_excerpt"):
                    return ("TEXTO COMPLETO (leído del PDF): "
                            + p["fulltext_excerpt"][:1600])
                return "ABSTRACT: " + (p.get("abstract") or "sin abstract")[:700]
            plist = "\n\n".join(
                f"[{i}] {p['title']} ({p.get('source','')}, {p['doi']}) "
                f"{'[RETRACTADO]' if p['integrity']=='retracted' else ''}\n"
                f"    {_content(p)}"
                for i, p in enumerate(papers))
            prompt = (
                "Confronta esta HIPÓTESIS LEYENDO los abstracts reales de la literatura. "
                f"Hipótesis: «{h.get('title','')}». Pregunta detonante: "
                f"{h.get('trigger_question','')}.\n\nPapers reales (con abstract; "
                f"referéncialos SOLO por índice, no inventes citas):\n{plist}\n\n"
                "Analiza el CONTENIDO de los abstracts. Devuelve: stance "
                "(supports|challenges|mixed), argument_for (qué de la evidencia la apoya, "
                "citando hallazgos concretos de los abstracts), argument_against (qué la "
                "debilita o contradice), improved_hypothesis (versión afinada por lo leído), "
                "citation_idx (índices de los papers RELEVANTES que realmente usaste), y "
                "experiment_ideas (2-4 formas CONCRETAS de comprobar la hipótesis que "
                "PODAMOS EJECUTAR EN UNA COMPUTADORA: bajar datasets públicos reales — NASA, "
                "ESA, MAST, arXiv data, Planck/WMAP, catálogos abiertos —, correr análisis "
                "matemático/estadístico o simulaciones teóricas en nuestra máquina, o "
                "formular un experimento numérico propio. Cada idea: title, approach (pasos "
                "breves), data_source (dataset PÚBLICO real y accesible, o 'teórico'/"
                "'simulación'), method_type (download_data|math_analysis|theoretical|"
                "simulation), feasible_local (true si corre en una laptop). "
                "Si los papers NO son relevantes, dilo y baja tu confianza. Sé escéptico y "
                "honesto; nada es un descubrimiento. En español.")
            out = prov.complete_json(prompt, CONFRONT_SCHEMA, temperature=0.3)
            idxs = [i for i in out.get("citation_idx", []) if 0 <= i < len(papers)]
            return {"provider": "codex", "stance": out.get("stance", ""),
                    "argument_for": out.get("argument_for", ""),
                    "argument_against": out.get("argument_against", ""),
                    "improved_hypothesis": out.get("improved_hypothesis", ""),
                    "experiment_ideas": out.get("experiment_ideas", []),
                    "citations": [self._cite(papers[i]) for i in idxs] or
                                 [self._cite(p) for p in papers[:3]]}
        except Exception:  # noqa: BLE001
            return {"provider": "none", "argument_for": "", "argument_against": "",
                    "improved_hypothesis": h.get("title", ""), "stance": "unassessed",
                    "experiment_ideas": [],
                    "citations": [self._cite(p) for p in papers[:3]]}

    def adopt_improved(self, project_id: str, hyp_id: str) -> dict[str, Any]:
        """Take the confrontation's improved hypothesis → bump the original to a new
        version, archiving the previous wording (and its confrontation) in history."""
        h = self.store.get(hyp_id)
        if not h:
            return {"ok": False, "error": "hypothesis not found"}
        conf = h.get("confrontation") or {}
        improved = (conf.get("improved_hypothesis") or "").strip()
        if not improved:
            return {"ok": False, "error": "no hay hipótesis mejorada que tomar"}
        old_title = h.get("title", "")
        if improved == old_title:
            return {"ok": False, "error": "la hipótesis mejorada es idéntica a la actual"}
        cur_ver = int(h.get("version", 1))
        new_ver = cur_ver + 1
        history = list(h.get("history", []))
        history.append({"version": cur_ver, "title": old_title,
                        "trigger_question": h.get("trigger_question", ""),
                        "confrontation": conf, "archived_at": now_iso()})
        self.store.update_payload(hyp_id, {
            "title": improved, "version": new_ver, "history": history,
            # the archived confrontation belongs to v(cur_ver); the new version starts
            # unassessed until it is re-investigated against the literature.
            "lit_status": "STALE"})
        self.ledger.record_event(
            project_id, ProvenanceAction.UPDATE, "human",
            f"hipótesis {h.get('tag')} tomada mejorada → v{new_ver}"[:150],
            {"version": new_ver}, entity_id=hyp_id)
        from .obsidian_sync import sync_project_best_effort
        sync_project_best_effort(project_id, self._sf)
        from .critic import critique_async
        critique_async(project_id, hyp_id, "nueva_version",
                       f"El equipo ADOPTÓ esta nueva versión (v{new_ver}): «{improved}». "
                       f"Versión anterior: «{old_title}». ¿La nueva formulación es "
                       "realmente mejor, o solo más cómoda/vaga?", self._sf)
        return {"ok": True, "hyp_id": hyp_id, "version": new_ver,
                "title": improved, "previous": old_title}

    # --- C6: deep literature — follow the references (snowballing) + OA PDFs ---
    def deepen_literature(self, project_id: str, hyp_id: str, *,
                          snowballer: Any | None = None,
                          pdf_fetcher: Any | None = None,
                          rows: int = 10) -> dict[str, Any]:
        """Level-2 literature: index the REFERENCES of the papers already read,
        and pull open-access arXiv PDFs into the Obsidian vault for deep reading."""
        h = self.store.get(hyp_id)
        if not h:
            return {"ok": False, "error": "hypothesis not found"}
        mine = [x for x in self.store.list_objects(project_id, kind="literature")
                if x.get("hyp_id") == hyp_id]
        if not mine:
            return {"ok": False, "error": "investiga primero: sin papers indexados"}
        known = {(x.get("doi") or "").lower() for x in
                 self.store.list_objects(project_id, kind="literature")}
        known |= {(x.get("title") or "").lower()[:60] for x in
                  self.store.list_objects(project_id, kind="literature")}
        ref_ids: list[str] = []
        for x in mine:
            ref_ids += list(x.get("referenced_works") or [])
        ref_ids = list(dict.fromkeys(ref_ids))          # dedup, keep order
        if snowballer is None:
            from ..knowledge_mesh import mesh as _mesh
            snowballer = _mesh.snowball

        added = []
        if ref_ids:
            try:
                refs = snowballer(ref_ids, rows=rows)
            except Exception:  # noqa: BLE001
                refs = []
            for o in refs:
                key_d = (o.get("doi") or "").lower()
                key_t = (o.get("title") or "").lower()[:60]
                if (key_d and key_d in known) or (key_t and key_t in known):
                    continue
                lid = new_id("lit")
                rec = {"id": lid, "angle": h.get("tag", ""), "hyp_id": hyp_id,
                       "title": o["title"], "doi": o.get("doi", ""),
                       "type": o["type"], "integrity": o["integrity"],
                       "url": o["url"], "authors": o["authors"],
                       "abstract": o.get("abstract", ""),
                       "source": o.get("source", ""),
                       "relevance": o.get("relevance"), "depth": 2}
                self.store.put(project_id, "literature", lid, rec, status="INDEXED",
                               actor="knowledge_mesh",
                               summary=f"🕸 referencia nivel-2 para {h.get('tag')}: "
                                       f"{(o['title'] or '')[:45]}")
                known.add(key_d or key_t)
                added.append(rec["title"][:80])

        # download OPEN-ACCESS full text, extract it, and READ beyond the abstract
        allp = [x for x in self.store.list_objects(project_id, kind="literature")
                if x.get("hyp_id") == hyp_id]
        read = self._read_fulltext(project_id, allp, fetcher=pdf_fetcher)
        pdfs = self._fetch_arxiv_pdfs(project_id, mine, pdf_fetcher=pdf_fetcher)

        from .obsidian_sync import sync_project_best_effort
        sync_project_best_effort(project_id, self._sf)
        # rebuild the semantic index over the (now richer) literature
        try:
            from .vault_index import build_index
            idx = build_index(project_id, self._sf, force=True)
            backend = idx.get("backend")
        except Exception:  # noqa: BLE001
            backend = "unavailable"
        return {"ok": True, "level2_added": len(added), "titles": added[:8],
                "pdfs_saved": pdfs, "fulltext_read": read["read"],
                "fulltext_attempted": read["attempted"],
                "embeddings_backend": backend,
                "note": ("Referencias reales (OpenAlex) + PDFs open-access descargados, "
                         f"LEÍDOS a texto completo ({read['read']}/{read['attempted']}) "
                         "e indexados por significado (embeddings). Vacío = las fuentes "
                         "no resolvieron más; nada se inventa.")}

    def _read_fulltext(self, project_id: str, papers: list[dict[str, Any]], *,
                       fetcher: Any | None = None, cap: int = 8) -> dict[str, int]:
        """Download OA PDFs, extract text, store a real excerpt on each paper."""
        from .fulltext import fetch_fulltext
        attempted = read = 0
        for p in papers:
            if p.get("fulltext_excerpt") or read >= cap:
                continue
            if not (p.get("pdf_url") or p.get("is_oa") or p.get("source") == "arxiv"):
                continue
            attempted += 1
            try:
                r = fetch_fulltext(p, downloader=fetcher) if fetcher \
                    else fetch_fulltext(p)
            except Exception:  # noqa: BLE001
                continue
            if r.get("ok"):
                self.store.update_payload(p["id"], {
                    "fulltext_excerpt": r["excerpt"], "fulltext_chars": r["chars"],
                    "fulltext_url": r.get("url", "")})
                read += 1
            else:
                self.store.update_payload(p["id"], {
                    "fulltext_status": r.get("reason", "no accesible")})
        return {"attempted": attempted, "read": read}

    def _fetch_arxiv_pdfs(self, project_id: str, papers: list[dict[str, Any]], *,
                          pdf_fetcher: Any | None = None, cap: int = 3) -> list[str]:
        """Best-effort: arXiv PDFs of this hypothesis' papers → vault Literatura/PDFs."""
        import re as _re
        import urllib.request as _rq

        from .obsidian_sync import ObsidianExporter, _safe
        p = self.ledger.get_project(project_id)
        if p is None:
            return []
        vault_dir = ObsidianExporter().root / _safe(p.title, 60) / "Literatura" / "PDFs"
        saved: list[str] = []
        for x in papers:
            if len(saved) >= cap:
                break
            url = x.get("url") or ""
            m = _re.search(r"arxiv\.org/abs/([\w.\-/]+)", url)
            if not m:
                continue
            aid = m.group(1)
            fname = _safe(aid.replace("/", "_")) + ".pdf"
            dest = vault_dir / fname
            if dest.exists():
                continue
            try:
                if pdf_fetcher is not None:
                    data = pdf_fetcher(aid)
                else:
                    req = _rq.Request(f"https://arxiv.org/pdf/{aid}",
                                      headers={"User-Agent": "ACERO/0.1"})
                    with _rq.urlopen(req, timeout=60) as r:
                        data = r.read(25 * 1024 * 1024)
                if data[:4] == b"%PDF":
                    vault_dir.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(data)
                    saved.append(fname)
            except Exception:  # noqa: BLE001 - a missing PDF is skipped, never faked
                continue
        return saved

    def investigate_all(self, project_id: str, *, use_ai: bool = True) -> dict[str, Any]:
        results = [self.investigate(project_id, h["id"], use_ai=use_ai)
                   for h in self.approved(project_id)]
        return {"ok": True, "n": len(results),
                "results": [{"tag": r.get("tag"), "n_papers": r.get("n_papers"),
                             "stance": (r.get("confrontation") or {}).get("stance")}
                            for r in results if r.get("ok")]}

    # --- experiments per hypothesis ---------------------------------------
    def propose_experiments(self, project_id: str, hyp_id: str, *, use_ai: bool = True,
                            via: str = "") -> dict[str, Any]:
        h = self.store.get(hyp_id)
        if not h:
            return {"ok": False, "error": "hypothesis not found"}
        exps = self._experiment_specs(h, use_ai=use_ai)
        created = []
        for e in exps:
            eid = new_id("exp")
            rec = {"id": eid, "hyp_id": hyp_id, "hyp_tag": h.get("tag", ""),
                   "title": e.get("title", ""), "what": e.get("what", ""),
                   "how": e.get("how", ""), "data_source": e.get("data_source", ""),
                   "method_type": e.get("method_type", ""),
                   "controls": e.get("controls", ""),
                   "discriminator": e.get("discriminator", ""), "via": via,
                   "hyp_version": int(h.get("version", 1)),
                   "status": "PROPOSED", "synthetic": None, "created_at": now_iso()}
            self.store.put(project_id, "experiment", eid, rec, status="PROPOSED",
                           actor="experiment_engine",
                           summary=f"experimento propuesto para {h.get('tag')}")
            created.append(rec)
        from .obsidian_sync import sync_project_best_effort
        sync_project_best_effort(project_id, self._sf)
        from .critic import critique_async
        for rec in created:
            critique_async(project_id, rec["id"], "experimento_propuesto",
                           f"Hipótesis: {h.get('title','')}\nExperimento: {rec['title']}\n"
                           f"Qué: {rec['what']}\nCómo: {rec['how']}\n"
                           f"Datos: {rec['data_source']}\nControles: {rec['controls']}\n"
                           f"Discriminador: {rec['discriminator']}", self._sf)
        return {"ok": True, "created": created}

    def _experiment_specs(self, h: dict[str, Any], *, use_ai: bool) -> list[dict[str, Any]]:
        # seeds: the computer-doable ideas surfaced during the literature confrontation
        ideas = ((h.get("confrontation") or {}).get("experiment_ideas") or [])
        seed_txt = ""
        if ideas:
            seed_txt = "\nParte de estas IDEAS ya sugeridas al leer la literatura " \
                       "(conviértelas en experimentos completos y ejecutables):\n" + \
                       "\n".join(f"- {i.get('title','')} [{i.get('method_type','')}] "
                                 f"datos: {i.get('data_source','')} — {i.get('approach','')}"
                                 for i in ideas[:4])
        if use_ai:
            try:
                from ..llm.providers import CodexCliProvider
                prov = CodexCliProvider(timeout_sec=200)
                if prov.available():
                    prompt = (
                        f"Propón 2-3 EXPERIMENTOS COMPUTACIONALES concretos para probar la "
                        f"hipótesis «{h.get('title','')}» (duda: {h.get('doubt','')}).{seed_txt}\n"
                        "Prioriza cosas EJECUTABLES EN NUESTRA MÁQUINA: bajar datasets públicos "
                        "reales (NASA/ESA/MAST/Planck/catálogos abiertos), correr análisis "
                        "matemático/estadístico o simulaciones teóricas locales. Cada uno: "
                        "title, what (qué mide), how (método paso a paso), data_source (dataset "
                        "PÚBLICO real y accesible, con nombre concreto), method_type "
                        "(download_data|math_analysis|theoretical|simulation), controls "
                        "(nulos/controles), discriminator (qué resultado la apoyaría vs la "
                        "falsaría). En español. Reproducible; nada es un descubrimiento.")
                    out = prov.complete_json(prompt, EXP_SCHEMA, temperature=0.4)
                    if out.get("experiments"):
                        return out["experiments"]
            except Exception:  # noqa: BLE001
                pass
        # offline fallback: derive from confrontation ideas if present, else a null test
        if ideas:
            return [{"title": i.get("title", ""), "what": i.get("approach", ""),
                     "how": i.get("approach", ""), "data_source": i.get("data_source", ""),
                     "method_type": i.get("method_type", ""),
                     "controls": "nulos/surrogatos del dominio",
                     "discriminator": "efecto estable y significativo vs nulos"}
                    for i in ideas[:3]]
        return [{"title": f"Prueba nula para «{h.get('title','')[:40]}»",
                 "what": "Verifica que la señal no es ruido/artefacto",
                 "how": "Comparar contra surrogatos de ruido y datos barajados",
                 "data_source": "dataset público del dominio",
                 "method_type": "math_analysis",
                 "controls": "ruido rojo AR(1), shuffle, estrella/muestra de control",
                 "discriminator": "SNR y estabilidad del efecto bajo nulos"}]

    # available real analyses (mapped by keywords in data_source/title)
    def _real_runner(self, text: str):
        # match on the DATA SOURCE / method keywords, specific enough to avoid false
        # hits (e.g. the hypothesis tag "H0" must NOT trigger the Hubble runner).
        t = text.lower()
        if any(w in t for w in ("kepler", "exoplanet", "exoplaneta", "tercera ley de kepler",
                                "third law")):
            from ..studies.kepler_law import verify
            return verify
        if "hubble" in t or "tensión de hubble" in t or "hubble tension" in t:
            from ..studies.hubble_tension import analyze
            return analyze
        return None

    def run_experiment(self, project_id: str, exp_id: str, *, use_ai: bool = True
                       ) -> dict[str, Any]:
        e = self.store.get(exp_id)
        if not e:
            return {"ok": False, "error": "experiment not found"}
        runner = self._real_runner(f"{e.get('title','')} {e.get('data_source','')} "
                                   f"{e.get('what','')}")
        from .critic import critique_async
        from .obsidian_sync import sync_project_best_effort
        if runner is not None:
            res = runner()
            self.store.update_payload(exp_id, {
                "status": "COMPLETE", "synthetic": False, "result": res,
                "claim": res.get("claim", "")}, status="COMPLETE")
            sync_project_best_effort(project_id, self._sf)
            critique_async(project_id, exp_id, "experimento_resultado",
                           f"Experimento: {e.get('title','')}\n"
                           f"Resultado real: {str(res.get('claim',''))[:600]}", self._sf)
            return {"ok": True, "mode": "real_analysis", "result": res}

        # EXPERIMENT FACTORY: generate + sandbox-run the analysis for real
        if use_ai:
            fr = self._run_factory(project_id, e)
            if fr is not None:
                return fr

        # no way to execute this yet → reproducible PLAN, honestly not a result
        plan = self._plan(e, use_ai=use_ai)
        self.store.update_payload(exp_id, {
            "status": "PLANNED", "synthetic": None, "plan": plan}, status="PLANNED")
        sync_project_best_effort(project_id, self._sf)
        critique_async(project_id, exp_id, "experimento_resultado",
                       f"Experimento: {e.get('title','')}\nPLAN (sin ejecutar aún): "
                       f"{plan[:600]}", self._sf)
        return {"ok": True, "mode": "plan_only", "plan": plan,
                "note": ("ACERO aún no tiene código para ejecutar este experimento con datos "
                         "reales; se generó un PLAN reproducible (pendiente). No es un resultado.")}

    def _run_factory(self, project_id: str, e: dict[str, Any]) -> dict[str, Any] | None:
        """Try the Experiment Factory. Returns the run dict on success, else None
        (caller falls back to an honest PLAN — never a fabricated result)."""
        from .critic import critique_async
        from .experiment_factory import run_generated
        from .obsidian_sync import sync_project_best_effort
        h = self.store.get(e.get("hyp_id", "")) or {}
        p = self.ledger.get_project(project_id)
        try:
            fr = run_generated(e, h, domain=(p.domain if p else ""))
        except Exception as exc:  # noqa: BLE001 - factory crash must not kill the flow
            fr = {"ok": False, "stage": "factory", "error": str(exc)[:300]}
        if not fr.get("ok"):
            # keep the honest trace of WHY it could not execute
            self.store.update_payload(e["id"], {"factory_error": {
                "stage": fr.get("stage", ""), "error": fr.get("error", ""),
                "attempts": fr.get("attempts", 0), "at": now_iso()}})
            return None
        res = fr["result"]
        claim = (f"[CÓDIGO GENERADO POR IA — revisar script] {res['verdict']}: "
                 f"{res['verdict_reason']}")[:300]
        real_data = bool(fr.get("provenance"))
        self.store.update_payload(e["id"], {
            "status": "COMPLETE", "synthetic": (not real_data), "result": res,
            "claim": claim, "provenance": fr.get("provenance", []),
            "code_path": fr.get("code_path", ""),
            "artifacts_dir": fr.get("artifacts_dir", ""),
            "factory": {"attempts": fr.get("attempts"), "generator": fr.get("generator"),
                        "duration_sec": fr.get("duration_sec"),
                        "disclaimer": fr.get("disclaimer", "")}},
            status="COMPLETE")
        sync_project_best_effort(project_id, self._sf)
        critique_async(project_id, e["id"], "experimento_resultado",
                       f"Experimento: {e.get('title','')}\n"
                       f"Veredicto del análisis generado: {res['verdict']} — "
                       f"{res['verdict_reason'][:300]}\n"
                       f"Métricas: {str(res.get('metrics'))[:300]}\n"
                       f"Nulos: {str(res.get('null_test'))[:200]}\n"
                       "OJO: el código lo escribió una IA; juzga también si el "
                       "análisis en sí es válido.", self._sf)
        return {"ok": True, "mode": "generated_analysis", "result": res,
                "provenance": fr.get("provenance", []),
                "attempts": fr.get("attempts"), "claim": claim,
                "disclaimer": fr.get("disclaimer", "")}

    def _plan(self, e: dict[str, Any], *, use_ai: bool) -> str:
        base = (f"Objetivo: {e.get('what','')}\nMétodo: {e.get('how','')}\n"
                f"Datos: {e.get('data_source','')}\nControles: {e.get('controls','')}\n"
                f"Discriminador: {e.get('discriminator','')}")
        if not use_ai:
            return base
        try:
            from ..llm.providers import CodexCliProvider
            prov = CodexCliProvider(timeout_sec=150)
            if prov.available():
                r = prov.complete(
                    "Convierte esto en un plan de ejecución reproducible, paso a paso, con "
                    "los controles y el criterio de decisión, en español (máx 200 palabras). "
                    "NO inventes resultados:\n" + base, temperature=0.2, max_tokens=600)
                return r.text
        except Exception:  # noqa: BLE001
            pass
        return base

    def run_all_experiments(self, project_id: str, *, use_ai: bool = True) -> dict[str, Any]:
        proposed = [e for e in self.store.list_objects(project_id, kind="experiment")
                    if (e.get("status") or "") == "PROPOSED"]
        out = [self.run_experiment(project_id, e["id"], use_ai=use_ai) for e in proposed]
        real = sum(1 for r in out if r.get("mode") == "real_analysis")
        return {"ok": True, "ran": len(out), "real_analyses": real,
                "plans": len(out) - real,
                "note": "Los experimentos con código real se ejecutaron; el resto quedó como "
                        "plan reproducible pendiente de datos."}

    def experiments_for(self, project_id: str, hyp_id: str) -> list[dict[str, Any]]:
        return [e for e in self.store.list_objects(project_id, kind="experiment")
                if e.get("hyp_id") == hyp_id]
