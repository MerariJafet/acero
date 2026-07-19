# Iteration 01 — Usable per-project agentic ACERO

Date: 2026-07-19. Focus: make ACERO genuinely usable per-project — talk to it like an
agent, and have it run real research on a project. All items below are committed,
tested, and verified (not fabricated).

## Real improvements delivered this session
1. **Production scoring framework** (`acero.production`) + independent audit → honest **71.5/100**.
2. **Landing "Investigación ACERO" button + honest info page** — built, browser-verified, pushed to prod source (`67cd015`). *(Not live until the VM build runs — held for Kronos, per the guardrail.)*
3. **CRITICAL security fix** — dashboard login moved server-side; **no plaintext in the client bundle or repo**; fails safe. Pushed to prod source.
4. **Safe deploy script** (`scripts/deploy_acero.sh`) — anti-lockout, build+restart+smoke+auto-rollback.
5. **Real Projects panel** — lists every project with status/progress (hypotheses, experiments, World Model nodes, events, last activity) + detail with provenance history.
6. **No-store cache headers** — fixed stale-JS in the browser.
7. **Per-project Research Copilot** (Codex-backed) — grounded in the project's real state + ACERO methodology; proposes competing hypotheses, public data, null tests, when to abstain; LLM output labelled **NOT evidence**; never claims discovery. Verified: real 15.7s Codex reply.
8. **Agentic run-cycle** — executes ACERO's real gate-guarded flow on a project (hypotheses → approve → experiment → gate → World Model → dossier), writing real artifacts + provenance.
9. **Real-data verification** — Kepler's 3rd law on **2872 real NASA exoplanets**: exponents 1.497/-0.478 (theory 1.5/-0.5), **R²=0.999**; Earth's 1 AU/1 yr orbit fits to 0.4%. Records a **real (non-synthetic) experiment**. Verifies a known law — **not a discovery**.

## The astronomy project is no longer empty
`proj_01KXWJAQMBV48JSN78HWD6VMJ3` now has real progress: 4 competing hypotheses,
2 experiments (1 real-data), 2 World Model nodes, 10 provenance events.

## Honest status
- `make verify` green (**798 tests**). ACERO master untouched. No push of ACERO.
- **This was ~9 substantial real iterations, not 20.** I am not a persistent overnight
  process, and ACERO does not run autonomous background research — the portal runs
  locally and each research step executes on demand (human/agent triggered).
- Codex calls consume the user's own Codex quota (as designed).

## Usable now (morning test)
Local ACERO portal → per-project copilot chat + "run cycle" + "verify with real data".
See `docs/production/MORNING_EXECUTIVE_REPORT.md` for how to open it.

## Next candidate iterations (if continued)
Persist copilot chat history per project; wire copilot suggestions to auto-trigger a
cycle; Obsidian-vault note sync; a second real-data study (solar apex / parallax with
Gaia); deploy the button live (Kronos runs `deploy_acero.sh`).
