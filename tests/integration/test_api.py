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


def test_project_crud_over_api():
    c = _client()
    created = c.post("/projects", json={"title": "API project", "domain": "math"}).json()
    pid = created["id"]
    got = c.get(f"/projects/{pid}").json()
    assert got["title"] == "API project"
    assert c.get(f"/projects/{pid}/entities").json() == []
    assert c.get("/projects/missing").status_code == 404
