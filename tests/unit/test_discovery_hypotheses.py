"""Sprint 5 tests: generation, falsifiability, diversity."""

from __future__ import annotations

import pytest

from acero.discovery.candidates import HypothesisType
from acero.discovery.diversity import (
    DUP_THRESHOLD,
    analyze,
    classify_pair,
    statement_similarity,
    text_similarity,
)
from acero.discovery.falsifiability import is_falsifiable, score_candidate
from acero.discovery.generation import (
    HYPOTHESIS_JSON_SCHEMA,
    CodexHypothesisGenerator,
)


def test_generates_at_least_8_and_a_null(mock_candidates):
    assert len(mock_candidates) >= 8
    types = {c.hypothesis_type for c in mock_candidates}
    assert HypothesisType.NULL in types
    assert HypothesisType.BASELINE in types
    assert HypothesisType.MECHANISTIC in types


def test_at_least_four_mechanisms(mock_candidates):
    rep = analyze(mock_candidates)
    assert rep.n_mechanisms >= 4
    assert rep.effective_num_hypotheses >= 4


def test_every_candidate_has_a_falsification_condition(mock_candidates):
    for c in mock_candidates:
        assert c.falsification_conditions, c.title


def test_falsifiability_scores_bounded(mock_candidates):
    for c in mock_candidates:
        s = score_candidate(c)
        for v in s.as_dict().values():
            assert 0.0 <= v <= 1.0


def test_hypothesis_without_prediction_not_falsifiable(mock_candidates):
    c = mock_candidates[0].model_copy(deep=True)
    c.predicted_observations = []
    assert not is_falsifiable(c)


def test_duplicate_and_paraphrase_detection(mock_candidates):
    a = mock_candidates[2]  # exponential
    dup = a.model_copy(deep=True)
    dup.id = "hc_dup"
    rep = analyze([a, dup])
    assert rep.duplicates  # identical statement/mechanism -> duplicate
    assert statement_similarity(a, dup) >= 0.82


# text_similarity: la misma señal pero sobre título+enunciado crudos, para
# gatear la APROBACIÓN sin exigir un HypothesisCandidate completo (el payload
# del discovery store no siempre trae 'mechanism').

def test_text_similarity_texto_identico_es_duplicado():
    assert text_similarity("El cover crece por una llave local",
                           "El cover crece por una llave local") >= DUP_THRESHOLD


def test_text_similarity_textos_sin_relacion_no_son_duplicados():
    assert text_similarity("El cover crece por una llave local",
                           "La firma cardiovascular vive en mieloides") < DUP_THRESHOLD


def test_param_only_vs_distinct_relation(mock_candidates):
    a = mock_candidates[2]  # exponential
    b = mock_candidates[4]  # damped -> distinct mechanism
    rel = classify_pair(a, b)
    assert rel.relation in {"distinct", "paraphrase"}


class _FakeCodex:
    name = "codex"
    model = "gpt-x"
    last_usage = {"input_tokens": 10, "output_tokens": 5}

    def __init__(self, payload):
        self._payload = payload

    def complete_json(self, prompt, schema, *, temperature=0.0):
        assert schema is HYPOTHESIS_JSON_SCHEMA
        return self._payload


def test_codex_generator_parses_and_records_provenance(project):
    payload = {"hypotheses": [
        {"title": "Exp", "statement": "y decays exponentially", "hypothesis_type": "MECHANISTIC",
         "mechanism": "exponential relaxation", "assumptions": ["k const"],
         "predicted_observations": ["approaches asymptote"],
         "falsification_conditions": ["non-exponential fits better"], "required_variables": ["t", "y"]},
        {"title": "Null", "statement": "no structure", "hypothesis_type": "NULL",
         "mechanism": "constant mean", "assumptions": [], "predicted_observations": ["mean not beaten"],
         "falsification_conditions": ["any model beats mean"], "required_variables": ["t"]},
    ]}
    gen = CodexHypothesisGenerator(_FakeCodex(payload))
    cands = gen.generate("Q", project_id=project.id, research_question_id="q1", n=2)
    assert len(cands) == 2
    assert cands[0].generation.generator == "codex"
    assert cands[0].generation.token_usage == {"input_tokens": 10, "output_tokens": 5}
    assert cands[0].sources_verified is False  # LLM sources never auto-verified


def test_codex_generator_skips_malformed_items(project):
    payload = {"hypotheses": [
        {"title": "", "statement": "", "hypothesis_type": "NULL", "mechanism": "",
         "assumptions": [], "predicted_observations": [], "falsification_conditions": [],
         "required_variables": []},  # invalid: empty title/statement
        {"title": "Good", "statement": "y is linear", "hypothesis_type": "PREDICTIVE",
         "mechanism": "linear", "assumptions": [], "predicted_observations": ["prop"],
         "falsification_conditions": ["nonlinear better"], "required_variables": ["t"]},
    ]}
    gen = CodexHypothesisGenerator(_FakeCodex(payload))
    cands = gen.generate("Q", project_id=project.id, research_question_id="q1", n=2)
    assert len(cands) == 1  # malformed one skipped, rest kept
    assert cands[0].title == "Good"


def test_codex_generator_requires_structured_provider():
    class NoJson:
        name = "mock"

    with pytest.raises(TypeError):
        CodexHypothesisGenerator(NoJson()).generate("Q", project_id="p", research_question_id="q")
