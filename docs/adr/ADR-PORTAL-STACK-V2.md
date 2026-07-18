# ADR: Portal Frontend Stack V2

- Status: **Accepted**
- Date: 2026-07-18
- Sprint: 23
- Deciders: Merari (human), ACERO build agent (proposer)

## Context

Sprint 23 requires turning the current portal into a professional, secure,
browser-verifiable local scientific application with authentication, a full
research workspace flow, a Decision Center, a World Model explorer that scales to
10,000+ nodes, scientific result cards, reliability/runtime centers, WCAG basics,
and **real Playwright E2E**.

Measured state of the existing portal (source of truth, not estimate):

| Asset | LOC | Notes |
|-------|-----|-------|
| `static/app.js` | 148 | vanilla ES, one `VIEWS` dict, `fetch`-based API client |
| `static/index.html` | 20 | SPA shell (`#nav`, `#view`) |
| `static/style.css` | 25 | minimal |
| `portal/app.py` | 212 | FastAPI router; actions reuse protected services |
| **Total client** | **193** | zero build step; `script-src 'self'`; no `eval` |

Duplication is low (`kv`/`panel`/`esc` helpers). No component framework. No
client state beyond `current`. Interaction today: nav + two forms (World Model
query, Decision). Graphs: none rendered client-side (server aggregates).

## Decision drivers

- **LOC / complexity today**: small (193 client LOC). Growth is real in Sprint 23
  (auth, workspace, cards, paginated explorer) but bounded — still a
  read-mostly control panel, not a data-entry-heavy app.
- **Local-first / offline**: ACERO is explicitly local-first. The portal must run
  with `make run` and no network.
- **Security surface**: Sprint 26 mandates a dependency + supply-chain audit. A
  React+Vite toolchain introduces `node_modules` (hundreds of transitive
  packages), a build artifact that can diverge from source, and pressure to relax
  CSP for bundler runtimes. That is a *cost*, not a benefit, for an audited
  scientific tool.
- **Single quality gate**: `make verify` today is Python-only (ruff + mypy +
  policy + schemas + pytest). React would add a second lint/type/test/build
  toolchain to maintain and gate.
- **Testability**: Playwright drives either stack identically (real browser over
  HTTP). Python route/DOM tests already cover the backend. So testability does
  **not** favor React.
- **Graphs**: the World Model explorer must **not** load the full graph; it
  paginates server-side. Heavy client-side graph libs are therefore unnecessary;
  progressive expansion + tables suffice and are more accessible.
- **Accessibility**: WCAG basics (landmarks, focus, ARIA, keyboard) are achieved
  with semantic HTML — framework-independent.
- **Migration cost**: rewriting 193 LOC into React is cheap in isolation, but the
  *ongoing* cost (build pipeline, deps, second toolchain, CSP) is permanent.

## Options

### Option A — Modular vanilla JS (ES modules), no build step  ✅ chosen
Split the monolithic `app.js` into ES modules loaded natively by the browser
(`<script type="module">`): `api` client (CSRF-aware), `auth`, `router`,
`components` (cards/tables/kv), and one module per view. Keep `script-src 'self'`,
no bundler, no `node_modules` shipped.

- **Pros**: zero build; offline; minimal dependency/supply-chain surface; keeps a
  single Python quality gate; strict CSP unchanged; native ES modules give real
  componentization and testable units; Playwright still exercises a real browser.
- **Cons**: no reactive state library (managed with explicit render + small
  helpers); no compile-time type checking of client code (mitigated with focused
  Playwright E2E + `"use strict"`).

### Option B — React + TypeScript + Vite
- **Pros**: components, typed client, ecosystem, easier for a large team.
- **Cons**: adds a Node build chain + `node_modules` supply-chain surface directly
  against Sprint 26's dependency audit; a second toolchain in `make verify`; build
  artifact ≠ source; CSP pressure; offline story more complex; migration + ongoing
  cost unjustified for a single-maintainer, read-mostly, local-first control panel
  of this size.

## Decision

**Option A.** Keep vanilla but modularize into native ES modules with a real
client architecture (Portal Shell, API Client, Auth, and per-section views),
semantic accessible HTML, and server-side pagination for the World Model. This is
**not** "keep it because it's there" — it is the choice that best fits the
measured size, the local-first/offline requirement, the strict CSP, the
supply-chain audit obligation, and the single Python quality gate. React is
explicitly rejected as premature for a 193-LOC read-mostly control panel where the
stated benefits (typing, components) are either achievable in vanilla ES modules
or outweighed by the permanent toolchain/dependency cost.

## Consequences

- Client becomes `static/js/{api,auth,router,components}.js` + `static/js/views/*`.
- Playwright + Chromium are **dev/test** dependencies only (never shipped to the
  running portal); recorded in the precheck and Sprint 23 report.
- If the portal later needs rich client-side interactivity beyond control-panel
  scope, revisit this ADR — the modular boundaries make a future migration
  view-by-view rather than big-bang.
- WCAG basics implemented in semantic HTML; `axe-core` run via Playwright if
  feasible.

## Revisit triggers

- Client LOC crosses ~3–4k with heavy shared interactive state.
- Multiple concurrent human editors / true multi-tenancy (explicitly out of scope
  now).
- A need for client-side rich graph visualization that tables cannot serve.
