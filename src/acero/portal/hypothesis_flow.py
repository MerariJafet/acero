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
    },
    "required": ["stance", "argument_for", "argument_against", "improved_hypothesis",
                 "citation_idx"],
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
                "controls": {"type": "string"},
                "discriminator": {"type": "string"},
            },
            "required": ["title", "what", "how", "data_source", "controls",
                         "discriminator"],
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
    def _query(self, h: dict[str, Any], domain: str) -> str:
        base = h.get("title") or h.get("description", "")
        return f"{domain} {base}".strip()[:220]

    def investigate(self, project_id: str, hyp_id: str, *, use_ai: bool = True
                    ) -> dict[str, Any]:
        h = self.store.get(hyp_id)
        if not h:
            return {"ok": False, "error": "hypothesis not found"}
        p = self.ledger.get_project(project_id)
        domain = p.domain if p else ""
        from ..knowledge_mesh.connectors import crossref
        try:
            objs = crossref.search(self._query(h, domain), rows=5)
        except Exception:  # noqa: BLE001
            objs = []
        papers = []
        for o in objs:
            doi = (o.identifiers.get("doi") or [""])[0]
            if not doi:
                continue
            lid = new_id("lit")
            rec = {"id": lid, "angle": h.get("tag", ""), "hyp_id": hyp_id,
                   "title": o.title, "doi": doi, "type": o.object_type.value,
                   "integrity": o.integrity_status, "url": o.canonical_url,
                   "authors": o.authors[:4]}
            self.store.put(project_id, "literature", lid, rec, status="INDEXED",
                           actor="knowledge_mesh",
                           summary=f"paper para {h.get('tag')}: {o.title[:50]}")
            papers.append(rec)

        confront = self._confront(h, papers, use_ai=use_ai)
        self.store.update_payload(hyp_id, {
            "lit_status": "DONE", "lit_count": len(papers),
            "confrontation": confront})
        return {"ok": True, "hyp_id": hyp_id, "tag": h.get("tag"),
                "n_papers": len(papers), "papers": papers, "confrontation": confront}

    def _confront(self, h: dict[str, Any], papers: list[dict[str, Any]], *, use_ai: bool
                  ) -> dict[str, Any]:
        if not use_ai or not papers:
            return {"provider": "none",
                    "argument_for": "", "argument_against": "",
                    "improved_hypothesis": h.get("title", ""), "stance": "unassessed",
                    "citations": [{"title": p["title"], "doi": p["doi"]} for p in papers[:3]]}
        try:
            from ..llm.providers import CodexCliProvider
            prov = CodexCliProvider(timeout_sec=200)
            if not prov.available():
                raise RuntimeError("codex unavailable")
            plist = "\n".join(f"[{i}] {p['title']} ({p['doi']}) "
                              f"{'[RETRACTADO]' if p['integrity']=='retracted' else ''}"
                              for i, p in enumerate(papers))
            prompt = (
                f"Confronta esta HIPÓTESIS con la literatura real encontrada. Hipótesis: "
                f"«{h.get('title','')}». Pregunta detonante: {h.get('trigger_question','')}. "
                f"Papers reales (referéncialos SOLO por índice, no inventes citas):\n{plist}\n\n"
                "Devuelve: stance (supports|challenges|mixed), argument_for, "
                "argument_against, improved_hypothesis (una versión mejorada/afinada por la "
                "evidencia) y citation_idx (índices de los papers que respaldan tu análisis). "
                "Sé escéptico y honesto; nada es un descubrimiento. En español.")
            out = prov.complete_json(prompt, CONFRONT_SCHEMA, temperature=0.3)
            idxs = [i for i in out.get("citation_idx", []) if 0 <= i < len(papers)]
            return {"provider": "codex", "stance": out.get("stance", ""),
                    "argument_for": out.get("argument_for", ""),
                    "argument_against": out.get("argument_against", ""),
                    "improved_hypothesis": out.get("improved_hypothesis", ""),
                    "citations": [{"title": papers[i]["title"], "doi": papers[i]["doi"]}
                                  for i in idxs] or
                                 [{"title": p["title"], "doi": p["doi"]} for p in papers[:3]]}
        except Exception:  # noqa: BLE001
            return {"provider": "none", "argument_for": "", "argument_against": "",
                    "improved_hypothesis": h.get("title", ""), "stance": "unassessed",
                    "citations": [{"title": p["title"], "doi": p["doi"]} for p in papers[:3]]}

    def investigate_all(self, project_id: str, *, use_ai: bool = True) -> dict[str, Any]:
        results = [self.investigate(project_id, h["id"], use_ai=use_ai)
                   for h in self.approved(project_id)]
        return {"ok": True, "n": len(results),
                "results": [{"tag": r.get("tag"), "n_papers": r.get("n_papers"),
                             "stance": (r.get("confrontation") or {}).get("stance")}
                            for r in results if r.get("ok")]}

    # --- experiments per hypothesis ---------------------------------------
    def propose_experiments(self, project_id: str, hyp_id: str, *, use_ai: bool = True
                            ) -> dict[str, Any]:
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
                   "controls": e.get("controls", ""),
                   "discriminator": e.get("discriminator", ""),
                   "status": "PROPOSED", "synthetic": None, "created_at": now_iso()}
            self.store.put(project_id, "experiment", eid, rec, status="PROPOSED",
                           actor="experiment_engine",
                           summary=f"experimento propuesto para {h.get('tag')}")
            created.append(rec)
        return {"ok": True, "created": created}

    def _experiment_specs(self, h: dict[str, Any], *, use_ai: bool) -> list[dict[str, Any]]:
        if use_ai:
            try:
                from ..llm.providers import CodexCliProvider
                prov = CodexCliProvider(timeout_sec=200)
                if prov.available():
                    prompt = (
                        f"Propón 2-3 EXPERIMENTOS COMPUTACIONALES concretos para probar la "
                        f"hipótesis «{h.get('title','')}» (duda: {h.get('doubt','')}). Cada uno: "
                        "title, what (qué mide), how (método paso a paso), data_source (dataset "
                        "PÚBLICO real y accesible), controls (nulos/controles), discriminator "
                        "(qué resultado la apoyaría vs la falsaría). En español. Reproducible; "
                        "nada es un descubrimiento.")
                    out = prov.complete_json(prompt, EXP_SCHEMA, temperature=0.4)
                    if out.get("experiments"):
                        return out["experiments"]
            except Exception:  # noqa: BLE001
                pass
        return [{"title": f"Prueba nula para «{h.get('title','')[:40]}»",
                 "what": "Verifica que la señal no es ruido/artefacto",
                 "how": "Comparar contra surrogatos de ruido y datos barajados",
                 "data_source": "dataset público del dominio",
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
        if runner is not None:
            res = runner()
            self.store.update_payload(exp_id, {
                "status": "COMPLETE", "synthetic": False, "result": res,
                "claim": res.get("claim", "")}, status="COMPLETE")
            return {"ok": True, "mode": "real_analysis", "result": res}
        # no code to run this yet → reproducible PLAN, honestly not a result
        plan = self._plan(e, use_ai=use_ai)
        self.store.update_payload(exp_id, {
            "status": "PLANNED", "synthetic": None, "plan": plan}, status="PLANNED")
        return {"ok": True, "mode": "plan_only", "plan": plan,
                "note": ("ACERO aún no tiene código para ejecutar este experimento con datos "
                         "reales; se generó un PLAN reproducible (pendiente). No es un resultado.")}

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
