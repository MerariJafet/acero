"""Tests for El Consejo — persona council data + per-project progress."""

from __future__ import annotations

from acero.portal.council import (
    PERSONAS, STAGES, build_flows, build_stories, council_for)


def test_all_personas_placed_in_a_stage():
    placed = {pid for st in STAGES for pid in st["ids"]}
    assert placed == {p["id"] for p in PERSONAS}
    assert len(PERSONAS) == 18    # +Ramanujan +Turing +Noether +Mendeleev


def test_empty_project_starts_at_zero_progress():
    """A brand-new investigation where NOBODY has worked yet must read 0% — the ring is
    real project work, not the module's capability maturity."""
    c = council_for({})
    assert len(c["personas"]) == 18
    assert all(p["progress"] == 0 for p in c["personas"])       # nada hecho → 0%
    assert all(p["source"] == "idle" for p in c["personas"])
    assert all(ph["progress"] == 0 for ph in c["phases"])       # fases también en 0
    assert c["overall"] == 0


def test_real_kpis_drive_project_signal():
    c = council_for({"hypotheses": 6, "experiments": 5, "approved": 3, "dossiers": 1})
    prog = {p["id"]: p for p in c["personas"]}
    assert prog["davinci"]["source"] == "project"        # experiments → Da Vinci
    assert prog["hilbert"]["source"] == "project"         # hypotheses → Hilbert
    assert prog["davinci"]["progress"] == min(100, 5 * 16)
    assert prog["gauss"]["progress"] == min(100, 1 * 24)
    # a persona with no real work on this project stays at 0 (e.g. nobody reformulated)
    assert prog["feynman"]["progress"] == 0
    assert 0 <= c["overall"] <= 100


def test_verdicts_pass_through_capped():
    v = [{"title": f"h{i}", "verdict": "verified", "status": "good"} for i in range(9)]
    c = council_for({"hypotheses": 1}, verdicts=v)
    assert len(c["verdicts"]) == 6


def test_journey_progress_and_next_step():
    """La barra superior: % general por hitos REALES y qué sigue. Proyecto vacío → 0% y
    el siguiente paso es plantear la conjetura; con trabajo, avanza y nunca llega a 100
    sin la validación externa HUMANA (5% que ACERO no puede marcarse solo)."""
    c0 = council_for({})
    assert c0["journey"]["pct"] == 0
    assert "Conjetura" in c0["journey"]["next_step"]
    items = {"experiment": [{"result": {"verdict": "holds_empirically"}}],
             "literature": [{"title": "p"}], "reformulation": [{"statement": "r"}],
             "lemma": [{"statement": "l", "proved": True}],
             "candidate": [], "critique": [], "dossier": []}
    c1 = council_for({"hypotheses": 1, "experiments": 1, "dossiers": 1}, items=items)
    assert c1["journey"]["pct"] == 95                 # todo menos la validación humana
    assert "HUMANA" in c1["journey"]["next_step"]
    # con el ciclo EN VIVO, "qué sigue" refleja la etapa actual
    c2 = council_for({"hypotheses": 1},
                     live={"done": False, "label": "Popper busca contraejemplos"})
    assert c2["journey"]["next_step"].startswith("en curso: Popper")


def test_build_flows_tracks_who_did_what_in_order():
    """El riel: por cada H, la cadena cronológica de personajes (ids ULID ⇒ orden por id),
    quién la tiene AHORA, de dónde VIENE y a quién PASARÁ."""
    rows = [
        {"id": "hyp_01A", "kind": "candidate", "status": "PROPOSED", "parent_id": None,
         "payload": {"tag": "H1", "claim": "decoherencia X", "by": "hilbert"}},
        {"id": "lit_01B", "kind": "literature", "status": "", "parent_id": "hyp_01A",
         "payload": {"title": "paper"}},
        {"id": "exp_01C", "kind": "experiment", "status": "RUN", "parent_id": "hyp_01A",
         "payload": {"result": {"verdict": "holds_empirically"}}},
    ]
    flows = build_flows(rows)
    assert flows[0]["id"] == "H1"
    assert [s["persona"] for s in flows[0]["steps"]] == ["hilbert", "hipatia", "popper"]
    assert flows[0]["current"] == "popper"      # verde: trabaja ahora
    assert flows[0]["from"] == "hipatia"        # amarillo: de dónde viene
    assert flows[0]["next"] == "bohr"           # naranja: a dónde pasa (hands_to de Popper)
    assert flows[0]["steps"][-1]["verdict"] == "holds_empirically"


def test_flow_collapses_consecutive_steps_of_same_persona():
    """12 papers de Hipatia = UN paso 'buscó literatura ×12', no 12 caritas seguidas."""
    rows = [
        {"id": "hyp_01A", "kind": "candidate", "status": "PROPOSED", "parent_id": None,
         "payload": {"tag": "H1", "claim": "C"}},
        {"id": "lit_01B", "kind": "literature", "status": "", "parent_id": "hyp_01A",
         "payload": {"title": "p1"}},
        {"id": "lit_01C", "kind": "literature", "status": "", "parent_id": "hyp_01A",
         "payload": {"title": "p2"}},
        {"id": "lit_01D", "kind": "literature", "status": "", "parent_id": "hyp_01A",
         "payload": {"title": "p3"}},
        {"id": "exp_01E", "kind": "experiment", "status": "RUN", "parent_id": "hyp_01A",
         "payload": {"result": {"verdict": "holds_empirically"}}},
    ]
    steps = build_flows(rows)[0]["steps"]
    assert [s["persona"] for s in steps] == ["hilbert", "hipatia", "popper"]
    assert steps[1]["n"] == 3                       # colapsado con contador
    # y las decisiones de Bohr NO ensucian el riel (no son pasos de trabajo)
    rows.append({"id": "dec_01F", "kind": "decision", "status": "TAKEN",
                 "parent_id": "hyp_01A", "payload": {"to": "popper", "reason": "r"}})
    assert len(build_flows(rows)[0]["steps"]) == 3


