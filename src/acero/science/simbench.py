"""Scientific Simulation & Recovery Bench — prove a method before trusting it.

The reviewer: one of the best ways to validate a pipeline is to build synthetic universes
where the truth is known, and check that the method (1) does NOT invent effects when none
exist, (2) recovers effects when they exist, (3) does not mistake confounding/leakage for
a real effect, and (4) fails visibly when the question is not identifiable.

A method is not fit to DISCOVER anything until it passes this bench. The bench is
deterministic (seeded numpy) so results are reproducible.

A "method under test" is any callable `method(data) -> Detection`, where `data` is a dict
of arrays and Detection reports whether an effect was detected and its estimate. The
bench feeds it universes with known truth and measures its operating characteristics.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np


@dataclass
class Detection:
    detected: bool
    estimate: float = 0.0


Method = Callable[[dict], Detection]


@dataclass
class Truth:
    has_effect: bool
    true_effect: float
    mechanism: str


# --- universe generators (binary group x ∈ {0,1}, continuous outcome y) -------
def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def gen_no_effect(seed: int, n: int = 200) -> tuple[dict, Truth]:
    r = _rng(seed)
    x = r.integers(0, 2, n)
    y = r.normal(0, 1, n)                 # y independent of x
    return {"x": x, "y": y}, Truth(False, 0.0, "sin efecto")


def gen_effect(seed: int, n: int = 200, effect: float = 0.8) -> tuple[dict, Truth]:
    r = _rng(seed)
    x = r.integers(0, 2, n)
    y = effect * x + r.normal(0, 1, n)
    return {"x": x, "y": y}, Truth(True, effect, "efecto directo")


def gen_confounded(seed: int, n: int = 200) -> tuple[dict, Truth]:
    """c → x and c → y; x has NO direct effect on y. A naive x-vs-y test detects an
    association that is pure confounding. Truth: no causal effect of x."""
    r = _rng(seed)
    c = r.integers(0, 2, n)
    # x tracks c strongly (but not perfectly), y driven by c only
    flip = r.random(n) < 0.15
    x = np.where(flip, 1 - c, c)
    y = 0.9 * c + r.normal(0, 1, n)
    return {"x": x, "y": y, "c": c}, Truth(False, 0.0, "confusión (c→x, c→y)")


def gen_batch(seed: int, n: int = 200) -> tuple[dict, Truth]:
    """Batch correlated with x drives y; x itself has no effect."""
    r = _rng(seed)
    batch = r.integers(0, 2, n)
    flip = r.random(n) < 0.2
    x = np.where(flip, 1 - batch, batch)
    y = 0.8 * batch + r.normal(0, 1, n)
    return {"x": x, "y": y, "batch": batch}, Truth(False, 0.0, "efecto de lote")


def gen_leakage(seed: int, n: int = 200) -> tuple[dict, Truth]:
    """A feature leaks the label: y is (almost) a copy of x. Apparent effect is trivial
    and enormous — a warning that 'great performance' can be leakage."""
    r = _rng(seed)
    x = r.integers(0, 2, n)
    y = 5.0 * x + r.normal(0, 0.01, n)
    return {"x": x, "y": y}, Truth(True, 5.0, "fuga de etiqueta (leakage)")


# --- a reference naive method (for self-test) --------------------------------
def naive_ttest(alpha_z: float = 1.96) -> Method:
    """Two-sample difference of means on x vs y. Sees ONLY x,y (no adjustment) — so it
    will (correctly per the bench) fail the confounding/batch scenarios."""
    def method(data: dict) -> Detection:
        x = np.asarray(data["x"])
        y = np.asarray(data["y"])
        y1, y0 = y[x == 1], y[x == 0]
        if len(y1) < 2 or len(y0) < 2:
            return Detection(False, 0.0)
        diff = float(y1.mean() - y0.mean())
        se = float(np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0)))
        t = diff / se if se > 0 else 0.0
        return Detection(abs(t) > alpha_z, diff)
    return method


# --- the bench ---------------------------------------------------------------
@dataclass
class ScenarioResult:
    scenario: str
    detection_rate: float          # = FPR if no effect, power if effect
    mean_estimate: float
    bias: float
    has_effect: bool


def run_scenario(method: Method, generator: Callable[..., tuple[dict, Truth]],
                 n_reps: int = 100, n: int = 200, seed0: int = 1000) -> ScenarioResult:
    detections = 0
    estimates = []
    truth: Truth | None = None
    name = generator.__name__.replace("gen_", "")
    for i in range(n_reps):
        data, truth = generator(seed0 + i, n)
        det = method(data)
        detections += int(det.detected)
        estimates.append(det.estimate)
    assert truth is not None
    mean_est = float(np.mean(estimates))
    return ScenarioResult(name, detections / n_reps, mean_est,
                          mean_est - truth.true_effect, truth.has_effect)


@dataclass
class BenchReport:
    fpr: float                            # false-positive rate on the no-effect universe
    power_strong: float                   # power on a strong real effect
    bias_strong: float
    false_effect_confounded: float        # detection under pure confounding (should be low)
    false_effect_batch: float             # detection under batch (should be low)
    leakage_detected: float               # ~1.0: leakage inflates apparent effect
    results: list[ScenarioResult]

    def passes_association(self, fpr_tol: float = 0.10, power_tol: float = 0.7) -> bool:
        """Fit to claim ASSOCIATIONS: controls false positives and has power."""
        return self.fpr <= fpr_tol and self.power_strong >= power_tol

    def passes_causal(self, false_tol: float = 0.20) -> bool:
        """Fit to claim CAUSAL effects: must NOT be fooled by confounding/batch."""
        return (self.passes_association()
                and self.false_effect_confounded <= false_tol
                and self.false_effect_batch <= false_tol)

    def summary(self) -> dict[str, object]:
        return {
            "fpr": round(self.fpr, 3), "power_strong": round(self.power_strong, 3),
            "bias_strong": round(self.bias_strong, 3),
            "false_effect_confounded": round(self.false_effect_confounded, 3),
            "false_effect_batch": round(self.false_effect_batch, 3),
            "leakage_detected": round(self.leakage_detected, 3),
            "passes_association": self.passes_association(),
            "passes_causal": self.passes_causal(),
        }


def evaluate(method: Method, n_reps: int = 100, n: int = 200) -> BenchReport:
    """Run the standard battery and return operating characteristics + fit verdicts."""
    no = run_scenario(method, gen_no_effect, n_reps, n, seed0=1000)
    strong = run_scenario(method, gen_effect, n_reps, n, seed0=2000)
    conf = run_scenario(method, gen_confounded, n_reps, n, seed0=3000)
    batch = run_scenario(method, gen_batch, n_reps, n, seed0=4000)
    leak = run_scenario(method, gen_leakage, n_reps, n, seed0=5000)
    return BenchReport(
        fpr=no.detection_rate, power_strong=strong.detection_rate,
        bias_strong=strong.bias, false_effect_confounded=conf.detection_rate,
        false_effect_batch=batch.detection_rate, leakage_detected=leak.detection_rate,
        results=[no, strong, conf, batch, leak])
