# Methodology — Evidence of Understanding

Understanding is measured through DIFFERENT tasks, never one kind alone:
explain in own words, predict before result, solve a similar case, detect an error,
identify an assumption, interpret a graph, modify code, derive a result, compare models,
transfer to another domain, propose a falsification, state what cannot be concluded.

Each `UnderstandingEvidence` records the task, the response, the expected elements, a
deterministic rubric score (partial credit), the grader (rubric / human / codex-advisory),
the rubric version, and the research context. A single correct answer never produces
definitive mastery — the state machine requires breadth of evidence kinds.

## Grading integrity
`assessment/grading.py` scores by coverage of expected reasoning elements and penalises
forbidden (wrong) claims. After an adversarial Codex audit, it also flags **keyword echo**
(a response that merely restates the rubric words with no explanatory content of its own),
so a thin answer cannot score a full pass. Codex may offer a second opinion, recorded
separately as `codex_advisory`; it never overrides the deterministic rubric.
