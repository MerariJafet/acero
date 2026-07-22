"""El Revisor — resident critic agent (offline: deterministic fallback only)."""

from __future__ import annotations

from acero.portal.critic import CriticAgent, critique_async
from acero.portal.hypotheses import HypothesisService


def test_critique_now_offline_persists_and_is_honest(session_factory, project):
    ag = CriticAgent(session_factory)
    rec = ag.critique_now(project.id, "hyp_x", "hipotesis",
                          "Hipótesis: el patrón es señal real", use_ai=False)
    assert rec["provider"] == "none"
    assert rec["verdict"] == "sin_revision"          # never fakes an AI review
    assert rec["target_id"] == "hyp_x"
    assert "falsaría" in rec["summary"]
    stored = ag.store.list_objects(project.id, kind="critique")
    assert len(stored) == 1 and stored[0]["id"] == rec["id"]


def test_latest_by_target_picks_newest(session_factory, project):
    ag = CriticAgent(session_factory)
    a = ag.critique_now(project.id, "t1", "hipotesis", "v1", use_ai=False)
    b = ag.critique_now(project.id, "t1", "literatura", "v2", use_ai=False)
    ag.critique_now(project.id, "t2", "hipotesis", "x", use_ai=False)
    latest = ag.latest_by_target(project.id)
    assert set(latest) == {"t1", "t2"}
    assert latest["t1"]["id"] in {a["id"], b["id"]}
    assert latest["t1"]["created_at"] >= a["created_at"]


def test_critique_async_disabled_in_tests(session_factory, project, monkeypatch):
    # conftest sets ACERO_CRITIC_DISABLED=1 — async trigger must be a no-op
    critique_async(project.id, "t9", "hipotesis", "ctx", session_factory)
    ag = CriticAgent(session_factory)
    assert ag.latest_by_target(project.id) == {}


def test_generate_hypotheses_does_not_break_with_critic_wired(session_factory, project):
    out = HypothesisService(session_factory).generate(project.id, use_ai=False)
    assert out["ok"] is True and out["created"]


def test_literature_context_prefers_abstracts(session_factory, project):
    ag = CriticAgent(session_factory)
    ag.store.put(project.id, "literature", "lit_a",
                 {"id": "lit_a", "title": "Paper con abstract", "abstract": "contenido",
                  "relevance": 9.0}, status="INDEXED", actor="t", summary="a")
    ag.store.put(project.id, "literature", "lit_b",
                 {"id": "lit_b", "title": "Paper sin abstract"},
                 status="INDEXED", actor="t", summary="b")
    ctx = ag._literature_context(project.id)
    assert "Paper con abstract" in ctx and "Paper sin abstract" not in ctx
