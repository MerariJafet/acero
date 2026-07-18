"""Portal tests: authenticated routes, real data, gates, security, DOM (Sprint 15/23)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from acero.api.app import create_app

_STATIC = Path(__file__).parents[2] / "src" / "acero" / "portal" / "static"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Isolate the portal user store + DB per test (config cache cleared)."""
    from acero.core.config import get_config
    monkeypatch.setenv("ACERO_PORTAL_USERS", str(tmp_path / "users.json"))
    monkeypatch.setenv("ACERO_DB_URL", f"sqlite:///{tmp_path}/portal.sqlite")
    get_config.cache_clear()
    from acero.portal.auth import UserStore
    UserStore().create_user("tester", "testpass123")
    yield
    get_config.cache_clear()


@pytest.fixture()
def anon(env) -> TestClient:
    return TestClient(create_app())


@pytest.fixture()
def client(env) -> TestClient:
    """An authenticated client with the CSRF header pre-set."""
    c = TestClient(create_app())
    r = c.post("/portal/api/login", json={"username": "tester", "password": "testpass123"})
    assert r.status_code == 200
    c.headers.update({"X-CSRF-Token": r.json()["csrf"]})
    return c


# --- shell + static -------------------------------------------------------

def test_portal_shell_served_with_security_headers(anon):
    r = anon.get("/portal/")
    assert r.status_code == 200
    assert "<title>ACERO" in r.text
    assert "Content-Security-Policy" in r.headers
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_portal_static_assets_served(anon):
    assert anon.get("/portal/static/js/app.js").status_code == 200
    assert anon.get("/portal/static/style.css").status_code == 200


# --- auth is enforced ------------------------------------------------------

def test_reads_require_login(anon):
    for path in ("/portal/api/overview", "/portal/api/programs", "/portal/api/runtime"):
        assert anon.get(path).status_code == 401


def test_login_logout_cycle(anon):
    assert anon.get("/portal/api/session").status_code == 401
    r = anon.post("/portal/api/login", json={"username": "tester", "password": "testpass123"})
    assert r.status_code == 200 and "csrf" in r.json()
    assert anon.get("/portal/api/overview").status_code == 200
    anon.post("/portal/api/logout")
    assert anon.get("/portal/api/overview").status_code == 401


def test_bad_password_rejected(anon):
    assert anon.post("/portal/api/login",
                     json={"username": "tester", "password": "wrong"}).status_code == 401


# --- real data (no central mocks) -----------------------------------------

def test_overview_reports_real_state(client):
    ov = client.get("/portal/api/overview").json()
    assert ov["gate_rules"] >= 80
    assert ov["auto_publication"] is False
    assert len(ov["sections"]) >= 10
    assert ov["user"] == "tester"


def test_reliability_view_uses_real_engine(client):
    rel = client.get("/portal/api/reliability").json()
    assert rel["red_team"]["detected"] == rel["red_team"]["n"]
    assert "adversarial_robustness" in rel["card"]["dimensions"]


def test_review_view_runs_real_gauntlet(client):
    assert client.get("/portal/api/review").json()["all_passed"] is True


# --- gates enforced in the UI layer too -----------------------------------

def test_decision_requires_csrf(client):
    bare = TestClient(create_app())
    bare.post("/portal/api/login", json={"username": "tester", "password": "testpass123"})
    # logged in but no CSRF header -> 403
    assert bare.post("/portal/api/decision", json={"decision": "DEFER"}).status_code == 403


def test_decision_approve_requires_reason(client):
    assert client.post("/portal/api/decision",
                       json={"decision": "APPROVE", "reason": ""}).status_code == 422
    ok = client.post("/portal/api/decision", json={"decision": "APPROVE", "reason": "understood"})
    assert ok.status_code == 200 and ok.json()["recorded"] == "APPROVE"


def test_decision_rejects_unknown_action(client):
    assert client.post("/portal/api/decision", json={"decision": "PUBLISH"}).status_code == 400


def test_decision_center_shows_why_not_execute(client):
    d = client.get("/portal/api/decision").json()
    assert "DISCOVERY_CONFIRMED is never granted" in d["why_not_execute"]
    assert "REQUIRE_EXTERNAL_REVIEW" in d["actions"]


