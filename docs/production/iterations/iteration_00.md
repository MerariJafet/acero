# Iteration 00 — Baseline + scoring framework

- **iteration_number:** 0
- **baseline_score:** n/a (first)
- **findings:** no production scoring existed; deployment feasibility unknown; CI
  absent; VM capacity unverified.
- **selected_improvements:** build rubric + scoring framework (`acero.production`);
  add `/ready`; author CI workflow; verify real infrastructure.
- **implementation_commits:** `ce8ef91` (framework + iteration 0).
- **tests_added:** `tests/unit/test_production_readiness.py` (9).
- **tests_failed:** none (795 pass).
- **security_findings:** none new (security_audit 10/10).
- **scientific_findings:** none new (transit abstains; no discovery).
- **production_findings:** VM cannot host ACERO's Py3.12 science stack
  (RAM/disk/Python) → deployment `BLOCKED_BY_HUMAN_DECISION` (host/cost); no
  independent CI (no remote); no external reviewer.
- **score_after:** 74.0 self → **71.5 after independent audit**.
- **remaining_blockers:** deployment host (cost), independent CI hosting, external
  human review. Autonomous ceiling ≈ 82–86.
- **evidence:** `docs/production/scorecards/production_score_iteration_0.md`,
  `docs/production/PRODUCTION_DEPLOYMENT.md`, independent-audit result.

## Human decisions received (this session)
- Deploy host: **upgrade VM / separate host** (user will provision; deploy becomes
  possible on a proper host).
- Landing: **add "Investigación ACERO" button + honest info page now**.
- Focus: **all** (raise score, deployment readiness, security, onboarding).
