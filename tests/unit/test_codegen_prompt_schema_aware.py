"""Phase-2 fix: codegen must prefer in-table columns and never encourage name-joins.

Regression guard for the DR25 cross-match defect: the old join_hint told Codex the
"discovery lives in joining catalogs" by 'hostname', which produced a 0.56% match when
koi_smet was already in the KOI table.
"""

from __future__ import annotations

from acero.portal.experiment_factory import build_codegen_prompt

EXP = {"title": "Valle vs [Fe/H]", "what": "pendiente del valle",
       "how": "regresión", "controls": "nulo por permutación",
       "discriminator": "coef [Fe/H]"}
HYP = {"title": "El valle depende de [Fe/H]"}


def _files(n):
    return [{"filename": f"t{i}.csv", "bytes": 100, "sha256": "a" * 12,
             "columns": ["kepid", "koi_smet", "koi_prad"], "n_rows": 4083}
            for i in range(n)]


def test_multi_dataset_prompt_is_anti_antipattern():
    p = build_codegen_prompt(EXP, HYP, _files(2), {})
    # new guidance present
    assert "IDENTIFICADOR ESTABLE" in p
    assert "GUARDARRAÍL DE COBERTURA" in p or "GUARDARRAIL DE COBERTURA" in p
    assert "0.60" in p                       # coverage threshold
    assert "defecto de cross-match" in p
    assert "una sola tabla" in p.lower()     # prefer in-table
    # old antipattern GONE
    assert "el descubrimiento vive en UNIR" not in p
    assert "nombre de la estrella anfitriona" not in p


def test_single_dataset_has_no_join_hint():
    p = build_codegen_prompt(EXP, HYP, _files(1), {})
    assert "INTEGRACIÓN DE DATOS" not in p
    assert "GUARDARRAÍL DE COBERTURA" not in p


def test_real_schema_columns_are_shown():
    p = build_codegen_prompt(EXP, HYP, _files(1), {})
    assert "ESQUEMA REAL" in p
    assert "koi_smet" in p and "kepid" in p
    assert "Usa EXACTAMENTE" in p


def test_feedback_is_included():
    p = build_codegen_prompt(EXP, HYP, _files(1), {}, feedback="columna X no existe")
    assert "INTENTO ANTERIOR FALLÓ" in p
    assert "columna X no existe" in p
