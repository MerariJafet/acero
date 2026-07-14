"""Publication-stage gate rules (9.26).

Automatic publication remains forbidden by policy; this is the *future* gate that a human
export must clear. It blocks AI authorship, unverified citations, irreproducible results,
incomplete methodology, missing data/code, undeclared AI use, exaggerated novelty,
unreviewed conflicts of interest, discovery claims without human review, and insufficient
human comprehension of the central conclusion.
"""

from __future__ import annotations

from ..models import GateRule, Severity, Stage
from .common import rule

S = Stage.PUBLICATION

RULES: list[GateRule] = [
    rule("no_ai_authorship", S, "ai_listed_as_author", expect=False,
         detail="AI is listed as an author",
         remediation="the human researcher is the author; AI is a tool"),
    rule("citations_verified", S, "all_citations_verified", expect=True,
         detail="not all citations are verified",
         remediation="verify every citation against an ingested source"),
    rule("results_reproducible", S, "reproducible", expect=True,
         detail="results are not reproducible",
         remediation="ship a reproducible bundle"),
    rule("methodology_complete", S, "methodology_complete", expect=True,
         detail="methodology is incomplete",
         remediation="document the full methodology"),
    rule("data_code_available", S, "data_or_code_missing_unjustified", expect=False,
         detail="data or code is missing without justification",
         remediation="include data/code or justify their absence"),
    rule("ai_use_declared", S, "ai_use_undeclared", expect=False,
         detail="AI use is undeclared where policy requires it",
         remediation="declare AI assistance"),
    rule("novelty_not_exaggerated", S, "novelty_exaggerated", expect=False,
         detail="novelty is exaggerated",
         remediation="state novelty conservatively with prior-work search"),
    rule("coi_reviewed", S, "conflict_of_interest_unreviewed", expect=False,
         detail="a conflict of interest is unreviewed", severity=Severity.WARNING,
         remediation="review and declare conflicts of interest"),
    rule("discovery_human_reviewed", S, "discovery_claim_without_human_review",
         expect=False,
         detail="a discovery claim lacks human review",
         remediation="require human review for any discovery claim"),
    rule("central_conclusion_understood", S, "human_understands_central_conclusion",
         expect=True,
         detail="human comprehension of the central conclusion is insufficient",
         remediation="complete comprehension assessment of the central conclusion"),
]
