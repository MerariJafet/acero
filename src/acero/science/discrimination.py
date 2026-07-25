"""Rival hypotheses + discriminating tests + expected information gain.

The single most important idea in the reviewer's dictamen: a critique that only points out
a flaw is not science. Every question must end by asking *what observation would
distinguish the rival explanations?* — the scientific equivalent of an "exploit". A test
is DECISIVE only if it has DIFFERENTIAL predictions (the rivals predict different things);
a test that can only confirm the favourite is not decisive.

Expected information gain ranks tests by how much they can move belief across the rival
set, so cheap, high-discrimination probes come first.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class RivalSet:
    """A question must spawn rivals, not a single favourite hypothesis."""
    question_id: str
    main: str
    null: str
    rivals: tuple[str, ...]                    # ≥2 plausible alternatives
    shared_predictions: tuple[str, ...] = ()
    differential_predictions: dict[str, str] = field(default_factory=dict)  # hyp -> exclusive prediction

    def all_hypotheses(self) -> list[str]:
        return [self.main, self.null, *self.rivals]

    def n_hypotheses(self) -> int:
        return len(self.all_hypotheses())

    def is_well_posed(self) -> bool:
        """At least two rivals beyond main+null, and some differential prediction."""
        return len(self.rivals) >= 2 and bool(self.differential_predictions)


def shannon_entropy(priors: list[float]) -> float:
    """Entropy (bits) of a prior distribution over hypotheses — the maximum information a
    perfectly discriminating test could extract."""
    tot = sum(p for p in priors if p > 0) or 1.0
    h = 0.0
    for p in priors:
        if p > 0:
            q = p / tot
            h -= q * math.log2(q)
    return h


@dataclass
class DiscriminatingTest:
    test_id: str
    question_id: str
    description: str
    outcome_favors: dict[str, str]     # hypothesis -> outcome that would favour it
    null_family: str = ""
    confounders: tuple[str, ...] = ()
    negative_controls: tuple[str, ...] = ()
    required_data: str = ""
    independence_possible: bool = False
    computational_cost: float = 0.3    # 0..1
    experimental_cost: float = 0.3

    @property
    def decisive(self) -> bool:
        """Decisive iff it separates ≥2 hypotheses by DIFFERENT predicted outcomes."""
        return len(set(self.outcome_favors.values())) >= 2

    def expected_information_gain(self, priors: list[float] | None = None) -> float:
        """Bits of belief the test can move: entropy over the hypotheses it discriminates,
        scaled to 0 if it is not decisive (cannot separate anything)."""
        if not self.decisive:
            return 0.0
        k = len(self.outcome_favors) or 1
        pri = priors or [1.0] * k
        return shannon_entropy(pri[:k]) if len(pri) >= k else shannon_entropy([1.0] * k)

    def value_per_cost(self, priors: list[float] | None = None) -> float:
        cost = 1.0 + (self.computational_cost + self.experimental_cost)
        return self.expected_information_gain(priors) / cost

    def summary(self) -> dict[str, object]:
        return {"decisive": self.decisive,
                "expected_information_gain": round(self.expected_information_gain(), 3),
                "value_per_cost": round(self.value_per_cost(), 3),
                "independence_possible": self.independence_possible,
                "n_hypotheses_separated": len(set(self.outcome_favors.values()))}


def design_discriminating_test(rivals: RivalSet, test_id: str = "",
                               required_data: str = "",
                               independence_possible: bool = False
                               ) -> DiscriminatingTest:
    """Turn a rival set into a test whose outcomes favour DIFFERENT hypotheses. If the
    rival set has no differential predictions, the resulting test is (correctly) not
    decisive — the caller must sharpen the hypotheses first."""
    favors: dict[str, str] = {}
    for hyp, pred in rivals.differential_predictions.items():
        favors[hyp] = pred
    # ensure the null has an outcome too (the 'no effect' branch)
    favors.setdefault(rivals.null, "sin efecto / dentro del nulo")
    return DiscriminatingTest(
        test_id=test_id or f"test.{rivals.question_id}",
        question_id=rivals.question_id,
        description=f"prueba que separa: {', '.join(rivals.differential_predictions) or 'n/a'}",
        outcome_favors=favors, required_data=required_data,
        independence_possible=independence_possible)


def rank_tests(tests: list[DiscriminatingTest],
               priors: list[float] | None = None) -> list[DiscriminatingTest]:
    """Sequential strategy: highest information-per-cost first (cheap decisive probes)."""
    return sorted(tests, key=lambda t: -t.value_per_cost(priors))
