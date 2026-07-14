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
