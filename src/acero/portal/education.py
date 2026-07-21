"""Educational plans + LMS courses linked to investigations.

- build_edu_plan: genera un plan de estudio (índice de temas con toggles) a partir del
  estado REAL del proyecto (fases, literatura, currículo del dominio). Usa Codex con
  esquema JSON; si no está disponible, cae a un plan determinista (sin IA fingida).
- generate_course: convierte los temas SELECCIONADOS en un curso LMS (módulos →
  lecciones con texto, quiz, links a papers reales del proyecto). Persistido y
  vinculado a la investigación.
- sync_course: si la investigación creció (ángulos/temas no cubiertos), agrega temas.

Los cursos EXPLICAN la investigación; nunca afirman descubrimientos.
"""

from __future__ import annotations

from typing import Any

from ..core.clock import now_iso
from ..core.ids import new_id
from ..discovery.store import DiscoveryStore
from ..ledger.db import default_session_factory
from ..ledger.service import ResearchLedger

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "topics": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "title": {"type": "string"},
                "why": {"type": "string"},
                "concepts": {"type": "array", "items": {"type": "string"}},
                "level": {"type": "string"},
            },
            "required": ["id", "title", "why", "concepts", "level"],
            "additionalProperties": False}},
    },
    "required": ["title", "topics"],
    "additionalProperties": False,
}

COURSE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "modules": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "lessons": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "quiz_question": {"type": "string"},
                        "quiz_options": {"type": "array", "items": {"type": "string"}},
                        "quiz_answer_idx": {"type": "integer"},
                    },
                    "required": ["title", "body", "quiz_question", "quiz_options",
                                 "quiz_answer_idx"],
                    "additionalProperties": False}},
            },
            "required": ["title", "lessons"],
            "additionalProperties": False}},
    },
    "required": ["title", "modules"],
    "additionalProperties": False,
}


