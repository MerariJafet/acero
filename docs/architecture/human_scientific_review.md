# Human Scientific Review & Local Publication Preparation (Sprint 12)

The culmination of Sprints 1–11: everything ACERO produces is assembled into a
human-reviewable dossier and can be exported LOCALLY only after an explicit human sign-off —
never published automatically. The human is the author and the final scientific authority.

## Package `src/acero/publication/`
- **dossier.py** — `ReviewDossier`: central claim + inference level, supporting AND counter
  evidence (with independent-group counting so duplicated support is visible), the Sprint-11
  reliability card + readiness, replication/comprehension/gate status, limitations, open
  questions, required external review, and explicit disclaimers of what it is NOT.
- **review.py** — `HumanReviewSession`: the reviewer must acknowledge central claim, main
  evidence, main counter-evidence, limitations, reliability, and what remains to validate
  externally, demonstrate comprehension, AND state a reason. Decisions:
  `APPROVE_FOR_EXTERNAL_REVIEW / REQUEST_CHANGES / REJECT` — there is deliberately no
  APPROVE_FOR_PUBLICATION. An AI reviewer cannot approve. A content hash binds the approval
  to the exact reviewed dossier.
- **export.py** — `evaluate_export` / `export_dossier`: refuses to write unless the
  publication policy (human-reviewed, no auto-publish), readiness
  (READY_FOR_HUMAN_SCIENTIFIC_REVIEW), comprehension, gate status, contradiction count, and a
  binding human approval all hold. Writes JSON + Markdown + manifest + checksums to a LOCAL
  directory and NEVER sends anything anywhere. Every export carries an AI-use +
  human-authorship declaration.
- **engine.py** — orchestrates reliability → dossier → review → export decision.

## Benchmark
`benchmarks/review_gauntlet.py` — 6 cases: export blocked when not reviewed / not ready /
comprehension insufficient / AI reviewer / unresolved contradiction; and one approved LOCAL
export (auto_published always False).

## Honesty
`READY_FOR_HUMAN_SCIENTIFIC_REVIEW` is the ceiling and means neither publication nor
discovery. `DISCOVERY_CONFIRMED` is never granted. Computational results are not experimental
validation. Nothing leaves the machine automatically.
