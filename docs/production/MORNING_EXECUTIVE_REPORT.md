# ACERO — Morning Executive Report

Date: 2026-07-18 · Session: Production Readiness — Iteration 0

## Executive summary
- **State:** ACERO 2.1.0-rc1, `make verify` green (795 tests). Production scoring
  framework built; **honest score 71.5/100** (independent-audited down from a 74.0
  self-assessment).
- **Infra (verified live):** merari-acero.com is live on GCP VM `vm-merari-landing`
  (I have SSH + git-deploy access). It runs the landing + Kronos + Nexus.
- **Deployment blocker (real):** the VM (2 vCPU / 958 MB RAM, ~300 MB free / 1.4 GB
  disk free / Python 3.10 / no Docker) **cannot host ACERO's Py3.12 science stack**.
  → `BLOCKED_BY_HUMAN_DECISION` (upgrade VM or separate host — a cost call).
- **Landing button:** "Investigación ACERO" + honest info page built, verified
  locally, pushed to the landing production **source** — but **NOT yet live**
  (build + PM2 restart on the shared prod VM held for human review). 404 today.
- **CRITICAL security finding** on the live landing: hardcoded plaintext password in
  `login/page.tsx` (client bundle). Rotate + move to server auth.

## Work completed (this session)
- `src/acero/production/` — 100-pt weighted rubric + 10 enforced scoring rules + audit
  + `acero production score|audit|report`. 9 tests. Rules provably hold the score
  <95 without deployment / CI / external review.
- Independent Audit Agent (separate, read-only) verified evidence is real (no
  inflation), tightened B/D/I → 71.5.
- `/ready` route (DB-at-head readiness); `/health` `/version` already present.
- `.github/workflows/ci.yml` authored (honestly not yet run — no remote).
- Landing: `InvestigacionACEROSection` + `/investigacion-acero` page (Next 16),
  built clean, verified desktop+mobile with Playwright.
- Verified infra recon; documented deployment plan + blocker + rollback runbook.

## Iterations
- Iteration 0 → 74.0 self → **71.5 independent-audited**. See
  `docs/production/scorecards/production_score_iteration_0.md`,
  `docs/production/iterations/iteration_00.md`.

## Production
- Deployment: **not performed** (VM capacity blocker). Landing source deployed;
  final build+restart pending human review. Rollback documented (RTO 1–2 min).
- Health/ready routes: added (code). Not yet exercised on a real deploy.

## Evidence
- Commits (ACERO): `ce8ef91`, `f7ffa41`, `375981e`. Landing: `72b0388` (pushed).
- `make verify` 795 green; `acero production report` 71.5; `acero security-audit`
  10/10; independent audit result; local Playwright screenshots
  (`docs/production/evidence/`).

## Pending (real)
1. **VM build + PM2 restart** to make the button live (held for review) — or owner runs it.
2. **Deployment host decision** (upgrade/separate) to unblock the ≥95 path.
3. **Rotate the leaked landing password**; move auth server-side.
4. **Independent CI hosting** and a **real external reviewer** (both human decisions).
5. Non-blocked backlog to raise the honest score toward the ~85 autonomous ceiling
   (Data Fabric, deeper statistics, 3rd program, observability, onboarding).

## Human decisions only
Publication of science; reviewer selection; VM cost/upgrade; rotating the landing
credential; making the site publicly promote ACERO. None taken by the agent.

## Honesty
No deployment faked. Score is real and independently reviewed. The button is
**not** claimed live (it isn't yet). No scientific discovery claimed. No push to
ACERO master; ACERO master untouched.
