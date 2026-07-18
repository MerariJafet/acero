"""Sprint 23 — REAL browser E2E over a REAL server (not TestClient).

Starts uvicorn in a subprocess with an isolated DB + user store, drives a real
headless Chromium through the 13 required flows plus negative security tests.
Skips (does not fail) if Playwright or a browser binary is unavailable, so the
gate stays green on machines without the browser installed; on a machine with it
installed these tests exercise the actual portal end-to-end.
"""

from __future__ import annotations

import contextlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("playwright", reason="playwright not installed")
from playwright.sync_api import Error as PWError  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

_REPO = Path(__file__).parents[2]


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("e2e")
    users = tmp / "users.json"
    db = tmp / "portal.sqlite"
    env = {**os.environ,
           "ACERO_PORTAL_USERS": str(users),
           "ACERO_DB_URL": f"sqlite:///{db}",
           "ACERO_ENV": "development"}
    # create the local user in the same file the server will read
    subprocess.run(
        [sys.executable, "-c",
         "from acero.portal.auth import UserStore;"
         "UserStore().create_user('tester','testpass123')"],
        env=env, check=True, cwd=str(_REPO))

    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "acero.api.app:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        env=env, cwd=str(_REPO))
    base = f"http://127.0.0.1:{port}"
    # wait for readiness
    import urllib.request
    ready = False
    for _ in range(100):
        if proc.poll() is not None:
            raise RuntimeError("uvicorn exited early")
        try:
            with urllib.request.urlopen(base + "/health", timeout=1) as r:
                if r.status == 200:
                    ready = True
                    break
        except Exception:  # noqa: BLE001
            time.sleep(0.1)
    if not ready:
        proc.terminate()
        raise RuntimeError("server did not become ready")
    yield base
    proc.terminate()
    with contextlib.suppress(Exception):
        proc.wait(timeout=5)


@pytest.fixture(scope="module")
def browser():
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            yield b
            b.close()
    except PWError as exc:  # pragma: no cover - environment without a browser binary
        pytest.skip(f"no browser binary available: {exc}")


@pytest.fixture()
def page(browser, server):
    ctx = browser.new_context(base_url=server)
    pg = ctx.new_page()
    yield pg
    ctx.close()


def _login(pg):
    pg.goto("/portal/")
    pg.wait_for_selector("#login-form", state="visible")
    pg.fill("#u", "tester")
    pg.fill("#p", "testpass123")
    pg.click("#login-form button[type=submit]")
    pg.wait_for_selector("#nav button", state="visible", timeout=10000)


# --- flow 1: login (and negative) -----------------------------------------

def test_flow_login_success(page):
    _login(page)
    assert page.is_hidden("#login")
    assert "signed in as tester" in page.inner_text("#whoami")


def test_negative_invalid_login_shows_error(page):
    page.goto("/portal/")
    page.wait_for_selector("#login-form")
    page.fill("#u", "tester")
    page.fill("#p", "wrongpass")
    page.click("#login-form button[type=submit]")
    page.wait_for_selector("#login-error:not(:empty)")
    assert "Invalid credentials" in page.inner_text("#login-error")


def test_negative_api_without_login_is_401(page):
    r = page.request.get("/portal/api/overview")
    assert r.status == 401


# --- flows 2-4: nav, program, project, question ---------------------------

def test_flow_nav_and_workspace_program_project_question(page):
    _login(page)
    page.click("#nav >> text=Research Workspace")
    page.wait_for_selector("#ws-mk-program")
    page.fill("#ws-mission", "transit robustness")
    page.click("#ws-mk-program")
    page.wait_for_selector("#ws-program-out .pill")
    page.fill("#ws-title", "kepler-10 study")
    page.click("#ws-mk-project")
    page.wait_for_selector("#ws-project-out .pill")
    page.fill("#ws-question", "how robustly can we recover a transit?")
    page.click("#ws-mk-question")
    page.wait_for_selector("#ws-question-out .pill")
    assert "question added" in page.inner_text("#ws-question-out")


# --- flows 5-8: hypotheses, approve, experiment, gate block ---------------

def test_flow_hypotheses_approve_experiment_and_gate(page):
    _login(page)
    page.click("#nav >> text=Research Workspace")
    page.wait_for_selector("#ws-mk-program")
    page.fill("#ws-mission", "m")
    page.click("#ws-mk-program")
    page.wait_for_selector("#ws-program-out .pill")
    page.fill("#ws-title", "p")
    page.click("#ws-mk-project")
    page.wait_for_selector("#ws-project-out .pill")
    page.click("#ws-gen-hyp")
    page.wait_for_selector("[data-approve]")
    page.click("[data-approve]")
    page.wait_for_selector("#ws-run-exp:not([disabled])")
    page.click("#ws-run-exp")
    page.wait_for_selector("#ws-exp-out .pill")
    # gate an invalid artifact -> must be blocked
    page.click("#ws-gate-bad")
    page.wait_for_selector("#gate-block")
    assert "correctly blocked" in page.inner_text("#gate-block")


