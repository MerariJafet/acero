"""Grader calibration fixtures and metrics.

A labelled fixture set covering the full spectrum of answer quality. We run the hybrid
grader (deterministic authority; semantic optional) and measure agreement with the labels,
false positives (a bad answer marked pass) and false negatives (a good answer marked fail).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .aggregation import GradeVerdict, grade_hybrid

QUESTION = "Explain why recovering an equation from data is not discovering a law."
EXPECTED = ["imposed library", "fit", "not a law", "system identification"]
FORBIDDEN = ["discovered a law of nature", "proves the mechanism"]

_PASS = {GradeVerdict.PASS, GradeVerdict.PASS_WITH_REVIEW}


@dataclass
class Fixture:
    name: str
    response: str
    should_pass: bool


FIXTURES: list[Fixture] = [
    Fixture("literal_correct",
            "The recovered term came from an imposed library and was chosen by its fit, "
            "so this is system identification, not a law.", True),
    Fixture("valid_paraphrase",
            "We picked a catalogue of candidate terms ourselves and kept the ones that "
            "matched the data best; matching data is not the same as finding a natural law.",
            True),
    Fixture("superficial",
            "It is complicated and depends on many things in the model.", False),
    Fixture("keyword_echo", "imposed library fit not a law system identification", False),
    Fixture("contradiction",
            "It is a law because it fits, but it is not a law.", False),
    Fixture("circular",
            "It is not a law because laws are different from what this is, which is not a "
            "law.", False),
    Fixture("partial",
            "The library was imposed by us, so the fit reflects our choices.", False),
    Fixture("creative_correct",
            "Think of it as choosing paints before painting: the palette (our term "
            "library) constrains the picture; a good likeness to the data is a fit, not a "
            "discovered law.", True),
    Fixture("long_but_empty",
            "This is a very deep and profound question about the nature of science and "
            "discovery and the beautiful relationship between data and understanding "
            "across many domains and scales and contexts and it is truly fascinating.",
            False),
    Fixture("short_and_precise", "Fit over an imposed library; not a law.", False),
]


@dataclass
class CalibrationReport:
    n: int
    agreement: float
    false_positives: int
    false_negatives: int
    per_fixture: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"n": self.n, "agreement": self.agreement,
                "false_positives": self.false_positives,
                "false_negatives": self.false_negatives, "per_fixture": self.per_fixture}


def run(provider: Any = None) -> CalibrationReport:
    agree = 0
    fp = 0
    fn = 0
    rows: list[dict[str, Any]] = []
    for fx in FIXTURES:
        g = grade_hybrid(QUESTION, fx.response, EXPECTED, forbidden_elements=FORBIDDEN,
                         provider=provider)
        graded_pass = g.verdict in _PASS
        ok = graded_pass == fx.should_pass
        agree += int(ok)
        if graded_pass and not fx.should_pass:
            fp += 1
        if (not graded_pass) and fx.should_pass:
            fn += 1
        rows.append({"fixture": fx.name, "should_pass": fx.should_pass,
                     "verdict": g.verdict.value, "score": g.score, "correct": ok})
    return CalibrationReport(len(FIXTURES), round(agree / len(FIXTURES), 3), fp, fn, rows)
