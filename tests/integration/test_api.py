from fastapi.testclient import TestClient

from acero.api.app import create_app


def _client():
    return TestClient(create_app())


def test_health():
    r = _client().get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_version_and_policies():
    c = _client()
    assert c.get("/version").json()["version"]
    pol = c.get("/policies").json()
    assert "costs" in pol and "research_safety" in pol


def test_domains_endpoint():
    c = _client()
    doms = c.get("/domains").json()
    names = {d["name"] for d in doms}
    assert {"physics", "astronomy", "genetics", "chemistry"} <= names
    bench = c.get("/domains/physics/benchmark").json()
    assert bench["all_passed"] is True
    assert c.get("/domains/nope/benchmark").status_code == 404


def test_discovery_endpoints():
    c = _client()
    pid = c.post("/projects", json={"title": "Disc API", "domain": "physics"}).json()["id"]
    # empty to start
    assert c.get(f"/projects/{pid}/discovery/candidate").json() == []
    assert c.get(f"/projects/{pid}/discovery/badkind").status_code == 400
    assert c.get(f"/projects/{pid}/discovery/candidates/rejected").json() == []


def test_inference_endpoints():
    c = _client()
    r = c.get("/inference/discover/damped").json()
    assert r["inference_level"] in {"system_identification", "curve_fitting"}
    assert "dv/dt" in r["equations"]
    assert r["imposed"]  # library was imposed
    assert c.get("/inference/discover/nope").status_code == 404


def test_cognitive_validate_equation_endpoint():
    c = _client()
    assert c.get("/cognitive/validate-equation", params={"lhs": "force", "rhs": "velocity"}
                 ).json()["consistent"] is False


def test_project_crud_over_api():
    c = _client()
    created = c.post("/projects", json={"title": "API project", "domain": "math"}).json()
    pid = created["id"]
    got = c.get(f"/projects/{pid}").json()
    assert got["title"] == "API project"
    assert c.get(f"/projects/{pid}/entities").json() == []
    assert c.get("/projects/missing").status_code == 404


# --- Sprint 9: Human Understanding Engine + Global Gate ---------------------

def test_gate_rules_and_check_endpoints():
    c = _client()
    rules = c.get("/gate/rules").json()
    assert "INFERENCE" in rules and rules["INFERENCE"]
    bad = c.get("/gate/check/INFERENCE", params={"bad": True}).json()
    assert bad["outcome"] == "BLOCKED"
    clean = c.get("/gate/check/INFERENCE").json()
    assert clean["outcome"] in ("PASS", "PASS_WITH_WARNINGS")
    assert c.get("/gate/check/NOPE").status_code == 404


def test_learn_requirements_endpoint():
    c = _client()
    reqs = c.get("/learn/requirements/sindy").json()
    assert reqs and any(r["blocking"] for r in reqs)
    assert c.get("/learn/requirements/nope").status_code == 404


def test_learn_benchmark_endpoint():
    c = _client()
    r = c.get("/learn/benchmark").json()
    assert r["case_4_adversarial_gate"]["gate_blocked"] is True
    assert r["transfer"]["transfer_pass"] is True


# --- Sprint 10: Domain Labs + inline gate + hybrid grader ------------------

def test_domain_labs_endpoints():
    c = _client()
    labs = c.get("/domains/labs").json()
    assert {lb["id"] for lb in labs} == {"physics", "astronomy", "genetics", "chemistry"}
    phys = c.get("/domains/labs/physics/benchmark").json()
    assert len(phys) == 8
    caps = c.get("/domains/labs/genetics/capabilities").json()
    assert caps["cannot_do"]
    assert c.get("/domains/labs/nope").status_code == 404


def test_multi_domain_and_bypass_endpoints():
    c = _client()
    md = c.get("/benchmarks/multi-domain").json()
    assert md["track_chemistry"]["gate_blocks_stoichiometry_violation"] is True
    bp = c.get("/gate/bypass-test").json()
    assert bp["all_blocked"] is True


def test_grader_benchmark_endpoint():
    c = _client()
    g = c.get("/grader/benchmark").json()
    assert g["calibration"]["false_positives"] == 0
    assert g["adversarial"]["any_fooled"] is False


# --- Sprint 11: reliability + publication candidate ------------------------

def test_reliability_endpoints():
    c = _client()
    rt = c.get("/reliability/red-team").json()
    assert rt["detected"] == rt["n"] and not rt["missed"]
    mut = c.get("/reliability/mutation").json()
    assert not mut["survived"]
    assert c.get("/reliability/gauntlet").json()["all_passed"] is True
    card = c.get("/reliability/scorecard").json()
    assert "adversarial_robustness" in card["dimensions"]


def test_publication_candidate_never_auto_publishes():
    c = _client()
    pc = c.get("/publication/candidate").json()
    assert pc["can_publish_automatically"] is False


def test_evidence_dependencies_endpoint():
    c = _client()
    d = c.get("/reliability/evidence-dependencies").json()
    assert d["n_independent_groups"] < d["n_items"]


def test_readiness_has_no_discovery_confirmed():
    c = _client()
    levels = c.get("/reliability/readiness").json()["levels"]
    assert "DISCOVERY_CONFIRMED" not in levels
    assert "READY_FOR_HUMAN_SCIENTIFIC_REVIEW" in levels
