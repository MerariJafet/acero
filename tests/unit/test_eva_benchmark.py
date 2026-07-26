"""The benchmark must reward decisions, not verbosity: the Codex-specific path should
raise confounding coverage and cut generic questions vs the heuristic."""

from __future__ import annotations

from acero.portal.eva_benchmark import benchmark_extractor, compare

HYPS = [
    {"id": "h0", "tag": "H0", "title": "El valle depende de [Fe/H] tras condicionar insolación",
     "argument": "la insolación gobierna la fotoevaporación", "doubt": "si persiste sin condicionar falla"},
    {"id": "h1", "tag": "H1", "title": "La señal de [Fe/H] es detectabilidad Kepler",
     "argument": "el brillo sesga la muestra", "doubt": "si el placebo no la iguala falla"},
]


def _fake_llm(h):
    # a real extractor would infer these; the fake proves the metric moves
    return {"exposure_or_input": "[Fe/H]", "outcome_or_prediction": "posición del valle",
            "assumptions": [f"supuesto propio de {h['tag']}"]}, "llm"


def test_heuristic_baseline_has_no_confounding():
    m = benchmark_extractor(HYPS, None)          # None -> heuristic
    assert m["confounding_coverage"] == 0.0
    assert m["generic_question_rate"] == 0.0     # question template fix already applied


def test_codex_path_raises_confounding_coverage():
    res = compare(HYPS, _fake_llm)
    assert res["heuristic"]["confounding_coverage"] == 0.0
    assert res["codex"]["confounding_coverage"] == 1.0
    # content distinctness (per-claim wording) is the real specificity signal
    assert res["codex"]["content_distinctness"] >= res["heuristic"]["content_distinctness"]


def test_compare_without_codex_returns_none():
    res = compare(HYPS, None)
    assert res["codex"] is None
    assert res["heuristic"]["n_claims"] == 2
