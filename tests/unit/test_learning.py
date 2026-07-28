"""Learning Mode engine — nested concept tree, tutor turns, frontier flag (offline).
The tutor provider is injected, so no LLM call happens."""
from __future__ import annotations

import pytest

from acero.portal.learning import LearningEngine, LearningTutor


@pytest.fixture(autouse=True)
def _root(tmp_path, monkeypatch):
    monkeypatch.setenv("ACERO_LEARNING_ROOT", str(tmp_path / "learning"))


class _Tutor(LearningTutor):
    """Deterministic tutor: echoes the title, offers one subtopic, flags frontier
    only when the title contains 'frontera'."""

    def turn(self, title, path, message):
        near = "frontera" in title.lower()
        return {
            "explanation": f"Explico {title} (ruta: {' → '.join(path)})",
            "formulas": [{"latex": "E=mc^2", "caption": "energía"}],
            "diagram_mermaid": "", "key_terms": [{"term": title, "definition": "x"}],
            "connections": ["relatividad"],
            "subtopics": [{"title": f"{title} avanzado", "hook": "más profundo"}],
            "frontier": {"near": near, "score": 0.9 if near else 0.1,
                         "open_question": "¿pregunta abierta?" if near else "",
                         "why": "no resuelto" if near else ""},
        }


def _engine():
    return LearningEngine(tutor=_Tutor())


def test_start_creates_root_and_first_turn():
    out = _engine().start("Mecánica cuántica")
    assert out["session_id"].startswith("lsess")
    assert out["node_id"].startswith("lnode")
    assert "Mecánica cuántica" in out["turn"]["explanation"]
    assert out["turn"]["frontier"]["near"] is False


def test_drill_creates_child_and_deepens_path():
    eng = _engine()
    s = eng.start("Átomo")
    child = eng.drill(s["session_id"], s["node_id"], "Electrón")
    # the child's turn shows the full breadcrumb (Átomo → Electrón)
    assert "Átomo → Electrón" in child["turn"]["explanation"]
    tree = eng.get(s["session_id"])["tree"]
    node = tree["nodes"][child["node_id"]]
    assert node["parent"] == s["node_id"] and node["depth"] == 1


def test_ask_keeps_node_and_records_messages():
    eng = _engine()
    s = eng.start("Física")
    eng.ask(s["session_id"], s["node_id"], "¿qué es la masa?")
    msgs = eng.get(s["session_id"])["messages"]
    roles = [m["role"] for m in msgs]
    assert "user" in roles and roles.count("assistant") >= 2   # start + ask


def test_frontier_flag_surfaces_open_question():
    eng = _engine()
    s = eng.start("Gravedad cuántica (frontera)")
    fr = s["turn"]["frontier"]
    assert fr["near"] is True and fr["score"] >= 0.5 and fr["open_question"]


def test_get_unknown_session_raises():
    with pytest.raises(KeyError):
        _engine().get("lsess_nope")


def test_real_tutor_falls_back_without_provider():
    class _Down:
        def available(self):
            return False
    t = LearningTutor(provider=_Down())
    turn = t.turn("Tema", ["Tema"], "hola")
    assert "sin IA" in turn["explanation"] and turn["frontier"]["near"] is False
