# Sprint 26 — ACERO 2.1.0-rc1

Date: 2026-07-18 · Branch: `integration/acero-2.1-program`
Status: **complete** · `make verify` green · **no push, no merge, no publication**

## 26.1 Version bump

`2.0.0-rc2 → 2.1.0-rc1` — done only after all gates passed (final acceptance
RECOMMENDED_FOR_HUMAN_RELEASE_REVIEW; `make verify` green). Stale manifest
known-issues rewritten to reflect Sprints 22–25 honestly.

## 26.2 Acceptance matrix

`acero acceptance` (`acero.release.acceptance`) → **23/23 PASS**, no blockers,
verdict RECOMMENDED_FOR_HUMAN_RELEASE_REVIEW. Rows: lineage, migrations, workers,
long-run burn-in, Playwright E2E, auth, accessibility, security, sunspots, transit,
clean-room, standalone reproduction, backup, restore, chaos, red-team, mutation,
review, self-evaluation, external-review, collaboration, publication-review. Each
row states **how** it was verified (inline vs suite vs docker) — no false "re-ran".

## 26.3 Clean install path

Documented + exercised: `make setup` → `acero secrets init` → `acero db upgrade`
→ `make verify` → `make run`. `acero db status` = up_to_date.

## 26.4 Full demo

`acero demo full` (`acero.cli.demo`) drives program → project → question →
hypothesis → experiment → sandbox/gate (valid PASS, invalid BLOCKED) → World Model
→ understanding → reliability → dossier (auto-publish OFF) → review export, through
the SAME protected services. No discovery claimed.

## 26.5 Burn-in

`acero.release.burnin.run_release_burnin`: **120 tasks / 4 real worker processes**,
3 cancellations, 117 done, **no duplication**, DB growth + metrics reported.

## 26.6 Security audit

`acero security-audit` (`acero.release.security_audit`) → **10/10**: password
hashing (no plaintext), session expiry + CSRF, rate limit, CSP + headers, no inline
handlers, no client eval, secret redaction, bundle tamper detection, metrics behind
auth, no hardcoded passwords.

## 26.7 Release docs

`docs/releases/ACERO_2_1_RC1_{REPORT,LIMITATIONS,SECURITY,REPRODUCIBILITY,`
`RESEARCH_PROGRAMS,MIGRATIONS}.md` + `release_manifest.json`.

## Tests (7 new)

`tests/unit/test_release_sprint26.py`: version, security audit all-ok, backup
roundtrip, burn-in no-duplication, demo full (no discovery, gate blocks), manifest
honesty, acceptance matrix all-pass.

## Verdict

ACERO **2.1.0-rc1** with two real scientific programs, a browser-verified portal,
independent-process reproduction, and a green acceptance matrix. Release approval,
push, merge, and publication remain **human** decisions.

Commit: `sprint-26: acero 2.1.0-rc1` · Tag: `v2.1.0-rc1`
