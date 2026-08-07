"""Offline tests for MathExplorer — everything injectable, no LLM/sandbox needed."""

from __future__ import annotations

from acero.science.explorer_ledger import ExplorerLedger
from acero.science.math_explorer import MathExplorer, _extract


def _mem_ledger():
    """In-memory ledger (store=None never touches disk) for offline tests."""
    return ExplorerLedger(store=None)


class _StubProv:
    """Deterministic provider: diverge → approaches, assemble → code, synth → hypothesis."""

    def __init__(self, *, viable: bool = True) -> None:
        self._viable = viable

    def available(self) -> bool:
        return True

    def complete_json(self, prompt: str, schema, temperature: float = 0.0):
        if "SINTETIZADOR" in prompt:
            return {"claim": "área = base × altura",
                    "why": "los tres enfoques coinciden en base*altura",
                    "formal_claim": {"kind": "identity", "lhs": "b*h", "rhs": "h*b"}}
        # diverge
        return {"approaches": [
            {"method": "numerico", "plan": "muestrear puntos", "tools_used": ["montecarlo_area"],
             "why_might_work": "cuenta área"},
            {"method": "calculo", "plan": "integrar", "tools_used": ["sym_integrate"],
             "why_might_work": "integral de constante"},
            {"method": "algebra", "plan": "descomponer", "tools_used": [],
             "why_might_work": "suma de celdas"}]}

    class _Resp:
        def __init__(self, text: str) -> None:
            self.text = text

    def complete(self, prompt: str, temperature: float = 0.0, max_tokens: int = 0):
        return self._Resp("print('code')")


def _runner_viable(code: str) -> tuple[str, str, int]:
    return ('RESULT_JSON: {"found": true, "candidate": "b*h", "checks": "montecarlo", "detail": "ok"}',
            "", 0)


def _runner_dead(code: str) -> tuple[str, str, int]:
    return ('RESULT_JSON: {"found": false, "candidate": null, "checks": "", "detail": "no"}',
            "", 0)


def test_extract_reads_last_result_line():
    out = "ruido\nRESULT_JSON: {\"found\": true, \"candidate\": \"x\"}\n"
    assert _extract(out) == {"found": True, "candidate": "x"}


def test_extract_none_when_absent():
    assert _extract("no json here") is None


def test_explore_settles_when_formal_proves():
    def probe(claim, formal):
        return {"verdict": "verified", "detail": "demostrado", "formal": {"result": "proved"}}

    ex = MathExplorer(provider=_StubProv(), runner=_runner_viable, probe=probe,
                      novelty=lambda c: {"verdict": "likely_open"}, ledger=_mem_ledger())
    res = ex.explore("área de un rectángulo", approaches=3, rounds=1)
    assert res["status"] == "settled"
    assert res["verdict"] == "verified"
    assert res["hypothesis"] == "área = base × altura"
    assert res["viable_approaches"]  # kept the ones that ran
    assert res["novelty"] == "likely_open"


def test_explore_records_tools_used_from_catalog():
    """Provenance: which LEGO pieces each viable approach used is surfaced."""
    def probe(claim, formal):
        return {"verdict": "verified", "detail": "ok", "formal": {"result": "proved"}}

    ex = MathExplorer(provider=_StubProv(), runner=_runner_viable, probe=probe,
                      novelty=lambda c: None, ledger=_mem_ledger())
    res = ex.explore("área", approaches=3, rounds=1)
    tools = {t for a in res["viable_approaches"] for t in a.get("tools_used", [])}
    assert "montecarlo_area" in tools and "sym_integrate" in tools


def test_consensus_guard_downgrades_uncorroborated_refutation():
    """A 'refuted' that contradicts 2+ agreeing approaches → 'candidate' + flag."""
    ex = MathExplorer(provider=_StubProv(), runner=_runner_viable,
                      probe=lambda c, f: {"verdict": "refuted", "detail": "ce"},
                      novelty=lambda c: None, ledger=_mem_ledger())
    res = ex.explore("resultado con consenso", approaches=3, rounds=1)
    assert res["status"] == "candidate"      # NOT settled as refuted
    assert res["verdict"] == "refuted"        # raw probe verdict preserved
    assert res["conflict"]                    # flagged for human review


def test_explore_candidate_when_only_empirical():
    def probe(claim, formal):
        return {"verdict": "holds_empirically", "detail": "sin contraejemplo"}

    ex = MathExplorer(provider=_StubProv(), runner=_runner_viable, probe=probe,
                      novelty=lambda c: None, ledger=_mem_ledger())
    res = ex.explore("algo", approaches=3, rounds=1)
    assert res["status"] == "candidate"      # NOT settled — empirical is never decisive
    assert res["verdict"] == "holds_empirically"


def test_explore_inconclusive_when_no_viable_approach():
    ex = MathExplorer(provider=_StubProv(), runner=_runner_dead,
                      probe=lambda c, f: {"verdict": "inconclusive"},
                      novelty=lambda c: None, ledger=_mem_ledger())
    res = ex.explore("algo imposible", approaches=3, rounds=2)
    assert res["status"] == "inconclusive"
    assert res["rounds"][0]["viable"] == 0


def test_explore_handles_no_provider():
    ex = MathExplorer(provider=None, ledger=_mem_ledger())
    # _prov() would try CodexCliProvider; force no-approaches path via a stub that's unavailable
    class _Down:
        def available(self) -> bool:
            return False
    ex._provider = _Down()
    res = ex.explore("algo", approaches=2, rounds=1)
    assert res["status"] == "inconclusive"
