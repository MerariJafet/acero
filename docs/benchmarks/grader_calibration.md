# Grader Calibration Benchmark

Source: `understanding/grading/calibration.py` + `audit.py`.

**Calibration** — 10 labelled fixtures spanning literal-correct, valid paraphrase,
superficial, keyword echo, contradiction, circular, partial, creative-correct,
long-but-empty, short-and-precise. Metrics: agreement, false positives, false negatives.
Result (no semantic layer): agreement 0.9, **0 false positives**. The remaining false
negative is a valid paraphrase in entirely different words, which the *semantic* layer
recognises (→ PASS_WITH_REVIEW).

**Adversarial** — prompt injection, rubric copy, grandiosity, empty confidence,
wrong-question, repeat-prior. None earns a clean PASS, even with a maximally lenient mock
semantic layer (Codex never unlocks mastery).

```bash
acero learner grader-benchmark
```
