"""Experimental math prover — computational search + formal cross-check + retry."""
from __future__ import annotations

from acero.science.math_probe import MathProbe, _extract


class _Prov:
    def __init__(self, code="print('x')"):
        self.code = code
        self.calls = 0

    def available(self):
        return True

    def complete(self, prompt, *, temperature=0.0, max_tokens=1024):
        self.calls += 1
        class _R:
            text = self.code
        return _R()


def _runner_for(stdout):
    return lambda code: (stdout, "", 0)


def test_formal_proof_yields_verified():
    p = MathProbe(provider=_Prov(), runner=_runner_for("RESULT_JSON: "
                  '{"verdict":"holds_empirically","counterexample":null,"n_tested":9,"detail":""}'),
                  formal=lambda fc: {"result": "proved", "detail": "sympy"})
    r = p.probe("sin^2+cos^2=1", formal_claim={"kind": "identity", "lhs": "a", "rhs": "a"})
    assert r["verdict"] == "verified" and r["formal"]["result"] == "proved"


def test_formal_refutation_trusted_when_no_empirical_conflict():
    # formal refutes AND the search finds no contradicting evidence → refuted
    out = 'RESULT_JSON: {"verdict":"inconclusive","counterexample":null,"n_tested":0,"detail":""}'
    p = MathProbe(provider=_Prov(), runner=_runner_for(out),
                  formal=lambda fc: {"result": "refuted", "counterexample": {"x": 2}})
    r = p.probe("(x+1)^2 = x^2+1", formal_claim={"kind": "identity", "lhs": "a", "rhs": "b"},
                max_tries=1)
    assert r["verdict"] == "refuted"


def test_formal_refutation_downgraded_to_inconclusive_on_conflict():
    # formal says false, but the search finds NO counterexample → misencoding suspected
    out = 'RESULT_JSON: {"verdict":"holds_empirically","counterexample":null,"n_tested":99999,"detail":""}'
    p = MathProbe(provider=_Prov(), runner=_runner_for(out),
                  formal=lambda fc: {"result": "refuted", "counterexample": {"x": 2}})
    r = p.probe("Binet F_n=(phi^n-psi^n)/sqrt5",
                formal_claim={"kind": "identity", "lhs": "a", "rhs": "b"}, max_tries=1)
    assert r["verdict"] == "inconclusive"     # abstains instead of falsely refuting


def test_numeric_nearmiss_is_not_a_refutation():
    # a 'counterexample' within 0.1% of expected is precision noise, not a refutation
    ce = '{"method":"quad","computed":1.7724512,"expected":1.7724538,"abs_error":2.6e-6}'
    out = f'RESULT_JSON: {{"verdict":"refuted","counterexample":{ce},"n_tested":1,"detail":""}}'
    r = MathProbe(provider=_Prov(), runner=_runner_for(out)).probe("I = sqrt(pi)", max_tries=1)
    assert r["verdict"] == "holds_empirically"    # the value actually holds


def test_truncation_tail_is_not_a_refutation():
    # Basel-style: 'refuted' justified only by a tiny leftover tail → not a real CE
    ce = '{"N":5217276,"tail_estimate":1.9e-07,"detail":"partial sum short of pi^2/6"}'
    out = f'RESULT_JSON: {{"verdict":"refuted","counterexample":{ce},"n_tested":1,"detail":""}}'
    r = MathProbe(provider=_Prov(), runner=_runner_for(out)).probe("sum 1/n^2 = pi^2/6",
                                                                   max_tries=1)
    assert r["verdict"] == "holds_empirically"


def test_robust_counterexample_still_refutes():
    ce = '{"computed":5.0,"expected":1.77,"abs_error":3.23}'   # gross mismatch
    out = f'RESULT_JSON: {{"verdict":"refuted","counterexample":{ce},"n_tested":1,"detail":""}}'
    r = MathProbe(provider=_Prov(), runner=_runner_for(out)).probe("claim", max_tries=1)
    assert r["verdict"] == "refuted"


def test_computational_counterexample_refutes():
    out = 'RESULT_JSON: {"verdict":"refuted","counterexample":27,"n_tested":100,"detail":"n=27"}'
    r = MathProbe(provider=_Prov(), runner=_runner_for(out)).probe("todo n cumple P(n)")
    assert r["verdict"] == "refuted" and r["computational"]["counterexample"] == 27


def test_no_counterexample_is_empirical_not_verified():
    out = 'RESULT_JSON: {"verdict":"holds_empirically","counterexample":null,"n_tested":1000000,"detail":""}'
    r = MathProbe(provider=_Prov(), runner=_runner_for(out)).probe("conjetura", max_tries=1)
    assert r["verdict"] == "holds_empirically"               # searching != proving
    assert r["verdict"] != "verified"


def test_creative_retry_on_inconclusive():
    prov = _Prov()
    # runner always returns junk (no RESULT_JSON) → inconclusive after retries
    r = MathProbe(provider=prov, runner=lambda code: ("nada util", "", 0)).probe("x", max_tries=3)
    assert r["verdict"] == "inconclusive" and prov.calls == 3   # it tried 3 different times


def test_extract_result_json():
    assert _extract('ruido\nRESULT_JSON: {"verdict":"refuted"}')["verdict"] == "refuted"
    assert _extract("sin marcador") is None
