"""Rule-based falsifiability / actionability / specificity scoring (Sprint 5.5).

These are HEURISTICS, not universal measures. They are deterministic and auditable:
each score is a transparent function of structural features of the candidate
(does it make concrete predictions? are there falsification conditions? are the
required variables named? etc.). No LLM is involved in the score itself.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .candidates import HypothesisCandidate, HypothesisType

# Words that signal a concrete, measurable prediction vs vague hand-waving.
_QUANT = re.compile(r"\b(\d+(\.\d+)?|less|greater|higher|lower|increase|decrease|"
                    r"proportional|linear|exponential|rate|slope|rmse|error|"
                    r"menor|mayor|proporcional|tasa|pendiente)\b", re.IGNORECASE)
_HEDGE = re.compile(r"\b(maybe|might|could|possibly|somehow|in general|generally|"
                    r"tal vez|quizá|podría|de alguna forma)\b", re.IGNORECASE)


@dataclass
class FalsifiabilityScores:
    falsifiability_score: float
    actionability_score: float
    specificity_score: float
    assumption_burden: float
    notes: list[str]

    def as_dict(self) -> dict[str, float]:
        return {
            "falsifiability_score": round(self.falsifiability_score, 4),
            "actionability_score": round(self.actionability_score, 4),
            "specificity_score": round(self.specificity_score, 4),
            "assumption_burden": round(self.assumption_burden, 4),
        }


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def score_candidate(c: HypothesisCandidate) -> FalsifiabilityScores:
    notes: list[str] = []

    # Falsifiability: concrete predictions + explicit falsification conditions +
    # a distinction between support and definitive confirmation.
    has_predictions = len(c.predicted_observations) > 0
    has_falsification = len(c.falsification_conditions) > 0
    fal = 0.0
    if has_predictions:
        fal += 0.4
    else:
        notes.append("No predicted observations -> hard to falsify.")
    if has_falsification:
        fal += 0.4
    else:
        notes.append("No explicit falsification conditions.")
    # A hypothesis that can be tuned to explain anything is LESS falsifiable.
    if c.hypothesis_type == HypothesisType.NULL:
        fal += 0.2  # a null is cleanly falsifiable by a detected effect
    elif "flexible" in (c.statement + c.mechanism).lower() or "poly" in c.statement.lower():
        fal -= 0.15
        notes.append("Flexible/over-parameterised form can explain many outcomes.")
    else:
        fal += 0.2

    # Actionability: measurable variables + feasible required data/tools.
    act = 0.0
    if c.required_variables:
        act += 0.5
    else:
        notes.append("No required variables named -> not directly actionable.")
    if c.predicted_observations:
        act += 0.3
    if c.required_data or c.required_tools:
        act += 0.2

    # Specificity: quantitative language, low hedging.
    text = " ".join([c.statement, c.mechanism, " ".join(c.predicted_observations)])
    quant_hits = len(_QUANT.findall(text))
    hedge_hits = len(_HEDGE.findall(text))
    spec = _clip(0.2 + 0.15 * quant_hits - 0.2 * hedge_hits)
    if hedge_hits:
        notes.append(f"Hedging language detected ({hedge_hits}); reduces specificity.")

    # Assumption burden: more assumptions -> higher burden (worse), saturating.
    n_assume = len(c.assumptions)
    burden = _clip(1.0 - 1.0 / (1.0 + n_assume)) if n_assume else 0.0

    return FalsifiabilityScores(
        falsifiability_score=_clip(fal),
        actionability_score=_clip(act),
        specificity_score=_clip(spec),
        assumption_burden=burden,
        notes=notes,
    )


def is_falsifiable(c: HypothesisCandidate, threshold: float = 0.4) -> bool:
    """A candidate is accepted as falsifiable only if it clears the threshold AND
    has at least one prediction and one falsification condition."""
    if not c.predicted_observations or not c.falsification_conditions:
        return False
    return score_candidate(c).falsifiability_score >= threshold
