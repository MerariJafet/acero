# Production Readiness Scorecard — Iteration 0 (baseline)

Date: 2026-07-18 · Version 2.1.0-rc1 · Branch `integration/acero-2.1-program`
Framework: `acero production report` (`src/acero/production/`)

## Total: **74.0 / 100** (goal ≥95)

| Cat | Area | Score | Max | Key evidence / gap |
|-----|------|-------|-----|--------------------|
| A | Architecture & integrity | 8.5 | 10 | boundaries + write-surface test, Alembic, idempotent runtime, mypy clean |
| B | Quality & tests | 9.5 | 12 | 795 tests, real Playwright E2E, mutation, benchmarks; coverage unmeasured |
| C | Security | **12.0** | 15 | strong static (auth/CSRF/CSP/tamper, audit 10/10) — **capped by rule 3** (no dynamic tests on a real deploy) |
| D | Reliability & operations | 8.0 | 12 | workers, burn-in, backup+restore proven; no deployed health/alerts/rollback |
| E | Product & UX | 6.5 | 10 | authenticated portal, WCAG basics; onboarding minimal; no 2nd-user test |
| F | Scientific rigor | 13.5 | 15 | prereg, competing hypotheses, nulls, **real abstention**, calibration, no discovery |
| G | Data & provenance | 5.5 | 8 | manifests + SHA-256 + licenses; no Data Fabric / drift yet |
| H | CI/CD & deployment | **3.0** | 8 | workflow authored but **not run independently** (no remote) — rule 4 |
| I | Maintainability & docs | 4.5 | 5 | ADRs, sprint/release/methodology/audit docs |
| J | External validation | **3.0** | 5 | bundles + playbook ready; **no external reviewer** — rule 5 |

## Applied rules
- **Rule 3** → C capped at 12/15 (no dynamic security on a real deployment).
- **Rule 4** → H capped at 5/8 (no independent CI run); awarded 3 (workflow not yet executed).
- **Rule 5** → J capped at 3/5 (no external human reviewer).
- **Rule 10** → ≥95 impossible now; missing: `deployment_tested`, `rollback_tested`,
  `ci_green`, `dynamic_security`, `independent_score_review`.

## Why ≥95 is currently blocked (honest)
Four of the five missing Rule-10 preconditions require infrastructure/human
decisions, not more local code:
1. **Deployment + rollback + dynamic security** need ACERO running on a real host.
   The available VM (`vm-merari-landing`, 2 vCPU / **958 MB RAM, ~274 MB free** /
   20 GB disk **1.4 GB free** / Python 3.10 / no Docker) **cannot host ACERO's
   Python-3.12 numpy/scipy/astropy stack** without a capacity upgrade → a cost
   decision (`BLOCKED_BY_HUMAN_DECISION`). See `docs/production/PRODUCTION_DEPLOYMENT.md`.
2. **Independent CI** needs a hosted remote/runner (no remote exists) → human decision.
3. **External review** needs a real external person → human decision.
4. **Independent score review** — pending an independent audit agent pass.

## Confidence & recommendation
Confidence: high (score derived from executed checks + verified infra recon).
Recommendation: proceed with all **non-blocked** improvements (Data Fabric,
Mission Engine, deliberation, 3rd program, deeper statistics, observability,
onboarding, coverage) which lift A/B/D/E/F/G/I honestly; surface the deployment /
CI / external-review decisions to the human. Realistic autonomous ceiling without
those human decisions is ≈ **82–86 / 100**.
