# RC2 Precheck — Sprints 18 & 19 (freeze RC1)

- **Base commit:** `887fc45` (v2.0.0-rc1). **Tag created (local only):** `v2.0.0-rc1`. Not pushed.
- **Branch:** `feature/acero-v2-rc2-sprints-18-19` (from `887fc45`). Master untouched.
- **Baseline:** `make verify` green — **656 tests**, ruff + mypy clean.
- **Version at freeze:** 2.0.0-rc1 (kept as the stable baseline; RC1 content NOT modified).

## RC1 modules (33 packages under src/acero/)
core, policies, epistemology, provenance, ledger, literature, evaluation*, sandbox,
experiment, pedagogy, llm, cli, api, domains, discovery, world_model, cognitive, inference,
understanding, epistemic_gate, reliability, publication, benchmarks, runtime, program, portal,
studies, release, plus vestigial hypothesis/integrations/knowledge.
(* the existing `evaluation` package is retrieval-metrics; Sprint 18's self-evaluation engine
is a NEW `selfeval` package to avoid confusing the two.)

## RC1 benchmarks
Hidden Dynamics, Cross-Domain Structural Discovery, Governing Dynamics, Human Understanding,
Multi-Domain Reasoning, Reliability Gauntlet, Publication Review, Chaos Runtime, Stellar
Variability, Gate Bypass.

## RC1 known issues (carried; see ACERO_V2_RC1_LIMITATIONS.md)
- Sprints 18 & 19 not yet implemented (this branch fills them).
- Portal: no Vitest/Playwright (pytest route/DOM/security tests).
- Worker drains synchronously (no long-lived daemon).
- Single astronomy dataset; no Alembic (idempotent create_all + schema versioning v3).

## RC2 plan
Sprint 18 (Scientific Capability Evaluation Engine) → Sprint 19 (External Review Preparation)
→ full audit + fixes → bump to 2.0.0-rc2. No push, no merge, no external contact, no publish.