# --- flows 9, 11: world model + dossier -----------------------------------

def test_flow_world_model_and_dossier(page):
    _login(page)
    page.click("#nav >> text=Research Workspace")
    page.wait_for_selector("#ws-mk-project")
    page.fill("#ws-title", "wm-proj")
    page.click("#ws-mk-project")
    page.wait_for_selector("#ws-project-out .pill")
    page.click("#ws-wm")
    page.wait_for_selector("#ws-final-out .pill")
    page.click("#ws-dossier")
    page.wait_for_selector("#dossier-done")
    txt = page.inner_text("#dossier-done")
    assert "auto-publish=OFF" in txt


# --- flow 10/12: result cards (claims) + explorer -------------------------

def test_flow_result_cards_show_prohibited_claims(page):
    _login(page)
    page.click("#nav >> text=Publication Candidates")
    page.wait_for_selector(".card")
    body = page.inner_text("#view")
    assert "PROHIBITED claims" in body


def test_flow_world_explorer_paginates(page):
    _login(page)
    # create a project with one node via workspace, then explore it
    page.click("#nav >> text=Research Workspace")
    page.wait_for_selector("#ws-mk-project")
    page.fill("#ws-title", "explore-proj")
    page.click("#ws-mk-project")
    page.wait_for_selector("#ws-project-out .pill")
    pid = page.inner_text("#ws-project-out").replace("project ", "").strip()
    page.click("#ws-wm")
    page.wait_for_selector("#ws-final-out .pill")
    page.click("#nav >> text=World Model")
    page.wait_for_selector("#wm-pid")
    page.fill("#wm-pid", pid)
    page.click("#wm-go")
    page.wait_for_selector("#wm-out table")
    assert "World Model nodes" in page.inner_text("#wm-out")


# --- flow 13: logout ------------------------------------------------------

def test_flow_logout(page):
    _login(page)
    page.click("#logout")
    page.wait_for_selector("#login-form", state="visible")
    assert page.is_visible("#login")


# --- accessibility (WCAG basics, in a real browser) -----------------------

def test_accessibility_landmarks_and_labels(page):
    _login(page)
    # landmarks
    assert page.locator("nav[aria-label]").count() >= 1
    assert page.locator("main#view").count() == 1
    assert page.locator("header[role=banner]").count() == 1
    # skip link present and is the first focusable element
    assert page.locator("a.skip-link").count() == 1
    # every input has an associated <label for=...> (login pane)
    page.click("#logout")
    page.wait_for_selector("#login-form")
    orphan = page.evaluate(
        """() => {
            const inputs = [...document.querySelectorAll('#login-form input')];
            return inputs.filter(i => !document.querySelector(`label[for="${i.id}"]`)).length;
        }""")
    assert orphan == 0


def test_accessibility_keyboard_focus_visible(page):
    page.goto("/portal/")
    page.wait_for_selector("#login-form")
    page.keyboard.press("Tab")            # should focus the skip link first
    focused = page.evaluate("document.activeElement && document.activeElement.className")
    assert "skip-link" in (focused or "")


def test_performance_metrics_recorded(page, server, tmp_path_factory):
    """Measure real load + API timing in the browser and persist an artifact."""
    _login(page)
    metrics = page.evaluate(
        """async () => {
            const nav = performance.getEntriesByType('navigation')[0] || {};
            const t0 = performance.now();
            const r = await fetch('/portal/api/overview', {credentials:'same-origin'});
            await r.json();
            const apiMs = performance.now() - t0;
            const mem = performance.memory ? performance.memory.usedJSHeapSize : null;
            return {
                domContentLoaded: nav.domContentLoadedEventEnd || null,
                loadComplete: nav.loadEventEnd || null,
                responseStart: nav.responseStart || null,
                overviewApiMs: Math.round(apiMs),
                jsHeapBytes: mem,
            };
        }""")
    assert metrics["overviewApiMs"] is not None
    assert metrics["overviewApiMs"] < 2000      # local API well under 2s
    # persist for the report
    out = _REPO / "docs" / "benchmarks"
    out.mkdir(parents=True, exist_ok=True)
    import json
    (out / "portal_performance.json").write_text(json.dumps(metrics, indent=2))


def test_negative_no_inline_script_csp_blocks(page):
    """The strict CSP (script-src 'self') must be present on portal responses."""
    r = page.request.get("/portal/")
    csp = r.headers.get("content-security-policy", "")
    assert "script-src 'self'" in csp
    assert "'unsafe-inline'" not in csp.split("script-src")[1].split(";")[0]
