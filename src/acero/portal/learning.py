"""Learning Mode — a Socratic tutor that takes you from a GENERAL topic down to the
research FRONTIER, tracking a NESTED TREE of the concepts you drilled into.

Each concept is a node with a parent; drilling into a subtopic creates a child,
and you navigate back up by revisiting an ancestor node — so the left panel shows
the exact thread of how you deepened. Every turn also feeds a CANVAS (formulas,
a diagram, key terms, connections) and an honest FRONTIER assessment: when a
question nears an open problem with no settled answer, the tutor flags it so it
can be promoted into a real ACERO investigation — closing learning → discovery.

The tutor's prose is guidance, never evidence; the frontier flag is a heuristic
starting point, and the research pipeline still does the real novelty check.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.config import repo_root
from ..core.ids import new_id

LEARN_TURN_SCHEMA = {
    "type": "object",
    "properties": {
        "explanation": {"type": "string"},          # markdown, leveled to the depth
        "formulas": {"type": "array", "items": {
            "type": "object",
            "properties": {"latex": {"type": "string"}, "caption": {"type": "string"}},
            "required": ["latex", "caption"], "additionalProperties": False}},
        "diagram_svg": {"type": "string"},            # inline SVG (LLM-drawn) or ""
        "key_terms": {"type": "array", "items": {
            "type": "object",
            "properties": {"term": {"type": "string"}, "definition": {"type": "string"}},
            "required": ["term", "definition"], "additionalProperties": False}},
        "connections": {"type": "array", "items": {"type": "string"}},
        "subtopics": {"type": "array", "items": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "hook": {"type": "string"}},
            "required": ["title", "hook"], "additionalProperties": False}},
        "frontier": {
            "type": "object",
            "properties": {
                "near": {"type": "boolean"},
                "score": {"type": "number"},
                "open_question": {"type": "string"},
                "why": {"type": "string"}},
            "required": ["near", "score", "open_question", "why"],
            "additionalProperties": False},
        "learner_signal": {                          # what this turn reveals about YOU
            "type": "object",
            "properties": {
                "level": {"type": "string"},          # principiante|intermedio|avanzado
                "interests": {"type": "array", "items": {"type": "string"}}},
            "required": ["level", "interests"],
            "additionalProperties": False},
    },
    # Codex structured output requires EVERY property key in `required`; the tutor
    # fills unused ones with empty arrays/strings.
    "required": ["explanation", "formulas", "diagram_svg", "key_terms",
                 "connections", "subtopics", "frontier", "learner_signal"],
    "additionalProperties": False,
}

_SYS = (
    "Eres un TUTOR de clase mundial en ACERO, modo LEARNING. Llevas al estudiante "
    "de un tema general hacia la FRONTERA del conocimiento, de forma socrática y "
    "clarísima, en ESPAÑOL. Adapta la PROFUNDIDAD al camino recorrido (ruta más "
    "larga ⇒ nivel más avanzado, menos básico). Reglas:\n"
    "- explanation: explica el punto actual con rigor pero didáctico (markdown corto).\n"
    "- formulas: fórmulas CLAVE en LaTeX VÁLIDO para KaTeX (sin $, sin \\text raro), "
    "cada una con caption de qué significa. Prefiere pocas y esenciales, bien escritas.\n"
    "- diagram_svg: DIBUJA un diagrama en SVG INLINE que ilustre el concepto — como una "
    "imagen. Requisitos: empieza con <svg viewBox=\"0 0 400 260\" ...>, SIN ancho/alto "
    "fijos, fondo transparente, texto legible (fill #e6edf3, font-size 12-14), trazos y "
    "cajas claras (stroke #8ab4f8, fill de cajas #1c2333), flechas con marker. Etiqueta "
    "todo en español. NADA de <script>. Si de verdad no aplica, cadena vacía.\n"
    "- key_terms: 2-5 términos con definición breve.\n"
    "- connections: teorías/ideas con las que conecta (para el lienzo).\n"
    "- subtopics: 3-5 conceptos MÁS PROFUNDOS en los que se puede ahondar desde aquí.\n"
    "- frontier: evalúa HONESTAMENTE si la pregunta actual está cerca de un PROBLEMA "
    "ABIERTO sin respuesta asentada. near=true y score alto SOLO si de verdad roza "
    "algo no resuelto; da la open_question concreta y por qué es abierta. Si es "
    "material asentado, near=false y score bajo. No inventes fronteras.\n"
    "- learner_signal: infiere del MENSAJE del estudiante su nivel "
    "(principiante|intermedio|avanzado) y 1-4 etiquetas de interés temático. Esto "
    "alimenta su PERFIL para personalizar futuras lecciones.\n"
    "Si te doy un PERFIL del estudiante, ÚSALO: ajusta la profundidad a su nivel, "
    "conecta con sus intereses recurrentes, y guíalo hacia lo que aún no domina."
)


# --- session storage (nested concept tree + per-node messages) ----------------

def learning_root() -> Path:
    env = os.environ.get("ACERO_LEARNING_ROOT", "").strip()
    return Path(env) if env else repo_root() / "acero_data" / "learning"


def _sdir(sid: str) -> Path:
    d = learning_root() / sid
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load(sid: str) -> dict[str, Any]:
    f = _sdir(sid) / "tree.json"
    if not f.exists():
        raise KeyError(f"learning session {sid} not found")
    return json.loads(f.read_text(encoding="utf-8"))


def _save(sid: str, data: dict[str, Any]) -> None:
    (_sdir(sid) / "tree.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _path_titles(tree: dict[str, Any], node_id: str) -> list[str]:
    """Breadcrumb from root to node (list of concept titles)."""
    nodes = tree["nodes"]
    chain, cur = [], node_id
    seen = set()
    while cur and cur in nodes and cur not in seen:
        seen.add(cur)
        chain.append(nodes[cur]["title"])
        cur = nodes[cur].get("parent")
    return list(reversed(chain))


def list_sessions() -> list[dict[str, Any]]:
    """All learning sessions (newest first) so you can resume any of them."""
    root = learning_root()
    if not root.exists():
        return []
    out: list[dict[str, Any]] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not d.name.startswith("lsess"):
            continue
        f = d / "tree.json"
        if not f.exists():
            continue
        try:
            t = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        nodes = t.get("nodes", {})
        last = max([str(n.get("created_at", "")) for n in nodes.values()]
                   + [str(t.get("created_at", ""))])
        out.append({"session_id": t.get("id", d.name), "topic": t.get("topic", ""),
                    "nodes": len(nodes), "last_activity": last})
    out.sort(key=lambda x: x["last_activity"], reverse=True)
    return out


# --- learner profile (what ACERO learns about YOU, to personalize) ------------

def profile_path() -> Path:
    return learning_root() / "profile.json"


def load_profile() -> dict[str, Any]:
    f = profile_path()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {"interests": {}, "topics": [], "levels": [], "n_questions": 0,
            "n_sessions": 0, "recent_questions": [], "updated_at": None}


def save_profile(p: dict[str, Any]) -> None:
    learning_root().mkdir(parents=True, exist_ok=True)
    profile_path().write_text(json.dumps(p, ensure_ascii=False, indent=2),
                              encoding="utf-8")


def _typical_level(levels: list[str]) -> str:
    if not levels:
        return ""
    from collections import Counter
    return Counter(levels[-12:]).most_common(1)[0][0]


def profile_summary(p: dict[str, Any]) -> str:
    """Compact, human-readable summary fed to the tutor to personalize."""
    if not (p.get("interests") or p.get("topics")):
        return ""
    parts: list[str] = []
    top = sorted(p.get("interests", {}).items(), key=lambda x: -x[1])[:6]
    if top:
        parts.append("intereses: " + ", ".join(t for t, _ in top))
    lvl = _typical_level(p.get("levels", []))
    if lvl:
        parts.append("nivel típico: " + lvl)
    if p.get("topics"):
        parts.append("temas explorados: " + ", ".join(p["topics"][-6:]))
    if p.get("recent_questions"):
        parts.append("suele preguntar: " + " | ".join(p["recent_questions"][-3:]))
    return "; ".join(parts)


def update_profile(*, topic: str | None = None, question: str | None = None,
                   signal: dict[str, Any] | None = None,
                   new_session: bool = False) -> dict[str, Any]:
    """Fold one turn into the learner profile (interests, level, questions)."""
    p = load_profile()
    if new_session:
        p["n_sessions"] = int(p.get("n_sessions", 0)) + 1
        if topic and topic not in p["topics"]:
            p["topics"].append(topic)
    if question:
        p["n_questions"] = int(p.get("n_questions", 0)) + 1
        p["recent_questions"] = (p.get("recent_questions", []) + [str(question)[:120]])[-10:]
    if isinstance(signal, dict):
        for tag in (signal.get("interests") or [])[:6]:
            tag = str(tag)[:40].strip()
            if tag:
                p["interests"][tag] = int(p["interests"].get(tag, 0)) + 1
        lvl = str(signal.get("level") or "").strip().lower()
        if lvl:
            p["levels"] = (p.get("levels", []) + [lvl])[-40:]
    p["updated_at"] = now_iso()
    save_profile(p)
    return p


class LearningTutor:
    """Produces one structured tutor turn. Provider is injectable for tests."""

    def __init__(self, provider: Any = None) -> None:
        self._provider = provider

    def _prov(self) -> Any:
        if self._provider is not None:
            return self._provider
        from ..llm.providers import CodexCliProvider
        return CodexCliProvider(timeout_sec=220)

    def turn(self, title: str, path: list[str], message: str) -> dict[str, Any]:
        prov = self._prov()
        if prov is None or not getattr(prov, "available", lambda: False)():
            return self._fallback(title)
        crumb = " → ".join(path) if path else title
        prof = profile_summary(load_profile())
        prompt = (f"{_SYS}\n\n"
                  + (f"PERFIL DEL ESTUDIANTE (personaliza desde aquí): {prof}\n\n" if prof else "")
                  + f"RUTA DE APRENDIZAJE (de general a específico): {crumb}\n"
                  f"CONCEPTO ACTUAL: {title}\n"
                  f"MENSAJE DEL ESTUDIANTE: {message}\n\nDevuelve el turno.")
        try:
            out = prov.complete_json(prompt, LEARN_TURN_SCHEMA, temperature=0.4)
            return self._normalize(out) if isinstance(out, dict) else self._fallback(title)
        except Exception:  # noqa: BLE001 - never break the lesson
            return self._fallback(title)

    @staticmethod
    def _normalize(out: dict[str, Any]) -> dict[str, Any]:
        fr = out.get("frontier") or {}
        out["frontier"] = {
            "near": bool(fr.get("near")),
            "score": float(fr.get("score") or 0.0),
            "open_question": str(fr.get("open_question") or "")[:400],
            "why": str(fr.get("why") or "")[:400]}
        out["subtopics"] = (out.get("subtopics") or [])[:6]
        out.setdefault("formulas", [])
        out.setdefault("key_terms", [])
        out.setdefault("connections", [])
        out.setdefault("diagram_svg", "")
        sig = out.get("learner_signal") or {}
        out["learner_signal"] = {"level": str(sig.get("level") or "")[:20],
                                 "interests": [str(i)[:40] for i in
                                               (sig.get("interests") or [])[:6]]}
        return out

    @staticmethod
    def _fallback(title: str) -> dict[str, Any]:
        return {"explanation": f"(tutor sin IA disponible) Tema: {title}.",
                "formulas": [], "diagram_svg": "", "key_terms": [],
                "connections": [], "subtopics": [],
                "frontier": {"near": False, "score": 0.0, "open_question": "", "why": ""},
                "learner_signal": {"level": "", "interests": []}}


class LearningEngine:
    def __init__(self, tutor: LearningTutor | None = None) -> None:
        self._tutor = tutor or LearningTutor()

    def _add_node(self, tree: dict[str, Any], title: str, parent: str | None) -> str:
        nid = new_id("lnode")
        depth = 0 if parent is None else tree["nodes"][parent]["depth"] + 1
        tree["nodes"][nid] = {"id": nid, "title": title[:120], "parent": parent,
                              "depth": depth, "created_at": now_iso()}
        tree["order"].append(nid)
        return nid

    def _append_msg(self, sid: str, node_id: str, role: str, text: str,
                    turn: dict[str, Any] | None = None) -> None:
        rec: dict[str, Any] = {"node_id": node_id, "role": role, "text": text,
                               "ts": now_iso()}
        if turn is not None:
            rec["turn"] = turn
        with (_sdir(sid) / "messages.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def start(self, topic: str) -> dict[str, Any]:
        sid = new_id("lsess")
        tree: dict[str, Any] = {"id": sid, "topic": topic[:200], "nodes": {},
                                "order": [], "root": None, "created_at": now_iso()}
        root = self._add_node(tree, topic, None)
        tree["root"] = root
        _save(sid, tree)
        turn = self._tutor.turn(topic, [topic], f"Enséñame sobre {topic} desde lo esencial.")
        self._append_msg(sid, root, "assistant", turn["explanation"], turn)
        update_profile(new_session=True, topic=topic, signal=turn.get("learner_signal"))
        return {"session_id": sid, "node_id": root, "turn": turn}

    def drill(self, sid: str, parent_id: str, subtopic: str) -> dict[str, Any]:
        tree = _load(sid)
        if parent_id not in tree["nodes"]:
            raise KeyError("parent node not found")
        nid = self._add_node(tree, subtopic, parent_id)
        _save(sid, tree)
        path = _path_titles(tree, nid)
        turn = self._tutor.turn(subtopic, path, f"Profundiza en {subtopic}.")
        self._append_msg(sid, nid, "assistant", turn["explanation"], turn)
        update_profile(question=f"profundizar: {subtopic}", signal=turn.get("learner_signal"))
        return {"node_id": nid, "turn": turn}

    def ask(self, sid: str, node_id: str, message: str) -> dict[str, Any]:
        tree = _load(sid)
        node = tree["nodes"].get(node_id)
        if not node:
            raise KeyError("node not found")
        path = _path_titles(tree, node_id)
        self._append_msg(sid, node_id, "user", message)
        turn = self._tutor.turn(node["title"], path, message)
        self._append_msg(sid, node_id, "assistant", turn["explanation"], turn)
        update_profile(question=message, signal=turn.get("learner_signal"))
        return {"node_id": node_id, "turn": turn}

    def get(self, sid: str) -> dict[str, Any]:
        tree = _load(sid)
        msgs = self._messages(sid)
        return {"tree": tree, "messages": msgs}

    @staticmethod
    def _messages(sid: str) -> list[dict[str, Any]]:
        f = _sdir(sid) / "messages.jsonl"
        if not f.exists():
            return []
        out = []
        for ln in f.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(ln))
            except Exception:  # noqa: BLE001
                continue
        return out
