"""Economic Mode engine — dialogue, adversarial critique, promote, resume (offline).
Advisor and NEXUS connector are injected, so no LLM/HTTP call happens."""
from __future__ import annotations

import pytest

from acero.portal.economics import EconomicAdvisor, EconomicEngine, list_sessions


@pytest.fixture(autouse=True)
def _root(tmp_path, monkeypatch):
    monkeypatch.setenv("ACERO_ECON_ROOT", str(tmp_path / "econ"))


class _Conn:
    def __init__(self, avail=True):
        self.avail = avail

    def fetch_snapshot(self):
        if not self.avail:
            return {"available": False, "reason": "no nexus", "expenses_by_category": []}
        return {"available": True, "source": "test", "currency": "MXN",
                "income": 50000, "expenses": 32000, "net": 18000,
                "expenses_by_category": [{"category": "renta", "amount": 12000}],
                "accounts": [{"name": "BBVA", "balance": 15000}]}


class _Advisor(EconomicAdvisor):
    def turn(self, snapshot, goal, message):
        return {"analysis": f"neto={snapshot.get('net')} meta={goal}",
                "insights": ["gastas 24% en renta"], "spend_strategy": ["recorta suscripciones"],
                "growth_ideas": [{"title": "vender skill X", "hook": "demanda alta",
                                  "expected_effect": "+5k/mes"}],
                "risks": ["ingreso variable"], "questions": ["¿cuánto puedes reinvertir?"],
                "canvas_svg": "<svg viewBox='0 0 10 10'></svg>",
                "health": {"score": 0.6, "reason": "neto positivo"}}

    def critique(self, snapshot, idea):
        viable = "sólida" in idea
        return {"verdict": "viable" if viable else "needs_work",
                "why": "cuadra con el flujo" if viable else "falta validar costo",
                "fixes": [] if viable else ["estima costo inicial"],
                "viability_score": 0.8 if viable else 0.4}


def _eng(avail=True):
    return EconomicEngine(advisor=_Advisor(), connector=_Conn(avail))


def test_start_grounds_on_nexus_snapshot():
    out = _eng().start("crecer 20% en 6 meses")
    assert out["session_id"].startswith("esess")
    assert out["snapshot"]["net"] == 18000
    assert "neto=18000" in out["turn"]["analysis"]
    assert out["turn"]["growth_ideas"][0]["title"] == "vender skill X"


def test_start_without_nexus_data_does_not_fabricate():
    out = _eng(avail=False).start("meta")
    assert out["snapshot"]["available"] is False       # honest emptiness


def test_ask_and_get_persist():
    eng = _eng()
    s = eng.start("meta")
    eng.ask(s["session_id"], "¿en qué recorto?")
    g = eng.get(s["session_id"])
    roles = [m["role"] for m in g["messages"]]
    assert "user" in roles and roles.count("assistant") >= 2


def test_critique_loop_questions_ideas():
    eng = _eng()
    s = eng.start("meta")
    weak = eng.critique(s["session_id"], "montar un negocio")
    strong = eng.critique(s["session_id"], "idea sólida con números")
    assert weak["verdict"]["verdict"] == "needs_work"
    assert strong["verdict"]["verdict"] == "viable"
    assert len(eng.get(s["session_id"])["critiques"]) == 2


def test_promote_saves_project():
    eng = _eng()
    s = eng.start("meta")
    p = eng.promote(s["session_id"], "vender skill X")
    assert p["ok"] and p["project"]["id"].startswith("eproj")
    assert len(eng.get(s["session_id"])["projects"]) == 1


def test_list_sessions():
    eng = _eng()
    eng.start("meta A")
    eng.start("meta B")
    assert len(list_sessions()) == 2


def test_get_unknown_raises():
    with pytest.raises(KeyError):
        _eng().get("esess_nope")