def test_stories_narrate_each_persona_work_per_hypothesis():
    """Cada personaje cuenta en PRIMERA PERSONA qué hizo por H y a quién se la pasó."""
    rows = [
        {"id": "hyp_01A", "kind": "candidate", "status": "PROPOSED", "parent_id": None,
         "payload": {"tag": "H1", "claim": "C", "by": "hilbert"}},
        {"id": "lit_01B", "kind": "literature", "status": "", "parent_id": "hyp_01A",
         "payload": {"title": "p1"}},
        {"id": "lit_01C", "kind": "literature", "status": "", "parent_id": "hyp_01A",
         "payload": {"title": "p2"}},
        {"id": "exp_01D", "kind": "experiment", "status": "RUN", "parent_id": "hyp_01A",
         "payload": {"result": {"verdict": "refuted"}}},
        {"id": "ref_01E", "kind": "reformulation", "status": "PROPOSED",
         "parent_id": "hyp_01A", "payload": {"statement": "C v2"}},
    ]
    flows = build_flows(rows)
    st = build_stories(flows)
    assert st["hilbert"][0].startswith("H1: planteé la conjetura")
    assert "Se la pasé a Hipatia" in st["hilbert"][0]           # el porqué del pase
    assert "leí 2 fuente(s)" in st["hipatia"][0]                # con números reales
    assert "veredicto: refuted" in st["popper"][0]
    assert "reformulé" in st["feynman"][0]
    # pedagogía: cada párrafo explica CÓMO, POR QUÉ y QUÉ SIGNIFICA
    for line in (st["hilbert"][0], st["hipatia"][0], st["popper"][0]):
        assert "¿Por qué?" in line and "Significa" in line
    # y el viaje trae el medidor de FRONTERA honesto
    c0 = council_for({})
    assert c0["journey"]["frontier"]["level"] == "camino"
    # y viaja dentro de council_for → el cajón del personaje lo muestra
    c = council_for({}, flows=flows)
    by = {p["id"]: p for p in c["personas"]}
    assert by["popper"]["story"] and by["popper"]["story"][0].startswith("H1:")


def test_flow_state_closed_vs_open():
    """Columna GRIS = hipótesis terminada (veredicto terminal o rechazo humano);
    ROJA = abierta, aún espera una decisión."""
    rows_closed = [
        {"id": "hyp_01A", "kind": "candidate", "status": "PROPOSED", "parent_id": None,
         "payload": {"tag": "H1", "claim": "C"}},
        {"id": "exp_01B", "kind": "experiment", "status": "RUN", "parent_id": "hyp_01A",
         "payload": {"result": {"verdict": "refuted"}}},
    ]
    assert build_flows(rows_closed)[0]["state"] == "closed"      # terminó refutada → gris
    rows_rej = [{"id": "hyp_01C", "kind": "candidate", "status": "REJECTED",
                 "parent_id": None, "payload": {"claim": "D"}}]
    assert build_flows(rows_rej)[0]["state"] == "closed"         # rechazo humano → gris
    rows_open = [
        {"id": "hyp_01E", "kind": "candidate", "status": "PROPOSED", "parent_id": None,
         "payload": {"claim": "E"}},
        {"id": "exp_01F", "kind": "experiment", "status": "RUN", "parent_id": "hyp_01E",
         "payload": {"result": {"verdict": "holds_empirically"}}},
        {"id": "ref_01G", "kind": "reformulation", "status": "PROPOSED",
         "parent_id": "hyp_01E", "payload": {"statement": "E refinada"}},
    ]
    assert build_flows(rows_open)[0]["state"] == "open"          # aún tiene algo que decir


def test_halos_follow_live_status_when_cycle_is_running():
    c = council_for({}, live={"persona": "popper", "from_persona": "feynman",
                              "next_persona": "godel", "done": False})
    assert c["halos"] == {"now": ["popper"], "from": ["feynman"], "next": ["godel"]}
    # y con el ciclo terminado, los halos salen del último paso de cada flujo
    c2 = council_for({}, live={"persona": "bohr", "done": True},
                     flows=[{"current": "popper", "from": "hipatia", "next": "bohr"}])
    assert c2["halos"]["now"] == ["popper"]


def test_persona_shows_its_real_ledger_items():
    """U2: each owner-persona surfaces its real fichas from the project ledger."""
    items = {
        "candidate": [{"claim": "phi(n) no divide n-1"}],
        "experiment": [{"claim": "Lehmer", "result": {"verdict": "holds_empirically"},
                        "method": "Popper"}],
        "literature": [{"title": "Lehmer's totient problem", "year": 1932}],
        "dossier": [], "critique": [],
    }
    c = council_for({"hypotheses": 1, "experiments": 1}, items=items)
    by = {p["id"]: p for p in c["personas"]}
    # Popper owns experiments → his ficha carries the verdict
    assert by["popper"]["items_label"] == "experimentos"
    assert by["popper"]["items"][0]["verdict"] == "holds_empirically"
    # Hilbert owns hypotheses, Hipatia literature
    assert by["hilbert"]["items"][0]["title"].startswith("phi(n)")
    assert by["hipatia"]["items"][0]["title"] == "Lehmer's totient problem"
    # a non-owner persona has no items panel
    assert "items_label" not in by["davinci"]
