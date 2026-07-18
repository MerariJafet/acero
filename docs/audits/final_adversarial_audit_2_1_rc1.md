# Final Adversarial Audit — ACERO 2.1.0-rc1

Date: 2026-07-18 · Branch `integration/acero-2.1-program`

## Deterministic audit

- `make verify` → **786 passed**, ruff + mypy + policy + schemas clean.
- `acero acceptance` → 23/23 PASS, RECOMMENDED_FOR_HUMAN_RELEASE_REVIEW.
- `acero security-audit` → 10/10.
- Real browser E2E (Playwright/Chromium) → 13 flows + negatives.
- Transit clean-room (Docker) + standalone package (Docker) → reproduced known
  period, hashes match.
- Burn-in → 120 tasks / 4 processes / no duplication.

## Real Codex adversarial audit

`codex exec --sandbox read-only -c model_reasoning_effort=high` over the transit
science modules, portal auth, and the reproduction package. Codex returned 7
verifiable findings; **all 7 were fixed with regression tests**:

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| 1 | Critical | Standalone `run_all.py` reused a warm `_data` cache → could claim independence without a fresh download | Download into a fresh temp dir every run; only claim `INDEPENDENT_PROCESS_REPRODUCTION` when `fresh_download and not hash_drift` |
| 2 | Critical | `ReproductionRecord.state` always returned `INDEPENDENT_PROCESS_REPRODUCTION`, even with all freshness flags false | `state` downgrades to `NON_ISOLATED_RERUN` unless isolated and drift-free |
| 3 | High | Abstention verdict never checked recovery of the KNOWN ephemeris — could pass on an agreed WRONG period | `decide()` takes `period_recovery_frac`; abstains if it exceeds tolerance |
| 4 | High | Prereg fixed Pipeline A window=101, but nulls/injection used window=51 → gating a non-declared detector | `PIPELINE_A_WINDOW=101` constant used by main pipeline, nulls, and injection |
| 5 | Medium | Nulls only exercised Pipeline A → Pipeline B false positives couldn't affect abstention | Control-star null now checks BOTH pipelines |
| 6 | Medium | False-positive scenarios were computed but never fed into abstention | `decide()` takes `n_false_positive_scenarios`; abstains if > 0 |
| 7 | Low | `/portal/api/logout` was a state-changing POST without session/CSRF gate | logout now requires a valid session + CSRF token |

### Effect on the science

After fixes, the transit program still **ABSTAINS** on the bounded claim — now
citing both the uncontrolled red-noise nulls AND the false-positive scenarios. The
known Kepler-8b period is still recovered (frac error 0.0002); recovery ≠ claim.
No discovery. The fixes make the abstention *stronger* and the reproduction claim
*harder to overstate* — exactly the intended direction.

## Regression tests added

`test_abstention_fires_on_wrong_period_recovery`, `test_abstention_fires_on_false_positive_scenarios`,
`test_nulls_use_declared_detrend_window`, `test_control_null_checks_both_pipelines`,
`test_non_isolated_run_is_downgraded`, and an updated logout-CSRF portal test.

## Verdict

All verifiable adversarial findings corrected with regressions; `make verify`
green (786). No push, no merge, no publication, no discovery.
