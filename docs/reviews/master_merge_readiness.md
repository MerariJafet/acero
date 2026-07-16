# Master Merge Readiness (Sprint 21)

```
MasterMergeReadiness
- commits_included: 20 (Sprints 1–20 + 18/19), all ancestors of RC2 a814fb8
- commits_missing: 0
- tests: 701 passing (ruff + mypy clean, make verify green on the rehearsal branch)
- migrations: create_all + schema_version v3 (Alembic is Sprint 22, not a merge blocker)
- conflicts: 0 (clean fast-forward — master is a linear ancestor of RC2)
- blockers: NONE (critical)
- security: gate in-line universal, tokens, sandbox, no auto-publication, write-surface test
- reproducibility: signed RC1 baseline; backup/restore verified; datasets hashed/gated
- human_review_required: YES — the final merge to master is a HUMAN decision
```

## The merge is prepared but NOT executed
The agent did NOT touch `master` (still `b9ccb58`). A rehearsal branch
`review/acero-v2-master-merge` proves the fast-forward is clean and green.

## Exact command for the human to run the final merge (after reviewing the diff)
```bash
# from the repo root, on a clean tree:
git checkout master
git merge --ff-only feature/acero-v2-rc2-sprints-18-19
# (fast-forward; no merge commit, preserves per-sprint history and tags)
# then, if desired:  git tag -a v2.0.0 -m "ACERO v2.0.0"   # only when a human approves a release
# DO NOT push automatically.
```
If a merge COMMIT is preferred over fast-forward (to mark the consolidation explicitly):
```bash
git checkout master
git merge --no-ff feature/acero-v2-rc2-sprints-18-19 -m "Merge ACERO v2 (Sprints 1–20 + 18–19)"
```

## Blockers before a v2.0.0 (non-rc) release
- Alembic migrations (Sprint 22), professional portal + browser E2E (Sprint 23), a second real
  science program (Sprint 24), independent replication package (Sprint 25). These are 2.1
  goals, NOT merge blockers for consolidating the RC2 history.