# --- workspace flow drives protected services ------------------------------

def test_workspace_full_flow_and_gate_blocks_invalid(client):
    prog = client.post("/portal/api/workspace/program", json={"mission": "m"}).json()
    proj = client.post("/portal/api/workspace/project",
                       json={"title": "t", "program_id": prog["id"]}).json()
    client.post("/portal/api/workspace/question", json={"program_id": prog["id"], "text": "q?"})
    hyps = client.post("/portal/api/workspace/hypotheses",
                       json={"project_id": proj["id"], "question": "q?"}).json()
    assert len(hyps) >= 3
    client.post("/portal/api/workspace/approve",
                json={"hypothesis_id": hyps[0]["id"], "reason": "reviewed"})
    exp = client.post("/portal/api/workspace/experiment",
                      json={"project_id": proj["id"], "hypothesis_id": hyps[0]["id"]}).json()
    good = client.post("/portal/api/workspace/gate", json={"artifact": exp}).json()
    bad = client.post("/portal/api/workspace/gate", json={"artifact": {
        "dimensions_valid": False, "train_test_disjoint": False,
        "reproduced": False, "codex_treated_as_evidence": True}}).json()
    assert good["outcome"] != "BLOCKED"
    assert bad["outcome"] == "BLOCKED"
    doss = client.post("/portal/api/workspace/dossier",
                       json={"project_id": proj["id"], "claim": "synthetic"}).json()
    assert doss["can_publish_automatically"] is False


def test_workspace_approve_requires_reason(client):
    proj = client.post("/portal/api/workspace/project", json={"title": "t"}).json()
    hyps = client.post("/portal/api/workspace/hypotheses",
                       json={"project_id": proj["id"], "question": "q?"}).json()
    r = client.post("/portal/api/workspace/approve",
                    json={"hypothesis_id": hyps[0]["id"], "reason": ""})
    assert r.status_code == 422


# --- security -------------------------------------------------------------

def test_portal_exposes_no_secrets_or_shell(client):
    for path in ("/portal/api/overview", "/portal/api/reliability", "/portal/api/runtime",
                 "/portal/api/decision"):
        blob = client.get(path).text.lower()
        assert "hmac_secret" not in blob and "signature" not in blob
    js = (_STATIC / "js" / "app.js").read_text()
    assert "eval(" not in js and "child_process" not in js


def test_no_inline_event_handlers_in_client(client):
    """CSP forbids inline handlers; the client must use addEventListener only."""
    for f in (_STATIC / "js").rglob("*.js"):
        text = f.read_text()
        assert "onclick=" not in text, f"{f} uses inline onclick (CSP violation)"


def test_world_endpoint_handles_missing_project(client):
    r = client.get("/portal/api/world/nonexistent")
    assert r.status_code in (200, 404)


# --- DOM structure --------------------------------------------------------

def test_spa_shell_has_landmarks_and_login(anon):
    html = (_STATIC / "index.html").read_text()
    assert 'id="nav"' in html and 'id="view"' in html
    assert "/portal/static/js/app.js" in html
    assert 'id="login-form"' in html          # auth gate present
    assert 'class="skip-link"' in html        # accessibility landmark


# --- self-evaluation + collaboration views --------------------------------

def test_portal_evaluation_view(client):
    e = client.get("/portal/api/evaluation").json()
    assert e["verdict"] in ("NO_REGRESSION", "REGRESSION_DETECTED", "INSUFFICIENT_BASELINE")
    assert len(e["benchmarks"]) >= 5


def test_self_evaluation_in_sections(client):
    assert "Self-Evaluation" in client.get("/portal/api/overview").json()["sections"]


def test_portal_collaboration_view(client):
    col = client.get("/portal/api/collaboration").json()
    assert col["ai_authorship_allowed"] is False
    assert col["gauntlet"]["all_passed"] is True
    assert "NOT external review" in col["note"]


def test_result_cards_present(client):
    cards = client.get("/portal/api/results/cards").json()
    assert len(cards) >= 2
    for c in cards:
        assert c["prohibited_claims"] and c["allowed_claims"]
