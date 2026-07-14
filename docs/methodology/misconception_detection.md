# Methodology — Misconception Detection

A catalogue of the classic confusions of computational science
(`learner/misconceptions.py`): correlation⇒causation, good fit⇒true mechanism, model
confidence⇒scientific certainty, simulation⇒physical proof, absence of evidence⇒evidence of
absence, recovering an equation⇒discovering a law, analogy⇒equivalence, low p-value⇒true
hypothesis, reproducible⇒correct, complex⇒deep, real data⇒causal conclusion, Codex⇒evidence,
and periodicity⇒mechanism.

Detection is **negation-aware**: a matched conflation that is *denied* by the learner
("an analogy does NOT mean the systems are identical") does not fire — avoiding the obvious
false positive.

## Resolution requires new evidence, not an explanation
A misconception is resolved ONLY by a NEW passing performance task on its concept that no
longer re-triggers the confusion. Reading a correction does not resolve it; a response that
restates the error re-opens it. Severity is HIGH/BLOCKING for the epistemically dangerous
confusions, which block critical decisions via the comprehension gate.
