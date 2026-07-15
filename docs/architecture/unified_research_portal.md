# Unified Research Portal (Sprint 15)

A functional local web app to operate ACERO from one place, served by FastAPI at `/portal`.

## Scope decision (documented)
Built as a **zero-dependency, no-build vanilla-JS single-page app** rather than a
React/Vite/Vitest/Playwright toolchain. Rationale: keep the portal offline, dependency-light,
and inside `make verify` (pytest) without a Node build step or an npm install over the
network. This is the mission's "component unavailable → document + fallback + test + continue"
path; the fallback (SPA + pytest route/DOM/security tests) is fully tested. A richer JS
toolchain remains possible later.

## Backend (`src/acero/portal/app.py`)
Read aggregators + safe-action endpoints under `/portal/api/*`, mounted into the main API.
Action endpoints go through the SAME protected services as the CLI — **the UI cannot bypass a
gate**. No endpoint exposes a secret, a raw mutation token, or a shell.

- `GET /portal/` — the SPA shell (static `index.html`).
- `GET /portal/api/overview` — version, env, gate-rule count, runtime queue, readiness ceiling,
  `auto_publication: false`, section list.
- `GET /portal/api/{programs,reliability,runtime,review,decision,world/{pid}}` — real engine
  state (Program OS, reliability card + red team, runtime queue, review gauntlet, World Model).
- `POST /portal/api/decision` — records a human decision; **APPROVE requires a reason** (mirrors
  the backend anti-rubber-stamp rule); unknown actions rejected.

## Frontend (`src/acero/portal/static/`)
`index.html` + `app.js` (vanilla, 126 lines) + `style.css`. Sections: Overview, Research
Programs, Projects, World Model, Reliability, Red Team, Runtime, Review, Publication
Candidates, Decision Center, Settings. The Decision Center shows question, context, evidence,
counter-evidence, uncertainty, cost, risk, learning required, recommendation, and **why NOT to
auto-execute**.

## Security
Local-first; strict **CSP** (`default-src 'self'`, no inline eval), `X-Frame-Options: DENY`,
`X-Content-Type-Options: nosniff`; static files served safely by FastAPI (path-traversal safe);
no secrets/tokens/shell exposed; the JS contains no `eval`/`child_process`.

## Tests
`tests/integration/test_portal.py` (11): shell + security headers, static assets, real-data
views, gate-enforced decisions, no-secrets/no-shell, and DOM structure.

## Limitations
No JS unit tests (Vitest) or browser E2E (Playwright) — replaced by pytest route/DOM/security
tests (documented fallback). The portal renders real backend state; write actions beyond the
Decision Center demo still go through the CLI/API protected services.
