"""Principal Investigator loop — decision, methodology bounds, tick side-effects,
pause/resume, and the event+interval driver. All offline: provider and the
mission/hypothesis services are injected, so no LLM or real mission runs."""
from __future__ import annotations

import pytest

from acero.ledger.service import ResearchLedger
from acero.portal import research_loop as rl
from acero.portal.hypotheses import HypothesisService
from acero.portal.research_loop import (
    PrincipalInvestigator,
    ResearchLoop,
    build_digest,
    is_paused,
    load_state,
    pause,
    resume,
    start_timed,
    synthesize_and_relaunch,
)


@pytest.fixture(autouse=True)
def _loop_root(tmp_path, monkeypatch):
    monkeypatch.setenv("ACERO_LOOP_ROOT", str(tmp_path / "loop"))


# --- injected fakes -----------------------------------------------------------

class _Prov:
    def __init__(self, decision):
        self.decision = decision

    def available(self):
        return True

    def complete_json(self, prompt, schema, *, temperature=0.0):
        return self.decision


class _Engine:
    def __init__(self, missions=None):
        self.started = []
        self.missions = missions or []

    def start_all(self, pid, *, use_ai=True, sync=False):
        self.started.append(pid)
        return {"started": [{"hyp": "h1"}], "skipped": []}

    def list_missions(self, pid):
        return self.missions


class _Hyps:
    def __init__(self):
        self.calls = []

    def generate(self, pid, *, n=6, use_ai=True, focus=""):
        self.calls.append((n, focus))
        return {"ok": True, "created": [{"id": f"h{i}"} for i in range(n)]}


class _Flow:
    def __init__(self):
        self.approved = []

    def set_status(self, pid, hid, status, reason=""):
        self.approved.append((hid, status))


def _pi(provider, **kw):
    return PrincipalInvestigator(sf=None, provider=provider, engine=kw.get("engine"),
                                 hyps=kw.get("hyps"), flow=kw.get("flow"))


# --- decision + methodology bounds -------------------------------------------

def test_deterministic_bootstraps_then_chases_anomalies():
    pi = _pi(None)
    d0 = pi._deterministic({"hypotheses_by_status": {}})
    assert d0["action"] == "generate_and_run"
    d1 = pi._deterministic({"hypotheses_by_status": {"APPROVED": 2},
                            "open_anomalies": ["algo raro"]})
    assert d1["action"] == "generate_and_run" and d1["focus"]
    d2 = pi._deterministic({"hypotheses_by_status": {"APPROVED": 2}})
    assert d2["action"] == "run_existing"


def test_validate_clamps_and_coerces():
    pi = _pi(None)
    v = pi._validate({"action": "bogus", "n_new": 999})
    assert v["action"] == "run_existing" and v["n_new"] == 0
    v2 = pi._validate({"action": "generate_and_run", "n_new": 0})
    assert v2["n_new"] == 2                       # generate implies ≥ some new
    v3 = pi._validate({"action": "generate_and_run", "n_new": 50})
    assert v3["n_new"] == rl.MAX_NEW_HYP_PER_TICK


def test_decide_falls_back_when_provider_unavailable():
    class _Down:
        def available(self):
            return False
    d = _pi(_Down()).decide({"hypotheses_by_status": {}})
    assert d["action"] == "generate_and_run"      # deterministic path


# --- tick side effects (build_digest monkeypatched) ---------------------------

def _canned_digest(*a, **k):
    return {"hypotheses_by_status": {"APPROVED": 1}, "recent_verdicts": [],
            "open_anomalies": [], "rigor": {}}


def test_tick_generates_approves_and_starts(monkeypatch):
    monkeypatch.setattr(rl, "build_digest", _canned_digest)
    eng, hyp, flow = _Engine(), _Hyps(), _Flow()
    pi = _pi(_Prov({"action": "generate_and_run", "focus": "anomalías", "n_new": 3,
                    "reasoning": "x"}), engine=eng, hyps=hyp, flow=flow)
    rec = pi.tick("p1")
    assert len(hyp.calls) == 1 and hyp.calls[0][0] == 3
    assert hyp.calls[0][1].startswith("anomalías")        # + anti-HARKing steer
    assert len(flow.approved) == 3 and eng.started == ["p1"]
    assert rec["applied"]["started"] == 1 and rec["dry"] is False
    assert rl.load_state("p1")["ticks"] == 1


class _NoStart(_Engine):
    def start_all(self, pid, *, use_ai=True, sync=False):
        return {"started": [], "skipped": []}


