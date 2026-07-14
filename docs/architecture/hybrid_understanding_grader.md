# Hybrid Understanding Grader (Sprint 10)

Combines deterministic rules + rubrics + accumulated evidence (the AUTHORITY) with a Codex
semantic ADVISORY layer. Codex can spot valid paraphrase, nuance, contradiction, and
circular reasoning — but never certifies mastery, and the final grade is always
rule-governed.

## Pipeline (`understanding/grading/`)
`response → deterministic rubric → forbidden claims → contradiction → consistency →
semantic advisory → aggregation → grade + uncertainty + knowledge-state proposal`.

- **deterministic.py** — rubric coverage + concept coverage; can PASS or FAIL alone.
- **semantic.py** — `SemanticAssessment` (paraphrase validity, coherence, missing nuance,
  circular, contradiction, unsupported, transfer, suggested range, rationale, **cited
  fragments** that must actually appear in the response). Never a bare grade; optional.
- **contradiction.py / consistency.py** — deterministic self-contradiction, prohibited
  claims (misconception catalogue), copy/reversal vs prior answers.
- **aggregation.py** — the policy.

## Rules that always hold
- Deterministic authority: prohibited claim / self-contradiction / red flags → HARD_FAIL,
  never rescued by Codex.
- Codex may lift a genuine paraphrase (different words) to **PASS_WITH_REVIEW** — never to a
  clean PASS or mastery — and only when it cites a real fragment (Codex-audit fix).
- Disagreements are recorded, not hidden; uncertainty rises with disagreement / no semantic.
- If the semantic layer is unavailable, the deterministic result stands.

## Calibration & adversarial (10.34–10.35)
`calibration.py`: 10 labelled fixtures (literal/paraphrase/superficial/echo/contradiction/
circular/partial/creative/empty/precise) → agreement, **zero false positives**. `audit.py`:
prompt injection, rubric copy, grandiosity, empty confidence, wrong-question, repeat — none
earns a clean PASS, even with a maximally lenient (mock) semantic layer.
