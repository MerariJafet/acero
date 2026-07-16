"""Review questions (Sprint 19). Not 'do you agree?' — questions that invite real critique."""

from __future__ import annotations

REVIEW_QUESTIONS = (
    "Is there a critical assumption that was not identified?",
    "Does the methodology actually support this conclusion?",
    "Is the evidence independent, or does it share a dataset/pipeline/analyst?",
    "Is there a simpler alternative explanation?",
    "Are the results reproducible from the provided materials?",
    "Is the novelty overstated relative to prior work?",
    "What additional experiment would be necessary to strengthen the claim?",
    "What result would INVALIDATE the interpretation?",
)


def questions_for(role: str | None = None) -> list[str]:
    base = list(REVIEW_QUESTIONS)
    extra = {
        "STATISTICIAN": ["Are multiple comparisons corrected?",
                         "Is the null model appropriate (e.g. red noise vs white)?"],
        "REPRODUCIBILITY_REVIEWER": ["Do the recorded hashes match the shipped artifacts?"],
        "SECURITY_REVIEWER": ["Could any step exfiltrate data or run unsandboxed code?"],
        "ETHICS_REVIEWER": ["Is AI use disclosed and authorship human-only?"],
    }
    return base + extra.get(role or "", [])
