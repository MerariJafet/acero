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


# --- paquete de EFICIENCIA: formal-first + caché de scripts (Tycho) -----------------

class _DictCache:
    def __init__(self):
        self.d = {}

    def get(self, k):
        return self.d.get(k)

    def put(self, k, v):
        self.d[k] = v


def test_formal_first_proves_without_any_codegen():
    """Si el claim se reduce a sympy y se PRUEBA, no se gasta NI UNA llamada de
    codegen ni una corrida de sandbox: el motor formal es gratis."""
    class _FProv:
        def available(self):
            return True

        def complete_json(self, prompt, schema, temperature=0.0):
            return {"lemma": "", "reduction": "",
                    "formal_claim": {"kind": "identity", "lhs": "sin(x)**2+cos(x)**2",
                                     "rhs": "1", "expr": "", "var": "", "to": "",
                                     "expected": "", "term": "", "index": "",
                                     "lower": "", "upper": "", "closed": ""},
                    "z3_claim": {"kind": ""}}

        def complete(self, *a, **k):
            raise AssertionError("codegen no debe llamarse en formal-first")

    def runner(code):
        raise AssertionError("el sandbox no debe correr nada en formal-first")

    r = MathProbe(provider=_FProv(), runner=runner).probe(
        "sin^2(x) + cos^2(x) = 1 para todo x real")
    assert r["verdict"] == "verified"
    assert "formal-first" in r["detail"] and r["attempts"] == []


def test_script_cache_makes_retry_round_free():
    """Segunda corrida del MISMO claim: la ronda 1 sale del caché de Tycho — cero
    tokens de codegen."""
    out = ('RESULT_JSON: {"verdict": "holds_empirically", "counterexample": null, '
           '"n_tested": 500, "detail": "ok"}')
    cache = _DictCache()

    class _P1:
        def available(self):
            return True

        def complete(self, prompt, temperature=0.0, max_tokens=0):
            class _R:
                text = "print('hola')"
            return _R()

    r1 = MathProbe(provider=_P1(), runner=lambda c: (out, "", 0),
                   script_cache=cache).probe("mismo claim", max_tries=1,
                                             formal_first=False)
    assert r1["verdict"] == "holds_empirically" and len(cache.d) == 1

    class _P2:
        def available(self):
            return True

        def complete(self, *a, **k):
            raise AssertionError("la ronda 1 debe salir del caché, no del LLM")

    r2 = MathProbe(provider=_P2(), runner=lambda c: (out, "", 0),
                   script_cache=cache).probe("mismo claim", max_tries=1,
                                             formal_first=False)
    assert r2["verdict"] == "holds_empirically"
