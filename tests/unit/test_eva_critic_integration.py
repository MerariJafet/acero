"""OP-A: EVA feeds Aristóteles (no duplicate re-derivation; objections trace to EVA).
OP-B: 'considerar crítica' reformulates the hypothesis, it doesn't just bump a version."""

from __future__ import annotations

from acero.epistemic.vulnerability import VulnerabilityType
from acero.portal.critic import CriticAgent
from acero.portal.epistemic_bridge import eva_for_hypothesis
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow
from acero.portal.lifecycle import Lifecycle
from acero.ledger.service import ResearchLedger

H = {"id": "h0", "tag": "H0", "title": "El valle depende de [Fe/H] tras condicionar insolación",
     "argument": "la insolación gobierna la fotoevaporación", "doubt": "si persiste sin condicionar falla"}


def test_eva_for_hypothesis_is_the_shared_surface():
    vulns = eva_for_hypothesis(H)                 # heuristic, offline
    assert vulns and all("id" in v and "decisive_test" in v for v in vulns)
    # with exposure/outcome (llm) the confounding vulnerability appears
    def llm(h):
        return {"exposure_or_input": "[Fe/H]", "outcome_or_prediction": "valle",
                "assumptions": ["insolación fija"]}, "llm"
    types = {v["type"] for v in eva_for_hypothesis(H, extractor=llm)}
    assert VulnerabilityType.CONFOUNDING.value in types


def test_critique_attaches_eva_vulnerability_ids(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Vida", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    c = CriticAgent(session_factory).critique_now(
        p.id, h["id"], "hipotesis", "revisa esta hipótesis", use_ai=False)
    # the critique now carries the EVA vulnerability ids it was handed (traceability)
    assert "eva_vulnerability_ids" in c
    assert c["eva_vulnerability_ids"]             # non-empty for a hypothesis target


def test_consider_critique_reformulates_and_degrades_gracefully(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Vida", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    fl = HypothesisFlow(session_factory)
    fl.set_status(p.id, h["id"], "APPROVED", "x")
    c = CriticAgent(session_factory).critique_now(
        p.id, h["id"], "hipotesis", "ctx", use_ai=False)
    # give the critique an objection so reformulation has something to address
    fl.store.update_payload(c["id"], {"objections": ["no descarta el sesgo de selección"],
                                      "summary": "sobredimensionada"})
    lc = Lifecycle(session_factory)
    out = lc.consider_critique(p.id, c["id"])
    assert out["ok"] and out["version"] == 2
    # offline (no Codex) reformulation degrades to {} but the flow still advances honestly
    assert "reformulated" in out
    hyp = fl.store.get(h["id"])
    assert int(hyp["version"]) == 2 and hyp["history"]      # old text preserved