class EducationService:
    def __init__(self, session_factory: Any | None = None) -> None:
        self._sf = session_factory or default_session_factory()
        self.ledger = ResearchLedger(self._sf)
        self.store = DiscoveryStore(self._sf, self.ledger)

    # ------------------------------------------------------------------ plan
    def _project_grounding(self, project_id: str) -> dict[str, Any]:
        from .phases import build_phases
        ph = build_phases(project_id, self._sf) or {}
        lit = self.store.list_objects(project_id, kind="literature")
        angles = sorted({li.get("angle", "") for li in lit if li.get("angle")})
        return {"phases": ph, "angles": angles,
                "papers": [{"title": li.get("title", ""), "url": li.get("url", ""),
                            "doi": li.get("doi", ""), "angle": li.get("angle", "")}
                           for li in lit]}

    def _deterministic_topics(self, project_id: str, g: dict[str, Any]
                              ) -> list[dict[str, Any]]:
        """Fallback SIN IA: temas desde ángulos reales + currículo del dominio."""
        topics: list[dict[str, Any]] = []
        for a in g["angles"]:
            n = sum(1 for p in g["papers"] if p["angle"] == a)
            topics.append({"id": f"angle_{a}", "title": a.replace("_", " ").title(),
                           "why": f"ángulo real de la investigación ({n} papers indexados)",
                           "concepts": [p["title"][:60] for p in g["papers"]
                                        if p["angle"] == a][:4] or [a],
                           "level": "core"})
        try:
            from ..understanding.curriculum.research_curriculum import requirements_for
            p = self.ledger.get_project(project_id)
            kinds = {"astronomy": ["transit"], "physics": ["sindy"]}.get(
                p.domain if p else "", ["reliability"])
            for kind in kinds:
                for req in requirements_for(kind, project_id)[:6]:
                    topics.append({"id": f"cur_{req.concept}", "title": req.concept,
                                   "why": req.reason_required,
                                   "concepts": [req.concept], "level":
                                   "bloqueante" if req.blocking else "opcional"})
        except Exception:  # noqa: BLE001
            pass
        return topics

    def build_edu_plan(self, project_id: str, *, use_ai: bool = True) -> dict[str, Any]:
        p = self.ledger.get_project(project_id)
        if p is None:
            return {"ok": False, "error": "project not found"}
        g = self._project_grounding(project_id)
        plan: dict[str, Any] | None = None
        provider = "deterministic"
        if use_ai:
            try:
                from ..llm.providers import CodexCliProvider
                prov = CodexCliProvider(timeout_sec=180)
                if prov.available():
                    angles = ", ".join(g["angles"]) or "generales"
                    prompt = (
                        "Diseña un PLAN EDUCATIVO (índice de estudio) para que un humano "
                        f"entienda la investigación «{p.title}» (dominio {p.domain}). "
                        f"Ángulos reales investigados: {angles}. Fases con trabajo: "
                        f"{[x['title'] for x in g['phases'].get('phases', []) if x['state']=='done']}. "
                        "Genera 6-10 temas ordenados de fundamentos a avanzado; cada tema con "
                        "id corto (snake_case), title, why (por qué importa para ESTA "
                        "investigación), concepts (3-5) y level (fundamento|core|avanzado). "
                        "En español. NO afirmes descubrimientos.")
                    plan = prov.complete_json(prompt, PLAN_SCHEMA, temperature=0.2)
                    provider = "codex"
            except Exception:  # noqa: BLE001
                plan = None
        if not plan or not plan.get("topics"):
            plan = {"title": f"Plan de estudio — {p.title}",
                    "topics": self._deterministic_topics(project_id, g)}
            provider = "deterministic"
        for t in plan["topics"]:
            t["enabled"] = True                       # el usuario apaga lo que ya sabe
        pid_obj = new_id("eduplan")
        payload = {"id": pid_obj, "project_id": project_id, "provider": provider,
                   "created_at": now_iso(), "status": "DRAFT", **plan}
        self.store.put(project_id, "edu_plan", pid_obj, payload, status="DRAFT",
                       actor="education", summary=f"plan educativo ({provider})")
        return {"ok": True, "plan": payload,
                "disclaimer": "Plan generado como ayuda didáctica; no es evidencia."}

    def latest_plan(self, project_id: str) -> dict[str, Any] | None:
        plans = self.store.list_objects(project_id, kind="edu_plan")
        plans.sort(key=lambda x: str(x.get("created_at", "")))
        return plans[-1] if plans else None

    # ---------------------------------------------------------------- course
    def _deterministic_lessons(self, topic: dict[str, Any], papers: list[dict[str, Any]]
                               ) -> list[dict[str, Any]]:
        refs = [p for p in papers if p.get("angle", "") in topic["id"]] or papers[:2]
        links = "\n".join(f"- {r['title'][:70]}: {r['url']}" for r in refs[:3])
        body = (f"{topic['why']}\n\nConceptos clave: {', '.join(topic['concepts'])}.\n\n"
                f"Lecturas reales de la investigación:\n{links or '- (sin papers aún)'}")
        opts = [topic["concepts"][0] if topic["concepts"] else topic["title"],
                "Un descubrimiento confirmado", "Un dato sin procedencia"]
        return [{"title": f"Introducción a {topic['title']}", "body": body,
                 "quiz_question": f"¿Qué papel juega «{topic['title']}» en esta investigación?",
                 "quiz_options": opts, "quiz_answer_idx": 0}]

    def generate_course(self, project_id: str, *, topic_ids: list[str] | None = None,
                        use_ai: bool = True) -> dict[str, Any]:
        p = self.ledger.get_project(project_id)
        if p is None:
            return {"ok": False, "error": "project not found"}
        plan = self.latest_plan(project_id)
        if not plan:
            gen = self.build_edu_plan(project_id, use_ai=use_ai)
            if not gen.get("ok"):
                return gen
            plan = gen["plan"]
        chosen = [t for t in plan["topics"]
                  if (topic_ids is None and t.get("enabled", True))
                  or (topic_ids is not None and t["id"] in topic_ids)]
        if not chosen:
            return {"ok": False, "error": "no topics selected"}
        g = self._project_grounding(project_id)
        course: dict[str, Any] | None = None
        provider = "deterministic"
        if use_ai:
            try:
                from ..llm.providers import CodexCliProvider
                prov = CodexCliProvider(timeout_sec=240)
                if prov.available():
                    tt = "; ".join(f"{t['title']} ({t['why'][:60]})" for t in chosen[:8])
                    prompt = (
                        f"Crea un CURSO LMS didáctico en español sobre la investigación "
                        f"«{p.title}». Temas seleccionados: {tt}. Un módulo por tema, 1-2 "
                        "lecciones por módulo. Cada lección: title, body (200-350 palabras, "
                        "didáctico, con analogías), quiz_question con 3 quiz_options y "
                        "quiz_answer_idx correcto. Distingue SIEMPRE lo establecido de lo "
                        "abierto; nada es un descubrimiento de esta investigación.")
                    course = prov.complete_json(prompt, COURSE_SCHEMA, temperature=0.3)
                    provider = "codex"
            except Exception:  # noqa: BLE001
                course = None
        if not course or not course.get("modules"):
            course = {"title": f"Curso — {p.title}",
                      "modules": [{"title": t["title"],
                                   "lessons": self._deterministic_lessons(t, g["papers"])}
                                  for t in chosen]}
            provider = "deterministic"
        cid = new_id("course")
        n_lessons = sum(len(m["lessons"]) for m in course["modules"])
        payload = {"id": cid, "project_id": project_id, "project_title": p.title,
                   "provider": provider, "created_at": now_iso(),
                   "topic_ids": [t["id"] for t in chosen],
                   "status": "READY", "progress": {"completed": [], "pct": 0},
                   "n_lessons": n_lessons, **course}
        self.store.put(project_id, "course", cid, payload, status="READY",
                       actor="education", summary=f"curso generado ({provider}, "
                                                  f"{n_lessons} lecciones)")
        return {"ok": True, "course": payload}

    def list_courses(self, project_id: str | None = None) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        projects = ([self.ledger.get_project(project_id)] if project_id
                    else self.ledger.list_projects())
        for p in projects:
            if p is None:
                continue
            for c in self.store.list_objects(p.id, kind="course"):
                out.append(c)
        out.sort(key=lambda c: str(c.get("created_at", "")), reverse=True)
        return out

    def get_course(self, course_id: str) -> dict[str, Any] | None:
        return self.store.get(course_id)

    def mark_lesson(self, course_id: str, lesson_key: str) -> dict[str, Any]:
        c = self.store.get(course_id)
        if not c:
            return {"ok": False, "error": "course not found"}
        prog = c.get("progress") or {"completed": [], "pct": 0}
        if lesson_key not in prog["completed"]:
            prog["completed"].append(lesson_key)
        total = max(1, int(c.get("n_lessons") or 1))
        prog["pct"] = round(100 * len(prog["completed"]) / total)
        status = "COMPLETED" if prog["pct"] >= 100 else c.get("status", "READY")
        self.store.update_payload(course_id, {"progress": prog, "status": status},
                                  status=status)
        return {"ok": True, "progress": prog, "status": status}

    def sync_course(self, course_id: str, *, use_ai: bool = False) -> dict[str, Any]:
        """La investigación creció → agrega módulos para ángulos no cubiertos."""
        c = self.store.get(course_id)
        if not c:
            return {"ok": False, "error": "course not found"}
        project_id = c.get("project_id", "")
        g = self._project_grounding(project_id)
        covered = set(c.get("topic_ids") or [])
        missing = [a for a in g["angles"] if f"angle_{a}" not in covered]
        if not missing:
            return {"ok": True, "added": 0, "note": "curso al día con la investigación"}
        added = 0
        modules = list(c.get("modules") or [])
        topic_ids = list(covered)
        for a in missing:
            topic = {"id": f"angle_{a}", "title": a.replace("_", " ").title(),
                     "why": "nuevo ángulo agregado a la investigación",
                     "concepts": [a], "level": "core"}
            modules.append({"title": topic["title"],
                            "lessons": self._deterministic_lessons(topic, g["papers"])})
            topic_ids.append(topic["id"])
            added += 1
        n_lessons = sum(len(m["lessons"]) for m in modules)
        self.store.update_payload(course_id, {
            "modules": modules, "topic_ids": topic_ids, "n_lessons": n_lessons,
            "status": "READY" if added else c.get("status", "READY")})
        return {"ok": True, "added": added, "n_lessons": n_lessons,
                "note": f"{added} tema(s) nuevos agregados desde la investigación"}
