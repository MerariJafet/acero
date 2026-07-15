# Sprint 12 Precheck — Human Scientific Review & Local Publication Preparation

- **Branch:** `feature/acero-sprint-12-scientific-review-publication` (from
  `feature/acero-sprint-11-scientific-reliability` @ `e8faf16`).
- **Baseline:** `make verify` green — 563 tests, ruff + mypy clean.
- **Codex CLI + Docker sandbox:** available (audits / execution unchanged).

## Existing pieces reused
- `ledger/export.py` — `build_dossier`, `export_project` (JSON + Markdown + manifest +
  checksums, all hashed). Local-only.
- `policies/publication.yaml` + `guard.check_publication` — automatic publication is off;
  human review required before export; discovery claims require review; ACERO never claims
  authorship.
- Sprint 11 `reliability/scorecard.py` — `ReadinessLevel`, `PublicationCandidate`
  (ceiling READY_FOR_HUMAN_SCIENTIFIC_REVIEW; never auto-publishes).
- Sprint 9 comprehension gate (`understanding/intervention/comprehension_gate`).
- Sprint 10/11 inline gate + PUBLICATION-stage rules.

## What Sprint 12 adds
- `src/acero/publication/`: a `ReviewDossier` that assembles the scientific record +
  reliability card + comprehension status + gate status + limitations; a structured
  `HumanReviewSession` sign-off (the human must demonstrate understanding of claim / main
  evidence / main counter-evidence / limitations / reliability / what remains to validate);
  and a **gated local export** that refuses to write unless the publication policy, the
  readiness level, the comprehension gate, and the gate status all pass — and never sends
  anything anywhere. Every export carries an AI-use + human-authorship declaration.
- The "promote to publication-ready" mutation is PROTECTED (PUBLICATION stage, inline gate).

## Non-negotiable
Nothing leaves the machine automatically. `DISCOVERY_CONFIRMED` is never granted. The
ceiling is READY_FOR_HUMAN_SCIENTIFIC_REVIEW; the human is the author and final authority.
