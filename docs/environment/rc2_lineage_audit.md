# RC2 Lineage Audit (Fase 0, Programa 2.1)

## Verified topology
The RC2 branch (`feature/acero-v2-rc2-sprints-18-19` @ `a814fb8`) is the **complete linear v2
history**: 20 commits ahead of `master` (`b9ccb58`, untouched), with every sprint commit an
ancestor of the RC2 tip (verified with `git merge-base --is-ancestor`, not by report).
`integration/acero-v2-program` (`887fc45`) is fully contained in RC2.

## Sprint matrix (all Integrated-in-RC2 = ✅; Integrated-in-master = ❌ by design)

| Commit | Sprint(s) | Conflicts vs master |
|---|---|---|
| dacf90b,1dcb3b3,431d326 | 1–4 | none (linear) |
| c5c3695 | 5–7 | none |
| 076c9dd | 8 | none |
| d5b634d | 8.5–8.7 | none |
| 6d04267 | 8.8–8.9 | none |
| e44b7af | 9 | none |
| 10e25e6 | 10 | none |
| e8faf16 | 11 | none |
| c416daf | 12 | none |
| 0352f3f | 13 | none |
| 33bdf92 | 14 | none |
| f0a0c6d | 16 | none |
| 4a712c0 | 15 | none |
| 7b0cbdf | 17 | none |
| 887fc45 | 20 (rc1) | none |
| a72990c | 18 | none |
| d36248b | 19 | none |
| a814fb8 | rc2 | none |

## Consequence
Because RC2 is already a single linear branch containing Sprints 1–20, there is NO merge to
perform to consolidate — `integration/acero-2.1-program` is created from RC2 (`a814fb8`) and
inherits the full per-sprint history (no squash, tags `v2.0.0-rc1`/`v2.0.0-rc2` preserved). A
merge into `master` is a **fast-forward** (master is an ancestor of RC2). `master` stays
untouched; the exact human command is prepared in the Sprint 21 report.

## Baseline
`make verify` green — 701 tests. `acero release accept` → 7 gauntlets pass.
