# Sprint Lineage — technical timeline

Each sprint is identifiable by its commit, report, source branch, tests, and ADRs. The
chain is linear; the integration branch `integration/acero-v2-program` descends from the
Sprint-12 tip and contains everything below.

```
b9ccb58  master — initial skeleton (untouched)
dacf90b  Sprints 1–4: foundation, ledger, literature, research cycle
1dcb3b3  Docker sandbox, Codex CLI provider, domain plugins
431d326  Wire Codex for real (Sprints 1–4 finalize)
c5c3695  Sprints 5–7: Discovery Engine
076c9dd  Sprint 8: World Model Engine
d5b634d  Sprints 8.5–8.7: Cognitive Discovery Engine
6d04267  Sprints 8.8–8.9: Governing Structure Inference
e44b7af  Sprint 9: Human Understanding Engine + Global Epistemic Gate
10e25e6  Sprint 10: Scientific Domain Labs + inline gate + hybrid grader
e8faf16  Sprint 11: Scientific Reliability & Adversarial Assurance
c416daf  Sprint 12: Human Scientific Review & Local Publication Preparation
   │
   └─▶ integration/acero-v2-program (Sprints 13+ build here)
```

## Per-sprint artifacts
- **Reports:** `docs/sprints/sprint_*_report.md` (one per sprint).
- **ADRs:** `docs/architecture/decisions/ADR-00xx-*.md`.
- **Constitution rules:** rules 14b–14m encode the epistemic guarantees added per sprint.
- **Tests:** `tests/unit`, `tests/property`, `tests/science`, `tests/integration`,
  `tests/security` — 586 passing at consolidation.

## Traceability guarantee
No squash. Every sprint's commit, report, and tests remain individually inspectable on the
integration branch. `git log --oneline` on `integration/acero-v2-program` shows the full
per-sprint chain.
