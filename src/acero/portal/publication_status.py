"""Publication status — "¿qué me falta para publicar esta investigación?"

`publication/export.py` already knew how to refuse an export, but that verdict was
invisible: you could not see, per investigation, how far you are from the ceiling
(READY_FOR_HUMAN_SCIENTIFIC_REVIEW) or which specific thing is blocking.

This composes a checklist from what the project ACTUALLY contains — dossiers,
experiment verdicts, reproduction evidence, critic objections, and third-party
attestations — and returns the blockers in plain Spanish. It is read-only: it
computes a status, it never approves anything and never publishes.

Honest limitation: a blocker like "falta revisión humana registrada" stays until a
human review session is bound to the dossier — by design, ACERO cannot clear it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..publication.external_validation import (
    ExternalAttestation,
    list_attestations,
    record_attestation,
    validation_status,
)

CEILING = "READY_FOR_HUMAN_SCIENTIFIC_REVIEW"


def _store(sf: Any = None):
    from ..discovery.store import DiscoveryStore
    from ..ledger.db import default_session_factory
    from ..ledger.service import ResearchLedger
    s = sf or default_session_factory()
    return DiscoveryStore(s, ResearchLedger(s))


def _check(ok: bool, label: str, detail: str = "") -> dict[str, Any]:
    return {"ok": bool(ok), "label": label, "detail": detail}


def dossier_checklist(store: Any, project_id: str, d: dict[str, Any],
                      exps: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-dossier readiness checklist + blockers, from real stored fields."""
    claim = str(d.get("claim") or d.get("synthesis") or "").strip()
    against = d.get("evidence_against") or []
    for_ = d.get("evidence_for") or []
    critic_block = bool(d.get("blocked_by_critic"))
    readiness = str(d.get("readiness") or "").strip() or "NOT_READY"

    # reproduction evidence: agentic experiments that reproduced net-free
    reproduced = [e for e in exps
                  if ((e.get("result") or {}).get("agentic") or {}).get("reproduced") is True]
    supports = [e for e in exps if (e.get("result") or {}).get("verdict") == "supports"]

    val = validation_status(project_id)

    checks = [
        _check(bool(claim), "Afirmación central declarada",
               claim[:120] or "el dossier no tiene claim/síntesis"),
        _check(bool(against), "Contraevidencia / limitaciones declaradas",
               f"{len(against)} en contra · {len(for_)} a favor"),
        _check(not critic_block, "Sin objeciones bloqueantes del revisor",
               "el crítico bloquea este dossier" if critic_block else "sin bloqueo"),
        _check(bool(reproduced), "Reproducción computacional verificada",
               f"{len(reproduced)} experimento(s) reprodujeron sin red"),
        _check(val["externally_validated"], "Validación externa independiente",
               "; ".join(val["reasons"]) or f"{val['independent_validators']} validador(es)"),
        _check(readiness == CEILING, f"Nivel de madurez = {CEILING}",
               f"actual: {readiness}"),
        # ACERO cannot clear this one for you — that is the point.
        _check(False, "Revisión humana aprobada y vinculada al dossier",
               "pendiente: solo tú puedes aprobar (ACERO nunca se auto-aprueba)"),
    ]
    blockers = [c["label"] for c in checks if not c["ok"]]
    return {"dossier_id": d.get("id"), "hyp_tag": d.get("hyp_tag", ""),
            "claim": claim[:220], "readiness": readiness, "status": d.get("status"),
            "checks": checks, "blockers": blockers,
            "can_export": not blockers,
            "n_supports": len(supports), "n_reproduced": len(reproduced),
            "validation": val}


def project_publication_status(project_id: str, sf: Any = None) -> dict[str, Any]:
    """Everything the publication panel needs for one investigation."""
    store = _store(sf)
    dossiers = store.list_objects(project_id, kind="dossier")
    exps = store.list_objects(project_id, kind="experiment")
    reports = [dossier_checklist(store, project_id, d, exps) for d in dossiers]
    val = validation_status(project_id)
    exportable = [r for r in reports if r["can_export"]]
    return {
        "project_id": project_id,
        "n_dossiers": len(dossiers),
        "dossiers": reports,
        "validation": val,
        "attestations": list_attestations(project_id),
        "exportable": len(exportable),
        "ceiling": CEILING,
        "note": ("ACERO nunca publica solo ni declara descubrimientos: el techo es "
                 "'listo para revisión científica humana'. Tú apruebas, tú compartes."),
    }


# --- actions ------------------------------------------------------------------

def build_packet_for_experiment(project_id: str, experiment_id: str, *,
                                title: str = "", make_zip: bool = True) -> dict[str, Any]:
    """Package one experiment's artifacts so a third party can verify it offline."""
    from ..publication.verification_packet import build_packet
    from .experiment_factory import artifacts_root
    src = artifacts_root() / experiment_id
    if not src.is_dir():
        raise FileNotFoundError(f"no hay artefactos para {experiment_id}")
    # ship only the small, meaningful files (never the raw data dumps)
    include = [p.name for p in sorted(src.iterdir())
               if p.is_file() and p.suffix in {".py", ".json", ".txt", ".sh", ".md"}]
    dest = Path(str(src)) / "_packet"
    info = build_packet(src, dest, title=title or f"ACERO · {experiment_id}",
                        include=include, make_zip=make_zip)
    info["project_id"] = project_id
    info["experiment_id"] = experiment_id
    return info


def ingest_attestation(project_id: str, payload: dict[str, Any], *,
                       author: str = "") -> dict[str, Any]:
    """Record a returned attestation.json from an external validator."""
    att = ExternalAttestation(
        validator=str(payload.get("validator") or ""),
        affiliation=str(payload.get("affiliation") or ""),
        bundle_hash=str(payload.get("bundle_hash") or ""),
        verdict=str(payload.get("verdict") or ""),
        independent=bool(payload.get("independent", True)),
        notes=str(payload.get("notes") or ""),
        contact=str(payload.get("contact") or ""))
    rec = record_attestation(project_id, att, author=author)
    return {"ok": True, "attestation": rec,
            "validation": validation_status(project_id)}
