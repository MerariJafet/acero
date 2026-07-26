"""Phase-1 fix: per-hypothesis EVA must be specific, traceable and provenance-tagged.

Regression guard for the frontier-run defect where 6 rival hypotheses received an
IDENTICAL vulnerability triple and generic 'la exposición/el outcome' questions, because
the bridge discarded each hypothesis' semantics and never reasoned per claim.
"""

from __future__ import annotations

from acero.epistemic.eva import audit_external
from acero.epistemic.vulnerability import VulnerabilityType
from acero.portal.epistemic_bridge import (
    _claim_from_hypothesis,
    codex_extract,
    heuristic_extract,
)
from acero.questions.question_engine import question_from_vulnerability


class _FakeProvider:
    """Offline stand-in for CodexCliProvider.complete_json."""
    def __init__(self, payload):
        self.payload = payload
        self.prompts = []

    def complete_json(self, prompt, schema, *, temperature=0.0):
        self.prompts.append(prompt)
        return dict(self.payload)

H_A = {
    "id": "hA", "tag": "H0",
    "title": "El valle se desplaza con [Fe/H] sólo tras condicionar por insolación",
    "argument": "La insolación gobierna la fotoevaporación; al fijarla, queda la química.",
    "doubt": "Si el desplazamiento persiste sin condicionar, la hipótesis falla.",
    "competes_with": "fotoevaporación pura sin dependencia de metalicidad",
    "trigger_question": "¿Sobrevive el coeficiente de [Fe/H] al ajustar por insolación?",
    "test_idea": "Comparar la posición del valle por sub-rangos de insolación.",
}
H_B = {
    "id": "hB", "tag": "H5",
    "title": "La señal de [Fe/H] es una ilusión de radios estelares Gaia",
    "argument": "Errores sistemáticos de radio estelar correlacionan con metalicidad.",
    "doubt": "Si una inyección de sesgo no reproduce la pendiente, la hipótesis falla.",
    "competes_with": "todas las hipótesis físicas de dependencia real con [Fe/H]",
    "trigger_question": "¿El valle se mueve con el error de radio y no con la química?",
    "test_idea": "Inyectar sesgos de radio y medir la pendiente resultante.",
}


def test_heuristic_extract_is_specific_per_hypothesis():
    fa, pa = heuristic_extract(H_A)
    fb, pb = heuristic_extract(H_B)
    assert pa == pb == "heuristic"
    # different hypotheses -> different mechanism + assumptions (not a shared template)
    assert fa["mechanism"] != fb["mechanism"]
    assert fa["assumptions"] != fb["assumptions"]
    assert any("insolación" in a or "insolacion" in a for a in fa["assumptions"])
    assert any("inyección" in a or "pendiente" in a or "física" in a or "fisica" in a
               for a in fb["assumptions"])


def test_different_claims_get_different_vulnerabilities():
    ca, *_ = _claim_from_hypothesis(H_A, [])
    cb, *_ = _claim_from_hypothesis(H_B, [])
    va = audit_external(ca).vulnerabilities
    vb = audit_external(cb).vulnerabilities
    # the assumption-derived vulnerabilities must differ in text between claims
    asm_a = {v.description for v in va if v.type == VulnerabilityType.UNVALIDATED_ASSUMPTION}
    asm_b = {v.description for v in vb if v.type == VulnerabilityType.UNVALIDATED_ASSUMPTION}
    assert asm_a and asm_b
    assert asm_a != asm_b
    # enrichment moves each claim past the identical src/rep/ext triple of the old bug
    assert {v.type for v in va} != {VulnerabilityType.SINGLE_SOURCE,
                                    VulnerabilityType.NOT_REPLICATED,
                                    VulnerabilityType.UNJUSTIFIED_EXTRAPOLATION}


