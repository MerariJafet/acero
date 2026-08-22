"""Hypothesis-centric flow: approve → literature → experiments (offline)."""

from __future__ import annotations

import pytest

from acero.ledger.service import ResearchLedger
from acero.portal.hypotheses import HypothesisService
from acero.portal.hypothesis_flow import HypothesisFlow


@pytest.fixture()
def setup(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Flow", domain="astronomy")
    h = HypothesisService(session_factory).generate(p.id, use_ai=False)["created"][0]
    return session_factory, p.id, h


def test_approve_requires_reason(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    assert fl.set_status(pid, h["id"], "APPROVED")["ok"] is False
    assert fl.set_status(pid, h["id"], "APPROVED", "cuestiona la nula")["ok"] is True
    assert len(fl.approved(pid)) == 1


def test_reject_and_unapprove(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    fl.set_status(pid, h["id"], "APPROVED", "x")
    fl.set_status(pid, h["id"], "PROPOSED")
    assert len(fl.approved(pid)) == 0


# --- gate de duplicados en la aprobación (incidente 2026-08-22) --------------
# 197 de 224 misiones en cola resultaron ser la MISMA hipótesis con hyp_id
# distinto, aprobada dos veces por caminos distintos (Bohr adoptando del
# backlog, el PI generando encima). El gate de diversidad existía en
# discovery/diversity.py pero nada lo llamaba antes de aprobar.

def _candidate(sf, pid, obj_id, title, statement):
    from acero.core.ids import new_id
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    st = DiscoveryStore(sf, ResearchLedger(sf))
    tag = obj_id[-6:]
    st.put(pid, "candidate", obj_id,
           {"id": obj_id, "tag": tag, "title": title, "statement": statement,
            "novelty": {"status": "abierta", "score": 7.5}},
           status="PROPOSED")
    return obj_id


def test_una_hipotesis_casi_identica_a_una_ya_aprobada_se_bloquea(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    assert fl.set_status(pid, h["id"], "APPROVED", "primera")["ok"] is True

    gemela = _candidate(
        sf, pid, "cand_gemela",
        h["title"], h.get("statement", h["title"]))  # texto idéntico → sim=1.0
    r = fl.set_status(pid, "cand_gemela", "APPROVED", "segunda")
    assert r["ok"] is False
    assert r["blocked_by_diversity"] is True
    assert r["duplicate_of"] == h["id"]
    assert len(fl.approved(pid)) == 1          # la gemela NO se coló


def test_force_deja_pasar_una_duplicada_a_proposito(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    fl.set_status(pid, h["id"], "APPROVED", "primera")
    _candidate(sf, pid, "cand_gemela", h["title"], h.get("statement", h["title"]))
    r = fl.set_status(pid, "cand_gemela", "APPROVED", "quiero las dos", force=True)
    assert r["ok"] is True
    assert len(fl.approved(pid)) == 2


def test_una_hipotesis_genuinamente_distinta_no_se_bloquea(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    fl.set_status(pid, h["id"], "APPROVED", "primera")
    _candidate(sf, pid, "cand_otra",
              "Título completamente distinto sobre otro mecanismo",
              "Enunciado sin relación alguna con la hipótesis previa, otro dominio")
    r = fl.set_status(pid, "cand_otra", "APPROVED", "segunda")
    assert r["ok"] is True
    assert len(fl.approved(pid)) == 2


def test_candidatas_sin_texto_comparable_no_se_bloquean_entre_si(setup):
    """Regresión real: el formato viejo del backlog de triaje guarda el
    enunciado en 'claim', no en 'statement'/'title'. Comparar texto ausente
    daba jaccard(vacío, vacío) = 1.0 por convención matemática — bloqueaba
    a ciegas CUALQUIER par de candidatas en ese formato, no solo duplicadas."""
    from acero.core.ids import new_id
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    sf, pid, _ = setup
    st = DiscoveryStore(sf, ResearchLedger(sf))
    fl = HypothesisFlow(sf)
    a, b = new_id("hyp"), new_id("hyp")
    st.put(pid, "candidate", a, {"id": a, "tag": "A", "claim": "vieja"},
          status="PROPOSED")
    st.put(pid, "candidate", b, {"id": b, "tag": "B", "claim": "reciente"},
          status="PROPOSED")
    assert fl.set_status(pid, a, "APPROVED", "primera")["ok"] is True
    r = fl.set_status(pid, b, "APPROVED", "segunda")
    assert r["ok"] is True, r.get("error")
    assert len(fl.approved(pid)) == 2


def test_propose_and_run_experiment_plan_only(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    fl.set_status(pid, h["id"], "APPROVED", "x")
    exps = fl.propose_experiments(pid, h["id"], use_ai=False)["created"]
    assert exps
    run = fl.run_experiment(pid, exps[0]["id"], use_ai=False)
    # a generic proposed experiment has no code to run → reproducible PLAN, not a result
    assert run["mode"] == "plan_only"
    assert "plan" in run and "no es un resultado" in run["note"].lower()


def test_run_experiment_maps_to_real_analysis(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    fl.set_status(pid, h["id"], "APPROVED", "x")
    e = fl.propose_experiments(pid, h["id"], use_ai=False)["created"][0]
    fl.store.update_payload(e["id"], {"data_source": "NASA exoplanet catalog, tercera ley de Kepler"})
    run = fl.run_experiment(pid, e["id"], use_ai=False)
    assert run["mode"] == "real_analysis"
    assert run["result"]["fitted"]["r_squared"] > 0.95


def test_hyp_tag_h0_does_not_trigger_hubble_runner(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    # a hypothesis literally tagged/titled "H0" must NOT match the Hubble runner
    assert fl._real_runner("H0: la señal es ruido") is None


def test_adopt_improved_versions_hypothesis(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    orig = fl.store.get(h["id"])["title"]
    # simulate a confrontation that produced an improved wording
    fl.store.update_payload(h["id"], {"confrontation": {
        "improved_hypothesis": "Versión afinada por la evidencia", "provider": "codex"}})
    res = fl.adopt_improved(pid, h["id"])
    assert res["ok"] is True and res["version"] == 2
    cur = fl.store.get(h["id"])
    assert cur["title"] == "Versión afinada por la evidencia"
    assert cur["version"] == 2
    assert cur["lit_status"] == "STALE"
    # v1 wording is archived in history
    assert cur["history"][0]["version"] == 1 and cur["history"][0]["title"] == orig


def test_adopt_improved_rejects_when_no_improvement(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    assert fl.adopt_improved(pid, h["id"])["ok"] is False  # no confrontation yet
    fl.store.update_payload(h["id"], {"confrontation": {
        "improved_hypothesis": fl.store.get(h["id"])["title"]}})
    # identical wording → nothing to adopt
    assert fl.adopt_improved(pid, h["id"])["ok"] is False


def test_experiments_seed_from_confrontation_ideas(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    fl.set_status(pid, h["id"], "APPROVED", "x")
    fl.store.update_payload(h["id"], {"confrontation": {"experiment_ideas": [
        {"title": "Bajar curvas de luz de MAST", "approach": "descargar y ajustar",
         "data_source": "MAST TESS", "method_type": "download_data",
         "feasible_local": True}]}})
    created = fl.propose_experiments(pid, h["id"], use_ai=False)["created"]
    assert created
    assert created[0]["title"] == "Bajar curvas de luz de MAST"
    assert created[0]["method_type"] == "download_data"


def test_kepler_mission_experiment_not_hijacked_by_third_law_runner(setup):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    # a Kepler-MISSION experiment (radius valley) must NOT trigger the third-law study
    assert fl._real_runner("Kepler DR25 radius valley completeness KOI table") is None
    assert fl._real_runner("Kepler vs TESS radius valley depth") is None
    # a genuine third-law experiment still routes to the study
    assert fl._real_runner("verificar la tercera ley de kepler") is not None


# --- recorte de contexto en la confrontación de literatura (2026-08-22) -------
# Se pegaban hasta 10 papers con hasta 1600 chars de fulltext cada uno —
# ~4-5K tokens por hipótesis, muchos de papers poco relevantes. El recorte
# NO debe cambiar la corrección del mapeo citation_idx → paper citado.

def _paper(i, *, relevance, abstract_len=50):
    return {"id": f"lit_{i}", "title": f"Paper {i}", "doi": f"10.doi/{i}",
           "source": "test", "integrity": "ok", "relevance": relevance,
           "abstract": "X" * abstract_len, "url": "", "authors": []}


class _FakeConfrontProvider:
    def __init__(self, out):
        self.out = out
        self.last_prompt = None

    def available(self):
        return True

    def complete_json(self, prompt, schema, *, temperature=0.0):
        self.last_prompt = prompt
        return self.out


def test_confront_manda_solo_los_papers_mas_relevantes(setup, monkeypatch):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    papers = [_paper(i, relevance=1.0 - i * 0.1) for i in range(10)]  # 0 es el más relevante
    fake = _FakeConfrontProvider({"stance": "mixed", "argument_for": "", "argument_against": "",
                                  "improved_hypothesis": "", "citation_idx": [0],
                                  "experiment_ideas": []})
    monkeypatch.setattr("acero.llm.providers.CodexCliProvider", lambda **kw: fake)
    fl._confront(h, papers, use_ai=True)
    assert fake.last_prompt is not None
    # los 5 más relevantes (0..4) SÍ están; los menos relevantes (8, 9) NO
    assert "Paper 0" in fake.last_prompt and "Paper 4" in fake.last_prompt
    assert "Paper 8" not in fake.last_prompt and "Paper 9" not in fake.last_prompt


def test_confront_recorta_el_abstract_largo(setup, monkeypatch):
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    papers = [_paper(0, relevance=1.0, abstract_len=2000)]
    fake = _FakeConfrontProvider({"stance": "mixed", "argument_for": "", "argument_against": "",
                                  "improved_hypothesis": "", "citation_idx": [],
                                  "experiment_ideas": []})
    monkeypatch.setattr("acero.llm.providers.CodexCliProvider", lambda **kw: fake)
    fl._confront(h, papers, use_ai=True)
    # el abstract de 2000 'X' no debe aparecer completo — se recortó a ~400
    assert "X" * 2000 not in fake.last_prompt
    assert "X" * 400 in fake.last_prompt


def test_confront_citation_idx_sigue_apuntando_al_paper_correcto(setup, monkeypatch):
    """El índice que el LLM devuelve en citation_idx es sobre la lista YA
    recortada — trimear después de responder rompería la correspondencia."""
    sf, pid, h = setup
    fl = HypothesisFlow(sf)
    papers = [_paper(i, relevance=1.0 - i * 0.1) for i in range(10)]
    fake = _FakeConfrontProvider({"stance": "supports", "argument_for": "x",
                                  "argument_against": "", "improved_hypothesis": "",
                                  "citation_idx": [2], "experiment_ideas": []})
    monkeypatch.setattr("acero.llm.providers.CodexCliProvider", lambda **kw: fake)
    out = fl._confront(h, papers, use_ai=True)
    assert out["citations"][0]["title"] == "Paper 2"     # el 3ro más relevante, no el 3ro original
