"""Literature-stage gate rules (9.17)."""

from __future__ import annotations

from ..models import GateRule, Severity, Stage
from .common import rule

S = Stage.LITERATURE

RULES: list[GateRule] = [
    rule("citation_exists", S, "all_citations_resolvable", expect=True,
         detail="a cited source does not exist / is not retrievable",
         remediation="remove or replace the unverifiable citation"),
    rule("fragment_supports_claim", S, "fragments_support_claims", expect=True,
         detail="a cited fragment does not support the claim it is attached to",
         remediation="quote a passage that actually supports the claim"),
    rule("retraction_respected", S, "uses_retracted_source", expect=False,
         detail="a retracted source is used as if valid",
         remediation="drop the retracted source"),
    rule("preprint_not_consensus", S, "preprint_as_consensus", expect=False,
         detail="a preprint is presented as established consensus", severity=Severity.WARNING,
         remediation="label preprints as non-peer-reviewed"),
    rule("commercial_source_flagged", S, "commercial_source_as_primary", expect=False,
         detail="a commercial source is used as primary evidence without a warning",
         severity=Severity.WARNING,
         remediation="flag commercial provenance and seek independent support"),
    rule("no_duplicate_evidence", S, "duplicate_counted_as_independent", expect=False,
         detail="the same source is counted as independent evidence twice",
         remediation="deduplicate before counting independent support"),
]
