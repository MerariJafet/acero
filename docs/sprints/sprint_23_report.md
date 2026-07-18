# Sprint 23 — Professional Research Portal

Date: 2026-07-18
Branch: `integration/acero-2.1-program`
Status: **complete** · `make verify` green (**750 passed**, ruff+mypy+policy+schemas clean)

## Objective

Turn the 413-LOC vanilla portal into a maintainable, secure, **browser-verified**
local scientific application: local auth, a full research workspace flow through
protected services, a Decision Center, a scalable World Model explorer, scientific
result cards, reliability/runtime centers, WCAG basics, and **real Playwright E2E**.

## 23.1 Frontend decision (ADR)

[ADR-PORTAL-STACK-V2.md](../adr/ADR-PORTAL-STACK-V2.md) — **Option A: modular
vanilla ES modules, no build step.** Chosen on measured evidence (193 client LOC,
read-mostly control panel), the local-first/offline requirement, the strict CSP
(`script-src 'self'`, no `unsafe-inline`), the Sprint-26 dependency/supply-chain
audit obligation, and the single Python quality gate. React+Vite rejected as
premature toolchain/dependency cost, not on merit of components.

Client restructured into native ES modules:
`static/js/{api,auth-less bootstrap in app,components,views,workspace}.js` +
`static/index.html` (semantic landmarks) + `static/style.css`.

## 23.2 Playwright (real browser)

- Playwright **1.56.0** (system site-packages), Chromium **141.0.7390.37**
  (`~/.cache/ms-playwright/chromium-1208`).
- Verified a real headless browser launches and executes JS (not TestClient).
- E2E runs a **real uvicorn server in a subprocess** with an isolated DB + user
  store, driven by real Chromium.

## 23.3–23.10 Architecture & sections

Portal Shell · API Client (CSRF-aware) · Authentication · Research Workspace ·
Decision Center · World Model Explorer · Reliability · Red Team · Runtime ·
Self-Evaluation · Review · Collaboration · Publication Candidates (result cards) ·
Learning Center · Settings.

- **Auth (23.4)**: local users, PBKDF2 (200k rounds, per-user salt) — **never
  plaintext**; server-side sessions (256-bit id in httponly + `SameSite=Strict`
  cookie, `Secure` configurable); double-submit **CSRF** on every mutation;
  per-user **rate limiting** with lockout; logout invalidation; manual local
  recovery via `acero portal-user add`.
- **Workspace (23.5)**: program → project → question → hypotheses → approve →
  experiment → **gate** → World Model → dossier. Every action calls the SAME
  protected services as the CLI (`ProgramEngine`, `DiscoveryStore`, `WorldModel`,
  `GlobalGate`, `build_dossier`). **No UI endpoint writes to persistence
  directly.** An invalid artifact is **BLOCKED** by the real gate, shown in the UI.
- **Decision Center (23.6)**: context/evidence/counter-evidence/uncertainty/cost/
  risk/why-not-execute + APPROVE/REJECT/REQUEST_CHANGES/DEFER/ABSTAIN/
  REQUIRE_EXTERNAL_REVIEW; APPROVE requires a reason (422 otherwise).
- **World Model Explorer (23.7)**: server-side pagination (`page_nodes`,
  SQL `LIMIT/OFFSET` + `LIKE` search, `confidence` order, hard cap 200). **Never
  loads the full graph** — proven with **10,000 synthetic nodes**, page query
  < 1s, no cross-page overlap.
- **Result cards (23.8)**: epistemic level, evidence/counter-evidence,
  calibration, reproducibility, gate, **allowed vs prohibited claims**.
- **Reliability/Runtime (23.9/23.10)**: real reliability card + red-team matrix;
  runtime tasks/status/metrics with **token/secret redaction**.

## 23.11 Accessibility (WCAG basics)

Skip link (first focusable), landmarks (`header[role=banner]`, `nav[aria-label]`,
`main#view`), `<label for>` on all inputs, `aria-live` regions, `aria-current` on
nav, visible focus ring (`:focus-visible`), accessible tables (`<caption>`,
`scope=col`), status conveyed by text + pill (not color alone). Verified in a real
browser (landmarks, orphan-label count = 0, Tab focuses the skip link).

Fixed a real accessibility bug found by the browser: `.login { display:grid }` was
overriding the `[hidden]` attribute, so the login pane never truly hid — added
`[hidden] { display:none !important }`.

## 23.12 E2E (real Playwright) — 13 browser tests

Login (+ invalid-login error, + unauthenticated API → 401), nav, program, project,
question, generate hypotheses, approve, run experiment + gate PASS, **gate blocks
invalid artifact**, World Model explorer pagination, result cards show prohibited
claims, dossier (auto-publish OFF), logout; **negative**: no-login 401, invalid
login, CSP `script-src 'self'` present without `unsafe-inline`, accessibility
landmarks/labels, keyboard focus. All green.

Screenshots (real browser): `docs/benchmarks/screenshots/{01_login,02_overview,03_workspace,04_result_cards}.png`.

## 23.13 Performance (measured in-browser)

`docs/benchmarks/portal_performance.json`: DOMContentLoaded ≈ 14 ms, loadComplete
≈ 14 ms, responseStart ≈ 1.6 ms, `/api/overview` round-trip ≈ 5 ms, JS heap ≈ 10 MB.
World Model 10k-node page query < 1s. No data hidden to make numbers look good.

## Tests added

| Area | File | Count |
|------|------|-------|
| Auth units | `tests/unit/test_portal_auth.py` | 9 |
| Portal integration (auth, workspace, gate, security) | `tests/integration/test_portal.py` | 22 |
| World Model explorer scale (10k) | `tests/integration/test_world_explorer_scale.py` | 4 |
| Real browser E2E | `tests/e2e/test_portal_e2e.py` | 13 |

Integrated into `make verify` (via `pytest tests`); `make e2e` runs the browser
suite alone. E2E **skips** (never fails) if no browser binary is present, keeping
the gate portable.

## Security notes

- All `/portal/api/*` require a session except login/session; mutations require CSRF.
- Metrics endpoint now authenticated (no unauthenticated task-label leak).
- CSP unchanged and strict; added `Referrer-Policy: no-referrer`.
- No secrets/tokens exposed; task rows redacted.

## Verdict

Sprint 23 **complete and browser-verified**. Real browser installed AND driven;
E2E real (not TestClient); login functional; portal secured; actions go through
gates; World Model scales; reliability & runtime visible; accessibility baseline
met; performance recorded; tests in `make verify`.

Commit: `sprint-23: professional research portal with real browser e2e`
