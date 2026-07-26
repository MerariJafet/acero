"""P4: EVA internal gate — attack the hypothesis BEFORE spending experiments.
Blocks fatal flaws (vague/reformulation/HARKing/confirm-only/trivial); conservative
offline (never blocks when it cannot assess); force overrides."""
from __future__ import annotations

from acero.portal.epistemic_bridge import internal_eva

H = {"id": "h", "tag": "H0", "title": "El valle depende de [Fe/H] tras condicionar insolación",
     "argument": "la insolación gobierna la fotoevaporación", "doubt": "si persiste sin condicionar falla",
     "trigger_question": "¿sobrevive [Fe/H] al ajustar insolación?", "test_idea": "regresión con nulo"}


class _Flags:
    def __init__(self, **over):
        base = {k: False for k in (
            "is_reformulation_of_known", "too_vague_to_refute", "arose_after_seeing_results",
            "simpler_explanation_exists", "dataset_cannot_answer", "experiment_confirm_only",
            "effect_would_be_trivial", "depends_on_single_decision")}
        base.update(over)
        base["reason"] = "test"
        self.payload = base

    def complete_json(self, prompt, schema, *, temperature=0.0):
        return dict(self.payload)


def test_offline_never_blocks():
    g = internal_eva(H, use_ai=False)
    assert g["proceed"] is True
    assert g["provenance"] == "heuristic"
    assert g["blockers"] == []


def test_vague_hypothesis_is_blocked():
    g = internal_eva(H, use_ai=True, provider=_Flags(too_vague_to_refute=True))
    assert g["proceed"] is False
    assert any("vaga" in b for b in g["blockers"])
    assert g["provenance"] == "llm"


def test_confirm_only_is_blocked():
    g = internal_eva(H, use_ai=True, provider=_Flags(experiment_confirm_only=True))
    assert g["proceed"] is False


def test_clean_hypothesis_proceeds_even_with_llm():
    g = internal_eva(H, use_ai=True, provider=_Flags())   # all flags false
    assert g["proceed"] is True and g["provenance"] == "llm"


def test_failing_provider_degrades_to_proceed():
    class _Boom:
        def complete_json(self, *a, **k):
            raise RuntimeError("codex down")
    g = internal_eva(H, use_ai=True, provider=_Boom())
    assert g["proceed"] is True and g["provenance"] == "fallback"


def test_known_reformulation_does_not_block_but_warns():
    # a known-but-testable relationship must NOT block (novelty concern, not validity)
    g = internal_eva(H, use_ai=True, provider=_Flags(is_reformulation_of_known=True))
    assert g["proceed"] is True
    assert any("conocido" in w for w in g["warnings"])


def test_trivial_effect_blocks():
    g = internal_eva(H, use_ai=True, provider=_Flags(effect_would_be_trivial=True))
    assert g["proceed"] is False
