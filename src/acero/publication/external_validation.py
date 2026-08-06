"""External validation — the missing engine behind `EXTERNALLY_VALIDATED`.

`assess_readiness(..., externally_validated=...)` has always accepted the flag,
but nothing computed it: external validation was a promise, not a mechanism. This
module makes it earnable and falsifiable.

A third party who received a verification packet runs it, then returns an
ATTESTATION: who they are, that they are independent of the author, WHICH exact
content they checked (the bundle manifest hash), and what happened
(reproduced | partial | failed). ACERO stores attestations per project and only
counts a claim as externally validated when enough DISTINCT, independent human
validators reproduced the SAME content that exists today.

Hard rules (each one exists because it is a way the claim could be faked):
  * The validator must be a human and NOT ACERO/AI — self-validation is not validation.
  * The validator must not be the author — independence is declared and checked.
  * The attestation binds to a bundle hash; if the content changed afterwards the
    attestation goes STALE and stops counting.
  * Only `reproduced` counts. `partial`/`failed` are preserved (negative results
    are evidence too) but never raise readiness.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..core.clock import now_iso
from ..core.config import repo_root
from ..core.ids import new_id

VERDICTS = ("reproduced", "partial", "failed")
_AI_NAMES = {"", "acero", "ai", "codex", "claude", "system", "gpt", "llm"}

# How many independent reproductions are required. One is the literal meaning of
# "externally validated"; raise it for stronger claims.
REQUIRED_VALIDATIONS = max(1, int(os.environ.get("ACERO_EXTERNAL_VALIDATIONS", "1")))


class AttestationError(ValueError):
    """Raised when an attestation is malformed or would be self-validation."""


@dataclass
class ExternalAttestation:
    validator: str                       # human name
    affiliation: str
    bundle_hash: str                     # binds to the EXACT content verified
    verdict: str                         # reproduced | partial | failed
    independent: bool = True             # validator declares no conflict with the author
    notes: str = ""
    contact: str = ""
    id: str = field(default_factory=lambda: new_id("attest"))
    received_at: str = field(default_factory=now_iso)

    def validate(self, *, author: str = "") -> None:
        name = (self.validator or "").strip().lower()
        if name in _AI_NAMES:
            raise AttestationError("el validador debe ser una persona, no ACERO/IA")
        if author and name == author.strip().lower():
            raise AttestationError("el autor no puede validar su propio trabajo")
        if not self.independent:
            raise AttestationError("el validador declaró conflicto de interés")
        if self.verdict not in VERDICTS:
            raise AttestationError(f"veredicto inválido: {self.verdict!r}")
        if not (self.bundle_hash or "").strip():
            raise AttestationError("falta bundle_hash (a qué contenido se ata)")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- storage ------------------------------------------------------------------

def validation_root() -> Path:
    env = os.environ.get("ACERO_VALIDATION_ROOT", "").strip()
    return Path(env) if env else repo_root() / "acero_data" / "validation"


def _file(project_id: str) -> Path:
    d = validation_root()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{project_id}.jsonl"


def record_attestation(project_id: str, att: ExternalAttestation, *,
                       author: str = "") -> dict[str, Any]:
    """Validate then persist. Raises AttestationError on self/AI validation."""
    att.validate(author=author)
    with _file(project_id).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(att.as_dict(), ensure_ascii=False) + "\n")
    return att.as_dict()


def list_attestations(project_id: str) -> list[dict[str, Any]]:
    f = _file(project_id)
    if not f.exists():
        return []
    out: list[dict[str, Any]] = []
    for ln in f.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ln))
        except Exception:  # noqa: BLE001
            continue
    return out


# --- the actual gate ----------------------------------------------------------

def validation_status(project_id: str, *, current_bundle_hash: str | None = None,
                      required: int = REQUIRED_VALIDATIONS) -> dict[str, Any]:
    """Compute whether the project is externally validated *today*.

    Attestations bound to a different bundle hash than the current content are
    reported as STALE and excluded — content changed, so the check no longer applies."""
    atts = list_attestations(project_id)
    fresh: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    for a in atts:
        if current_bundle_hash and a.get("bundle_hash") != current_bundle_hash:
            stale.append(a)
        else:
            fresh.append(a)
    reproduced = [a for a in fresh if a.get("verdict") == "reproduced"]
    validators = sorted({str(a.get("validator", "")).strip().lower() for a in reproduced})
    failed = [a for a in fresh if a.get("verdict") == "failed"]
    ok = len(validators) >= required
    reasons: list[str] = []
    if not ok:
        reasons.append(f"faltan {required - len(validators)} reproducción(es) "
                       f"independiente(s) (hay {len(validators)}/{required})")
    if stale:
        reasons.append(f"{len(stale)} attestation(es) obsoleta(s): el contenido "
                       "cambió tras la validación")
    if failed:
        reasons.append(f"{len(failed)} validador(es) NO pudieron reproducir")
    return {
        "externally_validated": ok,
        "required": required,
        "independent_validators": len(validators),
        "validators": validators,
        "attestations": len(atts),
        "fresh": len(fresh), "stale": len(stale),
        "failed": len(failed),
        "reasons": reasons,
    }


def is_externally_validated(project_id: str, *,
                            current_bundle_hash: str | None = None) -> bool:
    """Boolean to feed `assess_readiness(externally_validated=...)`."""
    return bool(validation_status(
        project_id, current_bundle_hash=current_bundle_hash)["externally_validated"])
