"""Sprint 15 tests: unified research portal (routes, real data, gates, security, DOM)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from acero.api.app import create_app


def _client():
    return TestClient(create_app())


# --- shell + static -------------------------------------------------------

def test_portal_shell_served_with_security_headers():
    c = _client()
    r = c.get("/portal/")
    assert r.status_code == 200
    assert "<title>ACERO" in r.text
    assert "Content-Security-Policy" in r.headers
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_portal_static_assets_served():
    c = _client()
    assert c.get("/portal/static/app.js").status_code == 200
    assert c.get("/portal/static/style.css").status_code == 200


# --- real data (no central mocks) -----------------------------------------

def test_overview_reports_real_state():
    ov = _client().get("/portal/api/overview").json()
    assert ov["gate_rules"] >= 80             # real gate registry
    assert ov["auto_publication"] is False
    assert len(ov["sections"]) >= 10


def test_reliability_view_uses_real_engine():
    rel = _client().get("/portal/api/reliability").json()
    assert rel["red_team"]["detected"] == rel["red_team"]["n"]
    assert "adversarial_robustness" in rel["card"]["dimensions"]


def test_review_view_runs_real_gauntlet():
    assert _client().get("/portal/api/review").json()["all_passed"] is True


# --- gates enforced in the UI layer too -----------------------------------

def test_decision_approve_requires_reason():
    c = _client()
    assert c.post("/portal/api/decision", json={"decision": "APPROVE", "reason": ""}).status_code == 422
    ok = c.post("/portal/api/decision", json={"decision": "APPROVE", "reason": "understood"})
    assert ok.status_code == 200 and ok.json()["recorded"] == "APPROVE"


def test_decision_rejects_unknown_action():
    assert _client().post("/portal/api/decision", json={"decision": "PUBLISH"}).status_code == 400


def test_decision_center_shows_why_not_execute():
    d = _client().get("/portal/api/decision").json()
    assert "DISCOVERY_CONFIRMED is never granted" in d["why_not_execute"]
    assert "REQUIRE_EXTERNAL_REVIEW" in d["actions"]


# --- security -------------------------------------------------------------

def test_portal_exposes_no_secrets_or_shell():
    """No portal endpoint returns a raw secret, a raw token signature, or runs a shell."""
    c = _client()
    for path in ("/portal/api/overview", "/portal/api/reliability", "/portal/api/runtime",
                 "/portal/api/decision"):
        blob = c.get(path).text.lower()
        assert "hmac_secret" not in blob and "signature" not in blob
    # static JS must not build shell commands or eval
    js = (Path(__file__).parents[2] / "src" / "acero" / "portal" / "static" / "app.js").read_text()
    assert "eval(" not in js and "child_process" not in js


def test_world_endpoint_handles_missing_project():
    r = _client().get("/portal/api/world/nonexistent")
    # returns stats for an (empty) ephemeral graph or a structured error, never a 500 stack
    assert r.status_code in (200, 404)


# --- DOM structure --------------------------------------------------------

def test_spa_shell_has_nav_and_view_mounts():
    html = (Path(__file__).parents[2] / "src" / "acero" / "portal" / "static" / "index.html").read_text()
    assert 'id="nav"' in html and 'id="view"' in html
    assert "/portal/static/app.js" in html


# --- Sprint 18: self-evaluation view ---------------------------------------

def test_portal_evaluation_view():
    e = _client().get("/portal/api/evaluation").json()
    assert e["verdict"] in ("NO_REGRESSION", "REGRESSION_DETECTED")
    assert len(e["benchmarks"]) >= 5
    astro = next(c for c in e["capabilities"]
                 if c["name"] == "astronomy_timeseries_analysis")
    assert astro["status"] == "EXPERIMENTAL"       # no self-promotion in the UI either


def test_self_evaluation_in_sections():
    assert "Self-Evaluation" in _client().get("/portal/api/overview").json()["sections"]
