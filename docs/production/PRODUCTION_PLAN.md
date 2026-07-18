# ACERO Production Readiness — Plan & Improvement Loop

Goal: a verified Production Readiness Score **≥95/100** — or the honest maximum
achievable before an unavoidable human decision, with blockers marked.

## Methodology
- Weighted 100-point rubric (`acero.production.rubric`), 10 hard scoring rules that
  cap categories/global score absent executed evidence, deployment, independent CI,
  and real external review.
- Loop: **AUDIT → SCORE → GAPS → PRIORITIZE → DESIGN → IMPLEMENT → TEST → RED-TEAM
  → FIX → VALIDATE → RE-SCORE → REPEAT.** Append-only iteration records; criteria
  are never changed retroactively to inflate a score.
- Independent Audit: a separate agent scores without implementing.
- Commands: `acero production score|audit|report`.

## Iteration 0 (baseline) — DONE
Score **74.0/100**. Framework built, `/health` `/ready` `/version` added, CI
workflow authored, infra verified. See
`docs/production/scorecards/production_score_iteration_0.md`.

## Blockers requiring a human decision (cannot be faked to 95)
1. **Deployment host** — the current VM cannot run ACERO's Py3.12 science stack
   (RAM/disk/Python). Needs a VM upgrade or a separate host (**cost**).
2. **Independent CI** — no hosted remote/runner exists (hosting decision).
3. **External human review** — needs a real external reviewer.
These gate `deployment_tested`, `rollback_tested`, `dynamic_security`, `ci_green`,
and category J — i.e. Rule 10. Autonomous ceiling ≈ **82–86** without them.

## Non-blocked backlog (raises the score honestly, autonomously)
Ordered by rubric leverage:
1. **Scientific Data Fabric** (G 5.5→~7.5): registry, CAS, lineage, drift, cards.
2. **Deeper statistics** (F 13.5→~14.5): multiple-testing/FDR, power, sensitivity,
   uncertainty propagation, leakage checks — applied to SILSO + Kepler-8 + a 3rd program.
3. **Third-domain program** (F/G): a safe public computational domain (e.g. chemical
   kinetics), full prereg→nulls→abstention→dossier→clean-room. No discovery.
4. **Long-Horizon Mission Engine** (A/D): missions, budgets, checkpoints, morning report.
5. **Multi-agent deliberation** (F): structured roles, SHARED_MODEL_DEPENDENCY, no
   false consensus.
6. **Observability + ops** (D 8→~10): structured logs, request IDs, metrics, health
   on a (staging) run, documented rollback + RTO/RPO, encrypted backup rotation + DR drill.
7. **Quality** (B 9.5→~11): coverage measurement, flakiness sweep, clean-install test.
8. **Onboarding / UX** (E 6.5→~8): guided tour, sample project, glossary, operator
   + researcher guides, simulated second-user E2E.
9. **Production code review** (A/I): structured per-domain review; subagents review
   modules they did not implement.
10. **External review prep** (J, capped at 3 until a real reviewer): expert matrix,
    drafts, traceability, import test.

## Deferred / staged (need the host decision first)
Landing "Investigación ACERO" entry point, VM deploy (staging→prod), HTTPS
subdomain, dynamic security scan on the deploy, rollback drill on the host.
See `docs/production/PRODUCTION_DEPLOYMENT.md`.

## Definition of done (unchanged, honest)
≥95 needs: zero criticals, all P0 gates, deployment tested, rollback tested, CI
green, dynamic security, real E2E, docs, independent score review. Until the host
+ CI + external-review decisions are made, the mission reports the real number and
marks `BLOCKED_BY_HUMAN_DECISION` — never a fabricated 95.
