"""Socratic questioning bound to the real project state.

Codex may PROPOSE questions, but a deterministic validator keeps only those that
reference real entities of the project (concepts, variables, equations, code, results).
A question that mentions nothing in the record is discarded — questions must bite on
something concrete, not float free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class SocraticKind(str, Enum):
    CLARIFICATION = "clarification"
    ASSUMPTION = "assumption"
    EVIDENCE = "evidence"
    ALTERNATIVE = "alternative"
    CONSEQUENCE = "consequence"
    LIMIT = "limit"
    FALSIFICATION = "falsification"
    TRANSFER = "transfer"
    METACOGNITION = "metacognition"


@dataclass(frozen=True)
class SocraticQuestion:
    kind: SocraticKind
    text: str
    references: tuple[str, ...]        # real entities the question touches


@dataclass
class ProjectEntities:
    concepts: list[str]
    variables: list[str]
    equations: list[str]
    code: list[str]
    results: list[str]

    def all_tokens(self) -> set[str]:
        toks: set[str] = set()
        for group in (self.concepts, self.variables, self.equations, self.code,
                      self.results):
            for item in group:
                for w in re.split(r"[\s/().,=+*-]+", item.lower()):
                    if len(w) > 2:
                        toks.add(w)
        return toks


def default_questions(ent: ProjectEntities) -> list[SocraticQuestion]:
    """A deterministic seed set grounded in the project's own entities."""
    var = ent.variables[0] if ent.variables else "the output"
    qs: list[SocraticQuestion] = [
        SocraticQuestion(SocraticKind.FALSIFICATION,
                         "What observation would most weaken this hypothesis?",
                         tuple(ent.results[:1])),
        SocraticQuestion(SocraticKind.EVIDENCE,
                         "Why is the model with the lowest RMSE not necessarily the best?",
                         ("rmse",)),
        SocraticQuestion(SocraticKind.ASSUMPTION,
                         "Which recovered term depends on the library we imposed?",
                         tuple(ent.equations[:1] or ["library"])),
        SocraticQuestion(SocraticKind.CONSEQUENCE,
                         f"What missing variable could produce autocorrelated residuals "
                         f"in {var}?",
                         (var,)),
        SocraticQuestion(SocraticKind.LIMIT,
                         "What is the difference between periodicity and mechanism here?",
                         ("periodicity",)),
    ]
    return [q for q in qs if validate(q, ent)]


def validate(q: SocraticQuestion, ent: ProjectEntities) -> bool:
    """Keep a question only if it references a real entity/token of the project."""
    tokens = ent.all_tokens()
    text_tokens = {w for w in re.split(r"\W+", q.text.lower()) if len(w) > 2}
    ref_hit = any(any(t in tokens for t in re.split(r"\W+", r.lower()) if len(t) > 2)
                  for r in q.references)
    return ref_hit or bool(text_tokens & tokens)


def filter_codex_questions(candidates: list[dict], ent: ProjectEntities
                           ) -> list[SocraticQuestion]:
    """Validate Codex-proposed questions against real project entities."""
    out: list[SocraticQuestion] = []
    for c in candidates:
        try:
            kind = SocraticKind(c.get("kind", "clarification"))
        except ValueError:
            kind = SocraticKind.CLARIFICATION
        q = SocraticQuestion(kind, str(c.get("text", "")).strip(),
                             tuple(c.get("references", [])))
        if q.text and validate(q, ent):
            out.append(q)
    return out
