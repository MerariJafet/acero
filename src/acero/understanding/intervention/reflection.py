"""Reflection prompts after a prediction is revealed or a decision is made.

Reflection turns a surprise into a model update: which assumption failed, what changed in
the researcher's mental model. It never rewrites the prediction (that stays locked).
"""

from __future__ import annotations

from ..models import HumanPrediction


def reflection_prompts(pred: HumanPrediction) -> list[str]:
    if pred.comparison is None:
        return ["Reveal the result first, then reflect."]
    if pred.comparison == "correct":
        return ["Which assumption made your prediction right?",
                "Would it still hold under more noise or a different regime?"]
    if pred.comparison == "partial":
        return ["Which part did you get right, and which assumption was off?",
                "What evidence would have sharpened the prediction?"]
    return ["Which specific assumption failed?",
            "What did this result teach you about the mechanism vs. the fit?",
            "How does your mental model change now?"]