def test_enriched_claim_has_more_than_the_generic_triple():
    """A bare/empty hypothesis yields the 3 unconditional vulns; an enriched one yields
    strictly more (mechanism + one-per-assumption)."""
    bare, *_ = _claim_from_hypothesis({"id": "z", "tag": "Z", "title": "algo vago"}, [])
    rich, *_ = _claim_from_hypothesis(H_A, [])
    assert len(audit_external(rich).vulnerabilities) > len(audit_external(bare).vulnerabilities)


def test_provenance_and_confidence_tagging():
    # heuristic default
    _, prov, conf = _claim_from_hypothesis(H_A, [])
    assert prov == "heuristic" and conf == 0.7

    # injected 'llm' extractor
    def fake_llm(h):
        return {"mechanism": "m", "assumptions": ("a1",),
                "exposure_or_input": "X", "outcome_or_prediction": "Y"}, "llm"
    _, prov2, conf2 = _claim_from_hypothesis(H_A, [], extractor=fake_llm)
    assert prov2 == "llm" and conf2 == 1.0

    # a failing extractor degrades to fallback, never raises
    def broken(h):
        raise RuntimeError("codex down")
    c3, prov3, conf3 = _claim_from_hypothesis(H_A, [], extractor=broken)
    assert prov3 == "fallback" and conf3 == 0.5
    assert c3.assumptions  # still enriched via the heuristic fallback


def test_transportability_question_is_not_generic_without_exposure():
    """When exposure/outcome are unknown the question must reference the claim, never the
    'la exposición / el outcome' placeholders."""
    claim, *_ = _claim_from_hypothesis(H_A, [])
    src = next(v for v in audit_external(claim).vulnerabilities
              if v.type == VulnerabilityType.SINGLE_SOURCE)
    q = question_from_vulnerability(src, claim)
    assert "la exposición" not in q.question_text
    assert "el outcome" not in q.question_text
    assert "[Fe/H]" in q.question_text  # references the real claim


def test_confounding_question_uses_real_variables_when_known():
    def fake_llm(h):
        return {"exposure_or_input": "metalicidad [Fe/H]",
                "outcome_or_prediction": "posición del valle"}, "llm"
    claim, *_ = _claim_from_hypothesis(H_A, [], extractor=fake_llm)
    src = next(v for v in audit_external(claim).vulnerabilities
              if v.type == VulnerabilityType.SINGLE_SOURCE)
    q = question_from_vulnerability(src, claim)
    assert "metalicidad [Fe/H]" in q.question_text


def test_codex_extract_with_mock_provider():
    prov = _FakeProvider({"exposure_or_input": "[Fe/H]",
                          "outcome_or_prediction": "posición del valle",
                          "mechanism": "fotoevaporación", "assumptions": ["a1", "a2"],
                          "effect_direction": "positiva", "boundary_conditions": []})
    fields, provenance = codex_extract(H_A, provider=prov)
    assert provenance == "llm"
    assert fields["exposure_or_input"] == "[Fe/H]"
    assert fields["assumptions"] == ["a1", "a2"]
    assert "boundary_conditions" not in fields   # empties dropped
    assert "[Fe/H]" in prov.prompts[0]           # the hypothesis fed to Codex


def test_llm_exposure_outcome_activates_confounding_vulnerability():
    """The heuristic path cannot infer exposure/outcome, so it never surfaces the
    CONFOUNDING vulnerability. The LLM path does -> genuine type-level specificity."""
    def llm(h):
        return {"exposure_or_input": "[Fe/H]", "outcome_or_prediction": "valle",
                "assumptions": ["insolación fija"]}, "llm"
    heuristic_claim, *_ = _claim_from_hypothesis(H_A, [])
    llm_claim, *_ = _claim_from_hypothesis(H_A, [], extractor=llm)
    h_types = {v.type for v in audit_external(heuristic_claim).vulnerabilities}
    l_types = {v.type for v in audit_external(llm_claim).vulnerabilities}
    assert VulnerabilityType.CONFOUNDING not in h_types
    assert VulnerabilityType.CONFOUNDING in l_types
