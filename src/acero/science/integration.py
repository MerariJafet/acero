"""Bridge: turn a REAL hypothesis + its executed experiments into a GovernanceReport.

This is the live wiring of the Constitution into the existing mission/dossier flow. It is
deliberately DEFENSIVE and READ-ONLY over the discovery objects: it derives an evidence
profile, a (rough but honest) search ledger, an independence ledger and the statistical-
controls checklist from what the experiments actually produced, then runs `govern()`.

The result is attached to the dossier as additive metadata (`governance`). It never
mutates existing behavior; if anything is missing it degrades to an honest, conservative
verdict rather than raising.
"""

from __future__ import annotations

import re
from typing import Any

from .claim_compiler import (
    DESIGN_OBSERVATIONAL,
    EvidenceProfile,
)
from .constitution import GovernanceInput, StatisticalControls, govern
from .independence import IndependenceLedger, IndependenceLevel
from .panel import Panelist, PanelVerdict, Review
from .preregistration import Regime
from .search_ledger import SearchSpaceLedger
from .states import StateEvidence


def _results(exps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in exps if (e.get("result") or {}).get("verdict")]


def _has_null_test(exps: list[dict[str, Any]]) -> bool:
    return any((e.get("result") or {}).get("null_test") for e in exps)


def _build_search_ledger(h: dict[str, Any], exps: list[dict[str, Any]]) -> SearchSpaceLedger:
    lg = SearchSpaceLedger(mission_id=str(h.get("id", "")))
    lg.hypothesis(str(h.get("title", "")))
    for e in exps:
        if e.get("data_source"):
            lg.dataset(str(e["data_source"]))
        lg.model(str(e.get("title", e.get("id", ""))))     # each analysis = a fork
        res = e.get("result") or {}
        for k in (res.get("metrics") or {}):                 # observed metrics = peeks
            lg.metric(str(k))
    return lg


def _build_independence(exps: list[dict[str, Any]]) -> IndependenceLedger:
    led = IndependenceLedger()
    supports = [e for e in exps if (e.get("result") or {}).get("verdict") == "supports"]
    # the factory requires a 2nd implementation for a 'supports' → a Level-1 check
    for e in supports:
        if (e.get("result") or {}).get("cross_checked") or e.get("code_v2"):
            led.add(IndependenceLevel.SAME_ALGO_OTHER_IMPL,
                    f"verificación cruzada 2ª implementación en {e.get('id','')}",
                    agreed=True)
            break
    # supporting evidence from ≥2 distinct datasets = an independent-dataset check
    datasets = {e.get("data_source") for e in supports if e.get("data_source")}
    if len(datasets) >= 2:
        led.add(IndependenceLevel.OTHER_DATASET_COHORT,
                f"apoyo en {len(datasets)} datasets distintos", agreed=True)
    return led


def _controls_from(exps: list[dict[str, Any]]) -> StatisticalControls:
    """Conservatively detect which controls the executed analyses actually reported."""
    blob = " ".join(
        (str((e.get("result") or {}).get("verdict_reason", ""))
         + " " + str((e.get("result") or {}).get("metrics", ""))
         + " " + str((e.get("result") or {}).get("null_test", ""))).lower()
        for e in exps)
    def has(*words: str) -> bool:
        return any(w in blob for w in words)
    return StatisticalControls(
        effect_size=has("effect", "efecto", "delta", "diff", "beta", "slope", "r2", "r²"),
        confidence_intervals=has(" ci", "intervalo", "confidence", "credible", "±",
                                 "ci=", "ic 9", "ic9", " ic ", "ic=", "intervalo de conf"),
        power_analysis=has("power", "potencia"),
        multiplicity_correction=has("fdr", "bonferroni", "bh", "permut", "multipl"),
        sensitivity_analysis=has("sensitiv", "sensibilidad", "robustez", "bootstrap"),
        outlier_check=has("outlier", "atípic"),
        residual_diagnostics=has("residual", "residuo", "qq", "normal"),
        missing_data_handling=has("missing", "faltant", "imput", "na "),
        bootstrap_stability=has("bootstrap"),
        leave_one_group_out=has("leave-one", "logo", "loso", "leave one"),
        stopping_rules=has("stopping", "parada"),
        exclusions_logged=has("exclu", "filtro", "filter"),
        heterogeneity=has("heterogen"),
        pipeline_uncertainty=_has_null_test(exps),
    )


def _draft_text(h: dict[str, Any], standing: str, exps: list[dict[str, Any]]) -> str:
    parts = [str(h.get("title", "")), standing]
    for e in _results(exps):
        parts.append(str((e.get("result") or {}).get("verdict_reason", ""))[:300])
        parts.append(str((e.get("result") or {}).get("claim", ""))[:200])
    return "\n".join(parts)


def _panel_from_critic(latest_crit: dict[str, Any] | None) -> PanelVerdict | None:
    """Map the resident critic (Aristóteles) into ONE panel voice (hostile writer).
    Full plural panel via Codex is a separate, heavier step; this keeps the critic's
    signal visible in the governance report without extra model calls."""
    if not latest_crit:
        return None
    verdict = latest_crit.get("verdict", "prometedor")
    verdict = verdict if verdict in ("solido", "prometedor", "debil", "defectuoso") \
        else "prometedor"
    objs = latest_crit.get("objections", []) or []
    return PanelVerdict([Review(Panelist.HOSTILE_WRITER, verdict, list(objs)[:4],
                                blocking=False, note="crítico residente")])


def govern_dossier(h: dict[str, Any], exps: list[dict[str, Any]], standing: str,
                   latest_crit: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute the GovernanceReport for a hypothesis's current evidence. Returns the
    summary dict (safe to store), or a minimal honest fallback on any error."""
    try:
        results = _results(exps)
        has_null = _has_null_test(exps)
        # exposure/outcome: a rough parse of the claim for the claim template
        title = str(h.get("title", "")) or "el fenómeno"
        m = re.split(r"\b(?:vs\.?|versus|con|sobre|and|y)\b", title, maxsplit=1)
        exposure = (m[0].strip() or title)[:60]
        outcome = (m[1].strip() if len(m) > 1 else "el resultado")[:60]
        profile = EvidenceProfile(
            exposure=exposure, outcome=outcome, regime=Regime.DISCOVERY,
            design=DESIGN_OBSERVATIONAL, causal_identifiable=False,
            independence=_build_independence(exps), has_null_test=has_null)
        gi = GovernanceInput(
            evidence_profile=profile,
            draft_text=_draft_text(h, standing, exps),
            search_ledger=_build_search_ledger(h, exps),
            independence=profile.independence,
            panel=_panel_from_critic(latest_crit),
            state_evidence=StateEvidence(
                hypothesis_formulated=True,
                executed_with_null_test=has_null and bool(results)),
            controls=_controls_from(exps))
        rep = govern(gi)
        out = dict(rep.summary())
        out["exploration"] = gi.search_ledger.summary() if gi.search_ledger else {}
        out["independence"] = profile.independence.summary() if profile.independence else {}
        return out
    except Exception as exc:  # noqa: BLE001 - governance must never kill synthesis
        return {"error": str(exc)[:200], "advance_permitted": False,
                "note": "gobernanza no disponible; degradado a conservador"}
