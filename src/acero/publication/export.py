"""Gated local export of a review dossier (Sprint 12).

Refuses to write anything unless ALL of the following hold: the publication policy allows a
human-reviewed local export, the readiness level is READY_FOR_HUMAN_SCIENTIFIC_REVIEW, the
comprehension gate passed, the gate status is complete, there are no unresolved
contradictions, and a human (not ACERO) approved the review. It writes ONLY to a local
directory (JSON + Markdown + manifest + checksums) and NEVER sends anything anywhere. Every
export carries an AI-use + human-authorship declaration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.errors import PolicyViolation
from ..core.hashing import hash_json, hash_text
from ..policies.guard import PolicyGuard
from ..reliability.scorecard import ReadinessLevel
from .dossier import ReviewDossier
from .review import HumanReviewSession


class ExportBlocked(RuntimeError):
    """Raised when an export is attempted before all preconditions are met."""

    def __init__(self, blockers: list[str]) -> None:
        self.blockers = blockers
        super().__init__("export blocked: " + "; ".join(blockers))


AI_USE_DECLARATION = (
    "AI assistance disclosure: ACERO (an AI system) assisted with computation, analysis, "
    "and drafting. ACERO is NOT an author and claims NO scientific authorship or discovery. "
    "All results are computational and require independent human scientific review and, "
    "where applicable, external experimental validation before any publication."
)


@dataclass
class ExportDecision:
    allowed: bool
    blockers: list[str] = field(default_factory=list)
    readiness: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "blockers": self.blockers,
                "readiness": self.readiness}


def evaluate_export(dossier: ReviewDossier, review: HumanReviewSession | None, *,
                    guard: PolicyGuard | None = None) -> ExportDecision:
    """Compute whether a local export is permitted — never mutates, never writes."""
    guard = guard or PolicyGuard()
    blockers: list[str] = []

    # 1. publication policy: human review required, no auto-publish.
    try:
        guard.check_publication(human_reviewed=bool(review and review.approved))
    except PolicyViolation as exc:
        blockers.append(f"policy: {exc}")

    # 2. readiness must be the human-review ceiling.
    if dossier.readiness != ReadinessLevel.READY_FOR_HUMAN_SCIENTIFIC_REVIEW.value:
        blockers.append(f"readiness is {dossier.readiness}, need "
                        f"{ReadinessLevel.READY_FOR_HUMAN_SCIENTIFIC_REVIEW.value}")

    # 3. comprehension + gate + contradictions.
    if dossier.comprehension_status not in ("sufficient", "PASS", "PASS_WITH_SUPPORT"):
        blockers.append("human comprehension not demonstrated")
    if dossier.gate_status != "complete":
        blockers.append("gate status incomplete")
    if dossier.unresolved_contradictions > 0:
        blockers.append(f"{dossier.unresolved_contradictions} unresolved contradiction(s)")

    # 4. an approved human review (not ACERO) that BINDS to the exact dossier content.
    if review is None or not review.approved:
        blockers.append("no approved human review")
    elif review.reviewer.strip().lower() in ("acero", "ai", "codex", "system"):
        blockers.append("reviewer must be a human")
    elif not review.matches(dossier):
        blockers.append("review does not bind to the current dossier "
                        "(content changed after approval)")

    # 5. a claim and its limitations must be present.
    comp = dossier.completeness()
    if not comp["has_central_claim"]:
        blockers.append("no central claim")
    if not comp["has_limitations"]:
        blockers.append("no stated limitations")

    return ExportDecision(allowed=not blockers, blockers=blockers,
                          readiness=dossier.readiness)


def _markdown(dossier: ReviewDossier, review: HumanReviewSession) -> str:
    d = dossier.as_dict()
    lines = [f"# Review dossier — {d['project']}", "",
             "> " + AI_USE_DECLARATION, "",
             f"**Central claim (inference level: {d['inference_level']}):** "
             f"{d['central_claim']}", "",
             f"**Readiness:** {d['readiness']} · **Replication:** {d['replication_status']} "
             f"· **Gate:** {d['gate_status']}", "",
             "## What this is NOT"]
    lines += [f"- {x}" for x in d["disclaimers"]]
    lines += ["", "## Supporting evidence "
              f"({d['independent_support_count']} independent group(s))"]
    lines += [f"- [{e['stance']}] {e['summary']}" for e in d["supporting_evidence"]] or ["- none"]
    lines += ["", "## Counter-evidence"]
    lines += [f"- {e['summary']}" for e in d["counter_evidence"]] or ["- none"]
    lines += ["", "## Limitations"]
    lines += [f"- {x}" for x in d["limitations"]] or ["- none stated"]
    lines += ["", "## Open questions / remaining external validation"]
    lines += [f"- {x}" for x in d["open_questions"]] or ["- none"]
    lines += ["", "## Human review",
              f"- Reviewer: {review.reviewer}",
              f"- Decision: {review.decision.value if review.decision else '—'}",
              f"- Content hash: {review.content_hash}"]
    return "\n".join(lines) + "\n"


def export_dossier(dossier: ReviewDossier, review: HumanReviewSession | None,
                   out_dir: str | Path, *, guard: PolicyGuard | None = None
                   ) -> dict[str, Any]:
    """Write the review package locally IFF permitted. Raises ExportBlocked otherwise."""
    decision = evaluate_export(dossier, review, guard=guard)
    if not decision.allowed:
        raise ExportBlocked(decision.blockers)
    assert review is not None

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = {"dossier": dossier.as_dict(), "review": review.as_dict(),
               "ai_use_declaration": AI_USE_DECLARATION, "exported_at": now_iso(),
               "destination": "local_only", "auto_published": False}
    json_text = json.dumps(payload, indent=2, ensure_ascii=False)
    md_text = _markdown(dossier, review)
    (out / "review_dossier.json").write_text(json_text, encoding="utf-8")
    (out / "review_dossier.md").write_text(md_text, encoding="utf-8")
    files: dict[str, str] = {"review_dossier.json": hash_text(json_text),
                             "review_dossier.md": hash_text(md_text)}
    manifest = {"dossier_id": dossier.id, "review_id": review.id,
                "exported_at": payload["exported_at"], "destination": "local_only",
                "files": files, "payload_hash": hash_json(payload)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False),
                                       encoding="utf-8")
    (out / "checksums.txt").write_text(
        "\n".join(f"{h}  {n}" for n, h in files.items()) + "\n", encoding="utf-8")
    return {"dir": str(out), "auto_published": False,
            "files": list(files), "manifest": str(out / "manifest.json")}