class _NoHyps(_Hyps):
    def generate(self, pid, *, n=6, use_ai=True, focus=""):
        self.calls.append((n, focus))
        return {"ok": True, "created": []}


def test_tick_expands_frontier_when_nothing_to_run(monkeypatch):
    # PI picks 'deepen' but nothing is runnable (finished/empty project) →
    # self-correct by EXPANDING the frontier with new hypotheses, never dry-spin.
    monkeypatch.setattr(rl, "build_digest", _canned_digest)
    hyp, flow = _Hyps(), _Flow()
    pi = _pi(_Prov({"action": "deepen", "reasoning": "profundizar"}),
             engine=_NoStart(), hyps=hyp, flow=flow)
    rec = pi.tick("pb")
    assert rec["applied"].get("expanded") is True
    assert rec["applied"]["generated"] >= 2 and rec["applied"]["approved"] >= 2
    # nothing actually ran in this fake engine → dry (driver will back off), but
    # the frontier WAS expanded so a real engine would launch the new hypotheses
    assert rec["dry"] is True


def test_pi_pause_is_cooldown_not_stop(monkeypatch):
    # a PI 'pause' decision must NOT stop the loop (only the researcher pauses);
    # it is a cooldown: no work added, no missions started, treated as dry.
    monkeypatch.setattr(rl, "build_digest", _canned_digest)
    pi = _pi(_Prov({"action": "pause", "reasoning": "fricción operativa"}),
             engine=_Engine(), hyps=_Hyps(), flow=_Flow())
    rec = pi.tick("p2")
    assert rec["applied"].get("cooldown") is True
    assert rec["applied"]["started"] == 0 and rec["dry"] is True
    assert is_paused("p2") is False               # PI did NOT pause the loop


def test_dry_tick_increments_backoff_streak(monkeypatch):
    # truly dry: nothing runs AND the generator produces nothing new
    monkeypatch.setattr(rl, "build_digest", _canned_digest)
    pi = _pi(_Prov({"action": "run_existing", "reasoning": "x"}),
             engine=_NoStart(), hyps=_NoHyps(), flow=_Flow())
    pi.tick("p3")
    pi.tick("p3")
    assert rl.load_state("p3")["dry_streak"] == 2


# --- pause / resume -----------------------------------------------------------

def test_pause_resume_roundtrip():
    assert is_paused("p4") is False
    pause("p4")
    assert is_paused("p4") is True
    resume("p4")
    assert is_paused("p4") is False


# --- digest on a real in-memory project (no LLM) ------------------------------

