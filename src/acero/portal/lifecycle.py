"""Lifecycle — trace map, critique cascade, safe delete w/ vault memory,
save/anchor experiments, and the active-processes view.

Rules kept: nothing is silently lost (deletes archive a memory note to the
Obsidian vault first), saved experiments survive their hypothesis, and every
derived object keeps provenance to WHO/WHAT created it (via, origin, IDs).
"""

from __future__ import annotations

from typing import Any

from ..core.clock import now_iso
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger
from ..provenance.events import ProvenanceAction


class Lifecycle:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)

    # ---- helpers ---------------------------------------------------------------
    def _deps(self, project_id: str, hyp_id: str) -> dict[str, list[dict[str, Any]]]:
        by = {}
        for kind in ("literature", "experiment", "critique", "mission",
                     "synthesis", "dossier"):
            key = "target_id" if kind == "critique" else "hyp_id"
            by[kind] = [x for x in self.store.list_objects(project_id, kind=kind)
                        if x.get(key) == hyp_id]
        return by

    # ---- 3) considerar crítica: re-version the WHOLE flow from an earlier level -
    def consider_critique(self, project_id: str, critique_id: str) -> dict[str, Any]:
        c = self.store.get(critique_id)
        if not c:
            return {"ok": False, "error": "critique not found"}
        target = self.store.get(c.get("target_id", "")) or {}
        # resolve the OWNING hypothesis (critique may target an experiment)
        hyp = target if "tag" in target and "hyp_id" not in target else \
            (self.store.get(target.get("hyp_id", "")) or {})
        if not hyp:
            return {"ok": False, "error": "no se encontró la hipótesis dueña"}
        cur_ver = int(hyp.get("version", 1))
        new_ver = cur_ver + 1
        history = list(hyp.get("history", []))
        history.append({"version": cur_ver, "title": hyp.get("title", ""),
                        "trigger_question": hyp.get("trigger_question", ""),
                        "reason": "reconsideración por crítica de Aristóteles",
                        "critique_id": critique_id,
                        "critique_summary": str(c.get("summary", ""))[:200],
                        "archived_at": now_iso()})
        self.store.update_payload(hyp["id"], {
            "version": new_ver, "history": history,
            "lit_status": "STALE",
            "reconsider_note": {"critique_id": critique_id,
                                "summary": str(c.get("summary", ""))[:250],
                                "from_level": c.get("task", ""), "at": now_iso()}})
        # downstream experiments of this hypothesis are flagged for re-review
        for e in self.store.list_objects(project_id, kind="experiment"):
            if e.get("hyp_id") == hyp["id"] and e.get("status") == "COMPLETE":
                self.store.update_payload(e["id"], {"superseded_by_critique": critique_id})
        self.ledger.record_event(
            project_id, ProvenanceAction.UPDATE, "human",
            f"crítica considerada → {hyp.get('tag')} pasa a v{new_ver}"[:150],
            {"critique_id": critique_id}, entity_id=hyp["id"])
        return {"ok": True, "hyp_id": hyp["id"], "tag": hyp.get("tag"),
                "version": new_ver,
                "note": (f"El flujo de {hyp.get('tag')} se replantea desde el nivel "
                         f"'{c.get('task','')}': v{new_ver}, literatura marcada STALE "
                         "y experimentos previos señalados como supeditados a la "
                         "crítica. Vuelve a Investigar / Lanzar Misión.")}

    # ---- 5) safe delete with vault memory --------------------------------------
    def delete_hypothesis(self, project_id: str, hyp_id: str) -> dict[str, Any]:
        h = self.store.get(hyp_id)
        if not h:
            return {"ok": False, "error": "hypothesis not found"}
        deps = self._deps(project_id, hyp_id)
        # 1) archive a memory note to the vault BEFORE deleting anything
        archived = self._archive_to_vault(project_id, h, deps)
        # 2) delete dependents (saved experiments become orphans instead)
        deleted = {"hypothesis": 1}
        kept_orphans = []
        for kind, items in deps.items():
            n = 0
            for x in items:
                if kind == "experiment" and x.get("saved"):
                    self.store.update_payload(x["id"], {
                        "hyp_id": "", "orphaned_from": {"hyp_id": hyp_id,
                                                        "tag": h.get("tag", ""),
                                                        "at": now_iso()}})
                    kept_orphans.append(x.get("title", "")[:60])
                    continue
                self.store.delete(x["id"])
                n += 1
            deleted[kind] = n
        self.store.delete(hyp_id)
        self.ledger.record_event(
            project_id, ProvenanceAction.UPDATE, "human",
            f"hipótesis {h.get('tag')} BORRADA (archivada en vault)"[:150],
            {"deleted": deleted}, entity_id=hyp_id)
        return {"ok": True, "deleted": deleted, "kept_orphans": kept_orphans,
                "vault_note": archived}

    def _archive_to_vault(self, project_id: str, h: dict[str, Any],
                          deps: dict[str, list[dict[str, Any]]]) -> str:
        try:
            from .obsidian_sync import ObsidianExporter, _fm, _safe
            p = self.ledger.get_project(project_id)
            ex = ObsidianExporter()
            d = ex.root / _safe(p.title if p else "proyecto", 60) / "Archivo"
            d.mkdir(parents=True, exist_ok=True)
            exps = deps.get("experiment", [])
            lits = deps.get("literature", [])
            crits = deps.get("critique", [])
            out = _fm({"type": "archivo", "tag": h.get("tag", ""),
                       "deleted_at": now_iso(), "version": h.get("version", 1)})
            out += (f"# 🗑 ARCHIVO: {h.get('tag','')} — {h.get('title','')}\n\n"
                    "> Esta hipótesis fue BORRADA, pero el vault recuerda qué se "
                    "hizo y qué pasó, para no repetir el camino.\n\n"
                    f"**Pregunta detonante:** {h.get('trigger_question','')}\n\n"
                    f"**Estado al borrar:** v{h.get('version',1)}, "
                    f"lit={h.get('lit_count',0)} papers, "
                    f"{len(exps)} experimentos, {len(crits)} críticas.\n\n")
            conf = h.get("confrontation") or {}
            if conf.get("stance"):
                out += f"**Postura de la literatura:** {conf['stance']}\n\n"
            if exps:
                out += "## Experimentos y qué pasó\n\n"
                for e in exps:
                    r = e.get("result") or {}
                    out += (f"- {e.get('title','')} [{e.get('status','')}] "
                            f"{r.get('verdict','')}: "
                            f"{str(r.get('verdict_reason',''))[:150]}\n")
                out += "\n"
            if lits:
                out += "## Literatura que se leyó\n\n"
                out += "".join(f"- {x.get('title','')} ({x.get('doi','')})\n"
                               for x in lits[:12]) + "\n"
            latest = max(crits, key=lambda c: c.get("created_at") or "", default=None)
            if latest:
                out += (f"## Última palabra de Aristóteles\n\n{latest.get('verdict','')}: "
                        f"{latest.get('summary','')}\n")
            fname = f"{_safe(h.get('tag','H'))} {_safe(h.get('title',''))[:50]}.md"
            (d / fname).write_text(out, encoding="utf-8")
            return str(d / fname)
        except Exception:  # noqa: BLE001 - archiving is best-effort
            return ""

    # ---- 6) save / anchor experiments ------------------------------------------
    def save_experiment(self, exp_id: str) -> dict[str, Any]:
        e = self.store.get(exp_id)
        if not e:
            return {"ok": False, "error": "experiment not found"}
        self.store.update_payload(exp_id, {"saved": True})
        return {"ok": True, "note": "Guardado: sobrevivirá aunque borres su hipótesis."}

    def anchor_experiment(self, project_id: str, exp_id: str, hyp_id: str
                          ) -> dict[str, Any]:
        e = self.store.get(exp_id)
        h = self.store.get(hyp_id)
        if not e or not h:
            return {"ok": False, "error": "experimento o hipótesis no encontrados"}
        self.store.update_payload(exp_id, {
            "hyp_id": hyp_id, "hyp_tag": h.get("tag", ""),
            "anchored": {"at": now_iso(), "from": e.get("orphaned_from")}})
        # the receiving hypothesis' flow must ABSORB the experiment's evidence
        from .synthesis import synthesize_hypothesis
        syn = synthesize_hypothesis(project_id, hyp_id, self._sf, use_ai=False)
        return {"ok": True, "anchored_to": h.get("tag"),
                "synthesis": syn.get("summary", "")[:200]}

    def orphan_experiments(self, project_id: str) -> list[dict[str, Any]]:
        return [e for e in self.store.list_objects(project_id, kind="experiment")
                if not e.get("hyp_id")]

    # ---- 0d) trace: the full story of one hypothesis as a flow -------------------
    def trace(self, project_id: str, hyp_id: str) -> dict[str, Any]:
        h = self.store.get(hyp_id)
        if not h:
            return {"ok": False, "error": "hypothesis not found"}
        deps = self._deps(project_id, hyp_id)
        nodes: list[dict[str, Any]] = []

        def add(ts: str, ntype: str, icon: str, title: str, summary: str,
                link: str = "", ref: str = "") -> None:
            nodes.append({"ts": ts or "", "type": ntype, "icon": icon,
                          "title": title[:120], "summary": summary[:260],
                          "link": link, "ref": ref})

        origin = ("🔥 nacida de anomalía" if h.get("origin") == "anomaly"
                  else "generada")
        prov = h.get("anomaly_provenance") or {}
        add(h.get("created_at", ""), "created", "🧪",
            f"{h.get('tag','')} creada ({origin})",
            prov.get("anomaly") or h.get("trigger_question", ""), "hipotesis")
        if h.get("approval_reason"):
            add(h.get("created_at", ""), "approved", "✅", "Aprobada por el humano",
                h.get("approval_reason", ""), "hipotesis")
        for v in (h.get("history") or []):
            why = v.get("reason") or "se tomó la hipótesis mejorada por la evidencia"
            add(v.get("archived_at", ""), "version", "⤴",
                f"v{v.get('version')} → v{int(v.get('version', 1)) + 1}",
                f"{why}. Antes: «{str(v.get('title',''))[:90]}»", "hipotesis")
        conf = h.get("confrontation") or {}
        if conf:
            add(h.get("new_evidence_at") or h.get("created_at", ""), "literature",
                "📚", f"Literatura investigada ({h.get('lit_count',0)} papers)",
                f"query «{conf.get('query_used','')}» → postura "
                f"{conf.get('stance','')}", "literatura")
        for m in deps["mission"]:
            steps = ", ".join(f"{s['name']}:{s['status']}" for s in m.get("steps", []))
            add(m.get("created_at", ""), "mission", "🚀",
                f"Misión {m.get('status','')}", steps, "literatura", m.get("id", ""))
        for e in sorted(deps["experiment"], key=lambda x: x.get("created_at") or ""):
            r = e.get("result") or {}
            via = " (vía misión)" if str(e.get("via", "")).startswith("mission") else \
                  (" (de crítica de Aristóteles)" if e.get("from_critique") else "")
            add(e.get("created_at", ""), "experiment", "⚗️",
                f"Experimento{via}: {e.get('title','')}",
                f"[{e.get('status','')}] {r.get('verdict','')} "
                f"{str(r.get('verdict_reason',''))[:140]}", "experimentos",
                e.get("id", ""))
        for c in sorted(deps["critique"], key=lambda x: x.get("created_at") or ""):
            add(c.get("created_at", ""), "critique", "🧐",
                f"Aristóteles ({c.get('task','')}): {c.get('verdict','')}",
                c.get("summary", ""), "", c.get("id", ""))
        for s in sorted(deps["synthesis"], key=lambda x: x.get("created_at") or ""):
            add(s.get("created_at", ""), "synthesis", "🧠", "Síntesis → conocimiento",
                s.get("summary", ""), "conclusiones")
        for d in deps["dossier"]:
            add(d.get("updated_at", ""), "dossier", "📄",
                f"Dossier {d.get('status','')}", d.get("readiness", ""), "conclusiones")
        # children: hypotheses born from THIS hypothesis' experiments (anomalies)
        exp_ids = {e["id"] for e in deps["experiment"]}
        for child in self.store.list_objects(project_id, kind="candidate"):
            ap = child.get("anomaly_provenance") or {}
            if ap.get("exp_id") in exp_ids:
                add(child.get("created_at", ""), "child", "🔥",
                    f"Nueva hipótesis {child.get('tag','')} nacida de una anomalía",
                    f"«{str(child.get('title',''))[:100]}» ← {str(ap.get('anomaly',''))[:80]}",
                    "hipotesis", child.get("id", ""))
        nodes.sort(key=lambda n: n["ts"])
        return {"ok": True, "tag": h.get("tag"), "title": h.get("title", ""),
                "version": int(h.get("version", 1)), "nodes": nodes}

    # ---- 0e) active processes ----------------------------------------------------
    def active_processes(self) -> dict[str, Any]:
        from .missions import MissionEngine
        from .parallel_runs import _LOCK, _RUNS
        eng = MissionEngine(self._sf)
        missions = []
        for p in self.ledger.list_projects():
            for m in eng.list_missions(p.id):
                if m.get("status") not in ("RUNNING", "PENDING"):
                    continue
                hyp = self.store.get(m.get("hyp_id", "")) or {}
                missions.append({
                    "mission_id": m["id"], "project": p.title[:50],
                    "hyp_tag": m.get("hyp_tag", ""), "hyp_id": m.get("hyp_id", ""),
                    "hyp_version": int(hyp.get("version", 1)),
                    "status": m.get("status"),
                    "steps": [{"name": s["name"], "status": s["status"]}
                              for s in m.get("steps", [])]})
        with _LOCK:
            runs = [{"id": r["id"], "kind": r["kind"], "status": r["status"],
                     "done": r["done"], "total": r["total"],
                     "items": [{"label": i["label"], "status": i["status"]}
                               for i in r["items"]]}
                    for r in _RUNS.values() if r["status"] == "RUNNING"]
        return {"missions": missions, "runs": runs, "at": now_iso()}
