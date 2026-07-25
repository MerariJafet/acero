"""Live wiring of the Constitution into the dossier synthesis (offline)."""

from __future__ import annotations

from acero.science.integration import govern_dossier


def _exp(verdict, reason, data_source, null=True, metrics=None):
    return {"id": f"exp_{verdict}", "title": f"análisis {data_source}",
            "data_source": data_source,
            "result": {"verdict": verdict, "verdict_reason": reason,
                       "metrics": metrics or {"effect": 0.3},
                       "null_test": {"passed": True} if null else None,
                       "claim": reason}}


def test_governance_flags_overclaim_in_generated_text():
    h = {"id": "h1", "title": "metilación vs parkinson"}
    exps = [_exp("supports", "esto demuestra que causa la enfermedad", "GSE111629")]
    g = govern_dossier(h, exps, standing="APOYADA")
    assert g["n_overclaims"] >= 1            # 'demuestra' / 'causa' caught
    assert g["advance_permitted"] is False
    assert "asociado" in g["allowed_claim"].lower()


def test_governance_reports_exploration_debt():
    h = {"id": "h2", "title": "radio planetario vs metalicidad"}
    exps = [_exp("supports", "correlación r=0.2", f"cat_{i}") for i in range(4)]
    g = govern_dossier(h, exps, standing="APOYADA")
    assert "exploration" in g and g["exploration"]["effective_comparisons"] >= 1
    # 4 distinct datasets among 'supports' → an independent-dataset check registered
    assert g["independence"]["independent_dataset"] is True


def test_governance_degrades_without_null_test():
    h = {"id": "h3", "title": "X vs Y"}
    exps = [_exp("supports", "diferencia observada", "D1", null=False)]
    g = govern_dossier(h, exps, standing="APOYADA")
    # no null test → cannot advance, honest
    assert g["advance_permitted"] is False


def test_governance_clean_case_can_advance():
    h = {"id": "h4", "title": "X vs Y"}
    exps = [_exp("supports",
                 "efecto delta=0.3, IC 95%, corrección FDR, exclusiones registradas "
                 "(filtro), bootstrap, sensibilidad, residuos, potencia, heterogeneidad, "
                 "imputación de faltantes, leave-one-group-out, regla de parada",
                 "D1")]
    g = govern_dossier(h, exps, standing="APOYADA con controles")
    assert not g["critical_controls_missing"]
    assert g["allowed_claim"]                 # a claim was compiled


def test_governance_never_raises_on_garbage():
    g = govern_dossier({}, [], standing="")
    assert "advance_permitted" in g