def test_build_digest_summarizes_state(session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Loop", domain="astronomy")
    HypothesisService(session_factory).generate(p.id, use_ai=False)
    dig = build_digest(session_factory, p.id)
    assert dig["project"]["title"] == "Loop"
    assert dig["n_hypotheses"] >= 1
    assert isinstance(dig["hypotheses_by_status"], dict)


# --- driver -------------------------------------------------------------------

class _FakePI:
    """Counts ticks; can pause itself on the Nth tick."""

    def __init__(self, engine, pause_on=None):
        self._engine = engine
        self.pause_on = pause_on
        self.ticks = 0

    def _engine_(self):
        return self._engine

    def tick(self, pid):
        self.ticks += 1
        if self.pause_on and self.ticks >= self.pause_on:
            pause(pid)
        return {"applied": {"started": 1}, "dry": False}


def test_run_stops_at_max_ticks():
    loop = ResearchLoop(sf=None, pi=_FakePI(_Engine()))
    out = loop.run("q1", max_ticks=3, wait=False)
    assert out["ticks"] == 3


def test_run_stops_when_paused_midloop():
    loop = ResearchLoop(sf=None, pi=_FakePI(_Engine(), pause_on=2))
    out = loop.run("q2", wait=False)              # unbounded, but pauses itself
    assert out["ticks"] == 2 and is_paused("q2")


def test_wait_returns_immediately_when_no_active_missions():
    loop = ResearchLoop(sf=None, pi=_FakePI(_Engine(missions=[])))
    slept = []
    loop._wait_for_missions("q3", interval_sec=100, poll_sec=5,
                            sleeper=lambda s: slept.append(s), clock=lambda: 0.0)
    assert slept == []                            # active==0 → no polling


def test_wait_polls_until_missions_finish():
    eng = _Engine(missions=[{"status": "RUNNING"}])
    loop = ResearchLoop(sf=None, pi=_FakePI(eng))
    t = {"v": 0.0}
    calls = {"n": 0}

    def _clock():
        return t["v"]

    def _sleep(s):
        t["v"] += s
        calls["n"] += 1
        if calls["n"] >= 2:
            eng.missions = []                     # missions finish after 2 polls
    loop._wait_for_missions("q4", interval_sec=100, poll_sec=5,
                            sleeper=_sleep, clock=_clock)
    assert calls["n"] == 2


# --- Modo Loop: temporizador + síntesis-y-relanzamiento -----------------------

class _Down:
    """Fake provider siempre no-disponible — nunca toca red/subprocess real."""

    def available(self):
        return False


def test_start_timed_sets_deadline_hours_from_now(monkeypatch):
    monkeypatch.setattr(rl.time, "time", lambda: 1000.0)
    st = start_timed("m1", 2.0)
    assert st["deadline"] == 1000.0 + 2 * 3600
    assert st["deadline_hours"] == 2.0
    assert st["paused"] is False


def test_synthesize_no_provider_no_anomalies_needs_human_review(monkeypatch,
                                                                 session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Synth1", domain="astronomy")
    monkeypatch.setattr(rl, "build_digest", lambda sf, pid, recent=8: {
        "hypotheses_by_status": {"APPROVED": 1}, "recent_verdicts": [],
        "open_anomalies": [], "rigor": {"resolved": 1, "total": 1}})
    start_timed(p.id, 1.0)
    rec = synthesize_and_relaunch(session_factory, p.id, provider=_Down())
    assert rec["decision"] == "needs_human_review"
    assert rec["relaunched"]["started"] == 0
    st = load_state(p.id)
    assert st["paused"] is True and st["status"] == "modo_loop_completed"
    assert st["deadline"] is None and st["last_synthesis_id"] == rec["id"]
    # queda registrado en el ledger, no solo en el estado del loop
    from acero.discovery.store import DiscoveryStore
    store = DiscoveryStore(session_factory, lg)
    rows = store.list_objects(p.id, kind="report")
    assert any(r.get("id") == rec["id"] for r in rows)


def test_synthesize_no_provider_with_anomalies_relaunches(monkeypatch,
                                                           session_factory):
    lg = ResearchLedger(session_factory)
    p = lg.create_project("Synth2", domain="astronomy")
    monkeypatch.setattr(rl, "build_digest", lambda sf, pid, recent=8: {
        "hypotheses_by_status": {"APPROVED": 1}, "recent_verdicts": [],
        "open_anomalies": ["algo raro"], "rigor": {}})
    eng, hyp, flow = _Engine(), _Hyps(), _Flow()
    start_timed(p.id, 1.0)
    rec = synthesize_and_relaunch(session_factory, p.id,
                                  pi=_pi(_Down(), engine=eng, hyps=hyp, flow=flow))
    # provider no-disponible -> cae al determinístico, que SÍ decide relanzar
    # cuando hay anomalías abiertas
    assert rec["decision"] == "relaunch"
    assert rec["relaunched"]["started"] == 1
    assert load_state(p.id)["status"] == "modo_loop_completed"


def test_resume_on_startup_revives_only_running_projects(monkeypatch):
    import time as _time

    resume("running1")
    pause("paused1")
    # "idle2" never touched -> status stays "idle", must NOT be revived either

    started = []

    class _FakeLoop:
        def start_background(self, pid, **kw):
            started.append(pid)

    monkeypatch.setattr(rl, "default_loop", lambda: _FakeLoop())
    rl.resume_on_startup(delay_sec=0)
    for _ in range(50):
        if started:
            break
        _time.sleep(0.02)
    assert started == ["running1"]


def test_resume_on_startup_disabled_via_env(monkeypatch):
    resume("running2")
    monkeypatch.setenv("ACERO_PI_RESUME_DISABLED", "1")
    called = {"n": 0}
    monkeypatch.setattr(rl, "default_loop", lambda: called.update(n=called["n"] + 1))
    rl.resume_on_startup(delay_sec=0)
    assert called["n"] == 0


def test_run_triggers_synthesis_when_deadline_passed(monkeypatch):
    called = {}

    def _fake_synth(sf, pid):
        called["pid"] = pid
        pause(pid)                     # como haría synthesize_and_relaunch real
        return {"decision": "needs_human_review"}

    monkeypatch.setattr(rl, "synthesize_and_relaunch", _fake_synth)
    start_timed("m2", 1.0)
    monkeypatch.setattr(rl.time, "time", lambda: 1e18)   # deadline ya pasó
    loop = ResearchLoop(sf="sf", pi=_FakePI(_Engine()))
    out = loop.run("m2", wait=False)
    assert called.get("pid") == "m2"
    assert out["ticks"] == 0                # no llegó a tickear: fue directo a síntesis


# --- triaje del backlog de propuestas (dictamen del Centinela) ----------------

def _seed_proposed(session_factory, pid, specs):
    """Crea candidatas PROPOSED directas en el store: specs = [(tag, claim), ...]."""
    from acero.core.ids import new_id
    from acero.discovery.store import DiscoveryStore
    from acero.ledger.service import ResearchLedger
    store = DiscoveryStore(session_factory, ResearchLedger(session_factory))
    ids = []
    for i, (tag, claim) in enumerate(specs):
        hid = new_id("hyp")
        store.put(pid, "candidate", hid,
                  {"id": hid, "tag": tag, "claim": claim, "status": "PROPOSED",
                   "created_at": f"2026-08-21T00:00:{i:02d}+00:00"},
                  status="PROPOSED", actor="test", summary=tag)
        ids.append(hid)
    return store, ids


def test_triage_rejects_duplicates_keeps_original(session_factory):
    from acero.ledger.service import ResearchLedger
    p = ResearchLedger(session_factory).create_project("Triage1", domain="astronomy")
    store, ids = _seed_proposed(session_factory, p.id, [
        ("H1", "la señal es endotelial"),
        ("H2", "LA  señal es   ENDOTELIAL"),      # duplicada (normaliza espacios/caso)
        ("H3", "otra idea distinta"),
    ])
    pi = PrincipalInvestigator(session_factory, provider=_Down())
    applied = {"generated": 0, "approved": 0, "started": 0, "blocks": []}
    pi._triage(p.id, applied)
    assert applied.get("triaged_dup") == 1
    assert store.get(ids[0])["status"] == "PROPOSED"     # la original se queda
    assert store.get(ids[1])["status"] == "REJECTED"
    assert "duplicada" in store.get(ids[1])["approval_reason"]
    assert store.get(ids[2])["status"] == "PROPOSED"


def test_triage_caps_backlog_rejecting_oldest(session_factory, monkeypatch):
    from acero.ledger.service import ResearchLedger
    monkeypatch.setenv("ACERO_PI_MAX_PROPOSED", "2")
    p = ResearchLedger(session_factory).create_project("Triage2", domain="astronomy")
    store, ids = _seed_proposed(session_factory, p.id, [
        ("H1", "idea uno"), ("H2", "idea dos"), ("H3", "idea tres"), ("H4", "idea cuatro"),
    ])
    pi = PrincipalInvestigator(session_factory, provider=_Down())
    applied = {"generated": 0, "approved": 0, "started": 0, "blocks": []}
    pi._triage(p.id, applied)
    assert applied.get("triaged_stale") == 2
    # las 2 MÁS VIEJAS rechazadas con razón restaurable; las 2 nuevas siguen
    assert store.get(ids[0])["status"] == "REJECTED"
    assert store.get(ids[1])["status"] == "REJECTED"
    assert "restaurable" in store.get(ids[0])["approval_reason"]
    assert store.get(ids[2])["status"] == "PROPOSED"
    assert store.get(ids[3])["status"] == "PROPOSED"


def test_generate_adopts_existing_proposed_before_creating_new(session_factory):
    from acero.ledger.service import ResearchLedger
    p = ResearchLedger(session_factory).create_project("Adopt1", domain="astronomy")
    store, ids = _seed_proposed(session_factory, p.id, [
        ("H1", "vieja"), ("H2", "media"), ("H3", "reciente"),
    ])
    hyp = _Hyps()
    pi = PrincipalInvestigator(session_factory, provider=_Down(), hyps=hyp)
    applied = {"generated": 0, "approved": 0, "started": 0, "blocks": []}
    pi._generate_and_approve(p.id, 2, "", applied)
    # adoptó las 2 mejores según el dictamen (fallback: las más recientes)
    # y NO generó nada nuevo
    assert applied.get("adopted") == 2 and applied["approved"] == 2
    assert applied["generated"] == 0 and hyp.calls == []
    assert store.get(ids[2])["status"] == "APPROVED"
    assert store.get(ids[1])["status"] == "APPROVED"
    assert store.get(ids[0])["status"] == "PROPOSED"     # la vieja espera su turno


def test_triage_respects_bohr_llm_ranking(session_factory, monkeypatch):
    """Cuando el LLM de Bohr está disponible, SU ranking manda — no la antigüedad:
    la que Bohr rankea al final se rechaza aunque sea la más reciente, con SU razón."""
    from acero.ledger.service import ResearchLedger
    monkeypatch.setenv("ACERO_PI_MAX_PROPOSED", "2")
    p = ResearchLedger(session_factory).create_project("Triage3", domain="astronomy")
    store, ids = _seed_proposed(session_factory, p.id, [
        ("H1", "idea vieja pero fuerte"), ("H2", "idea media"), ("H3", "idea nueva floja"),
    ])

    class _Bohr:
        def available(self):
            return True

        def complete_json(self, prompt, schema, *, temperature=0.0):
            # Bohr juzga: la vieja (H1) es la mejor; la nueva (H3) no promete
            return {"ranked": [ids[0], ids[1], ids[2]],
                    "drop_reasons": {ids[2]: "redundante y sin predicción a priori"}}

    pi = PrincipalInvestigator(session_factory, provider=_Bohr())
    applied = {"generated": 0, "approved": 0, "started": 0, "blocks": []}
    pi._triage(p.id, applied)
    assert store.get(ids[0])["status"] == "PROPOSED"     # la vieja SOBREVIVE
    assert store.get(ids[1])["status"] == "PROPOSED"
    assert store.get(ids[2])["status"] == "REJECTED"     # la nueva cae por juicio
    assert "redundante" in store.get(ids[2])["approval_reason"]


def test_question_seed_turns_eva_blocks_into_fertile_questions():
    """Reconexión EP3/F4: los bloqueos EVA recientes pasan por el motor de
    preguntas y enriquecen el focus de la siguiente generación."""
    from acero.portal.research_loop import append_feedback
    pid = "qseed1"
    append_feedback(pid, {"ts": "t", "tick": 1, "decision": {}, "applied": {
        "blocks": ["EVA interno bloqueó la misión: hipótesis vaga sin predicción",
                   "ya hay una misión activa (msn_X)"]}})
    pi = _pi(_Down())
    out = pi._question_seed(pid, "foco original")
    assert out.startswith("foco original")
    assert "PREGUNTAS FÉRTILES" in out
    assert "misión activa" not in out          # bloqueos de concurrencia filtrados


def test_question_seed_no_blocks_returns_focus_unchanged():
    pi = _pi(_Down())
    assert pi._question_seed("qseed2", "igual") == "igual"


def test_deepen_ahora_profundiza_literatura_de_verdad(monkeypatch):
    """'deepen' hacía lo MISMO que 'run_existing' (ambas solo lanzaban misiones),
    así que el PI podía decidir distinto sin que cambiara nada — el
    BUCLE_DE_DECISION que cazó el Auditor el 2026-08-21. Ahora profundizar
    significa leer las REFERENCIAS de lo ya leído (y no usa el agente de codegen,
    así que produce trabajo aunque la fábrica esté caída)."""
    monkeypatch.setattr(rl, "build_digest", _canned_digest)

    class _FlowDeep:
        def __init__(self):
            self.deepened = []

        def set_status(self, pid, hid, status, reason="", **kw):
            pass

        def approved(self, pid):
            return [{"id": "h1", "tag": "H1"}, {"id": "h2", "tag": "H2"}]

        def deepen_literature(self, pid, hid, **kw):
            self.deepened.append(hid)
            return {"ok": True, "n_refs": 7}

    flow = _FlowDeep()
    pi = _pi(_Prov({"action": "deepen", "reasoning": "profundizar"}),
             engine=_Engine(), hyps=_Hyps(), flow=flow)
    rec = pi.tick("pdeep")
    assert flow.deepened == ["h1", "h2"]          # leyó referencias de verdad
    assert rec["applied"]["deepened"] == 2


def test_deepen_reporta_el_motivo_cuando_no_puede(monkeypatch):
    """Sin papers indexados aún, profundizar es imposible — y se dice por qué."""
    monkeypatch.setattr(rl, "build_digest", _canned_digest)

    class _FlowNoLit:
        def set_status(self, pid, hid, status, reason="", **kw):
            pass

        def approved(self, pid):
            return [{"id": "h1", "tag": "H1"}]

        def deepen_literature(self, pid, hid, **kw):
            return {"ok": False, "error": "investiga primero: sin papers indexados"}

    pi = _pi(_Prov({"action": "deepen", "reasoning": "x"}),
             engine=_Engine(), hyps=_Hyps(), flow=_FlowNoLit())
    rec = pi.tick("pdeep2")
    assert rec["applied"]["deepened"] == 0
    assert any("investiga primero" in b for b in rec["applied"]["blocks"])


def test_deterministico_rompe_el_bucle_cuando_lanzar_no_cierra_nada():
    """El fallback solo sabía emitir 2 de las 4 acciones ('deepen' y 'pause'
    eran inalcanzables) y con el LLM caído siempre caía aquí → 5+ rondas
    idénticas. Si lanzar no devuelve veredictos, hay que cambiar de táctica."""
    pi = _pi(None)
    d = pi._deterministic({
        "hypotheses_by_status": {"APPROVED": 5}, "open_anomalies": [],
        "recent_decisions": [{"action": "run_existing"}] * 3,
        "recent_verdicts": []})
    assert d["action"] == "deepen"
    assert "veredicto" in d["reasoning"]


def test_deterministico_sigue_lanzando_si_hay_veredictos_frescos():
    """Repetir jugada NO es bucle si está produciendo: no romper lo que funciona."""
    pi = _pi(None)
    d = pi._deterministic({
        "hypotheses_by_status": {"APPROVED": 5}, "open_anomalies": [],
        "recent_decisions": [{"action": "run_existing"}] * 3,
        "recent_verdicts": [{"verdict": "refuted"}]})
    assert d["action"] == "run_existing"


def test_deterministico_no_escala_con_pocas_rondas():
    """Dos rondas iguales todavía no son un bucle — dale tiempo al trabajo."""
    pi = _pi(None)
    d = pi._deterministic({
        "hypotheses_by_status": {"APPROVED": 5}, "open_anomalies": [],
        "recent_decisions": [{"action": "run_existing"}] * 2,
        "recent_verdicts": []})
    assert d["action"] == "run_existing"


def test_el_prompt_avisa_al_director_cuando_repite_sin_cerrar_nada():
    """El dato ya viajaba en el digest pero enterrado en JSON y el LLM seguía
    repitiendo. Ahora el aviso va en texto plano, imposible de pasar por alto."""
    visto = {}

    class _Spy:
        def available(self):
            return True

        def complete_json(self, prompt, schema, *, temperature=0.0):
            visto["prompt"] = prompt
            return {"action": "deepen", "reasoning": "cambio de táctica"}

    pi = _pi(_Spy())
    pi.decide({"hypotheses_by_status": {"APPROVED": 5},
               "recent_decisions": [{"action": "run_existing"}] * 4,
               "recent_verdicts": []})
    assert "ATENCIÓN, DIRECTOR" in visto["prompt"]
    assert "run_existing" in visto["prompt"]


def test_no_avisa_si_la_jugada_repetida_SI_produce():
    """Repetir mientras se cierran preguntas es persistencia, no estancamiento."""
    visto = {}

    class _Spy:
        def available(self):
            return True

        def complete_json(self, prompt, schema, *, temperature=0.0):
            visto["prompt"] = prompt
            return {"action": "run_existing", "reasoning": "va bien"}

    _pi(_Spy()).decide({"hypotheses_by_status": {"APPROVED": 5},
                        "recent_decisions": [{"action": "run_existing"}] * 4,
                        "recent_verdicts": [{"verdict": "refuted"}]})
    assert "ATENCIÓN, DIRECTOR" not in visto["prompt"]


def test_contrapresion_no_encola_si_la_cola_ya_es_enorme(monkeypatch):
    """Encolar más no acelera: el pool corre de a pocas. 2026-08-21: 68 misiones
    activas con 4 workers, y un proyecto famélico con 40 PENDING sin correr."""
    monkeypatch.setenv("ACERO_PI_MAX_QUEUE", "12")

    class _Lleno(_Engine):
        def list_missions(self, pid):
            return [{"status": "PENDING"} for _ in range(40)]

        def start_all(self, pid, *, use_ai=True, sync=False):
            raise AssertionError("no debió intentar encolar con la cola llena")

    n, blocks = _pi(None, engine=_Lleno())._start("psat")
    assert n == 0
    assert any("contrapresión" in b for b in blocks)


def test_con_cola_corta_si_encola(monkeypatch):
    monkeypatch.setenv("ACERO_PI_MAX_QUEUE", "12")

    class _Corta(_Engine):
        def list_missions(self, pid):
            return [{"status": "RUNNING"}, {"status": "DONE"}]

    n, _ = _pi(None, engine=_Corta())._start("pok")
    assert n == 1                              # _Engine.start_all devuelve 1
