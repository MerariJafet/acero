# Methodology — Hybrid Grading

Deterministic authority + Codex advisory. See
`docs/architecture/hybrid_understanding_grader.md` for the pipeline. Key invariants:

- The deterministic layer alone can PASS/FAIL; hard signals (prohibited claim,
  self-contradiction, keyword echo) are HARD_FAIL and never rescued.
- Codex advisory may lift a genuine paraphrase to PASS_WITH_REVIEW **only** with a cited
  fragment that appears in the response, and never to a clean PASS or mastery.
- MASTERED still requires a full deterministic pass PLUS multiple distinct evidence kinds
  (the learner state machine) — the grader proposes, it does not certify mastery.
- Disagreements are recorded; uncertainty is reported; a missing semantic layer degrades to
  the deterministic result.
