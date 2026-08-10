"""Regression detection (Sprint 18).

Compares a fresh benchmark result against a LOCKED baseline using PRE-REGISTERED tolerances
(never adjusted after seeing results). A small variation within tolerance is UNCHANGED, not a
regression. Metrics are higher-is-better unless listed in _LOWER_IS_BETTER.

CAPACIDAD vs RENDIMIENTO — son dos preguntas distintas y solo una bloquea:
- Capacidad: ¿ACERO sigue siendo igual de bueno? (pass_rate, detection_rate…). Una caída
  aquí SÍ es un blocker de release: el sistema perdió habilidad.
- Rendimiento: ¿tardó más reloj de pared? Eso mide la MÁQUINA, no la habilidad. Medir
  wall-clock en un equipo cargado hace que el gate dependa de qué más esté corriendo —
  y ACERO corre sus propias investigaciones de días (solvers Z3, ciclos del Consejo al
  80% de CPU). El resultado era perverso: cuanto más trabajaba ACERO investigando, más
  su propio gate de release declaraba "regresión de capacidad" con la calidad intacta.
  Se sigue reportando (nunca se silencia una señal) pero como observación, no blocker.
"""

from __future__ import annotations

from typing import Any

from .models import RegressionStatus

# Pre-registered per-metric tolerances (absolute). Fixed; do not tune to results.
_TOLERANCE: dict[str, float] = {
    "pass_rate": 0.0,          # gauntlets must stay perfect
    "detection_rate": 0.0,
    "caught_rate": 0.0,
    "recovery_rate": 0.05,
    "period_years": 0.5,       # astronomy period may vary within 0.5 yr
    "duration_sec": 2.0,       # latency tolerance before flagging
}
_LOWER_IS_BETTER = {"duration_sec", "ece", "abstention_rate", "false_positive_rate"}
_DEFAULT_TOL = 0.02

# Métricas que describen la MÁQUINA, no la habilidad. Se comparan y se reportan, pero
# no determinan el veredicto de capacidad ni bloquean un release.
_PERFORMANCE_METRICS = {"duration_sec"}

# El rendimiento se juzga por RAZÓN, no por segundos absolutos: 2s de tolerancia fija
# es irrelevante para un benchmark de 0.05s y asfixiante para uno de 30s. Un benchmark
# puede tardar hasta 3x lo del baseline antes de que valga la pena mencionarlo.
#
# El piso absoluto existe SOLO para no reportar ruido de milisegundos (un benchmark de
# 0.01s que sube a 0.03s es 3x pero no significa nada). Debe ser pequeño: con +2s se
# comía el chequeo por razón justo en los benchmarks rápidos que pretendía proteger
# (0.05s → 1.0s son 20x y quedaban dentro del piso). Medio segundo separa bien el ruido
# de una ralentización real.
_PERF_RATIO_TOL = 3.0
_PERF_ABS_FLOOR_S = 0.5


def _direction(metric: str) -> int:
    return -1 if metric in _LOWER_IS_BETTER else 1


def compare_metric(metric: str, baseline: float, current: float) -> RegressionStatus:
    tol = _TOLERANCE.get(metric, _DEFAULT_TOL)
    delta = (current - baseline) * _direction(metric)
    if abs(current - baseline) <= tol:
        return RegressionStatus.UNCHANGED
    return RegressionStatus.IMPROVED if delta > 0 else RegressionStatus.REGRESSED


def compare_performance(baseline_s: float, current_s: float) -> RegressionStatus:
    """Juzga el reloj de pared por RAZÓN (ver _PERF_RATIO_TOL). Tolera lo que sea más
    permisivo entre el factor y el piso absoluto, para que benchmarks rápidos no
    disparen por ruido de milisegundos."""
    slack = max(baseline_s * _PERF_RATIO_TOL, baseline_s + _PERF_ABS_FLOOR_S)
    if current_s > slack:
        return RegressionStatus.REGRESSED
    if current_s * _PERF_RATIO_TOL < baseline_s:
        return RegressionStatus.IMPROVED
    return RegressionStatus.UNCHANGED


def compare_benchmark(baseline: dict[str, Any] | None, current: dict[str, Any]
                      ) -> dict[str, Any]:
    """Compare one benchmark's current run against its baseline entry.

    `status` = veredicto de CAPACIDAD (lo único que puede bloquear un release).
    `performance` = veredicto de reloj de pared, informativo y siempre visible."""
    if baseline is None:
        return {"status": RegressionStatus.INSUFFICIENT_DATA.value, "per_metric": {},
                "performance": RegressionStatus.INSUFFICIENT_DATA.value}
    per_metric: dict[str, str] = {}
    worst = RegressionStatus.UNCHANGED
    order = [RegressionStatus.IMPROVED, RegressionStatus.UNCHANGED,
             RegressionStatus.REGRESSED]
    for metric, cur in current.get("metrics", {}).items():
        base = baseline.get("metrics", {}).get(metric)
        if base is None:
            per_metric[metric] = RegressionStatus.INSUFFICIENT_DATA.value
            continue
        st = compare_metric(metric, float(base), float(cur))
        per_metric[metric] = st.value
        if metric in _PERFORMANCE_METRICS:   # se reporta, no vota la capacidad
            continue
        if st in order and order.index(st) > order.index(worst):
            worst = st
    # reloj de pared: se compara y se reporta APARTE — nunca degrada la capacidad
    perf = RegressionStatus.INSUFFICIENT_DATA
    if current.get("duration_sec") is not None and baseline.get("duration_sec") is not None:
        perf = compare_performance(float(baseline["duration_sec"]),
                                   float(current["duration_sec"]))
        per_metric["duration_sec"] = perf.value
    return {"status": worst.value, "per_metric": per_metric,
            "performance": perf.value}


def compare_run(baseline_results: dict[str, Any], current_results: dict[str, Any]
                ) -> dict[str, Any]:
    """Compare a full run vs the baseline; return per-benchmark statuses + any regressions."""
    out: dict[str, Any] = {}
    regressions = []
    slowdowns = []
    for bid, cur in current_results.get("results", {}).items():
        base = baseline_results.get("results", {}).get(bid)
        cmp = compare_benchmark(base, cur)
        out[bid] = cmp
        if cmp["status"] == RegressionStatus.REGRESSED.value:
            regressions.append(bid)
        if cmp.get("performance") == RegressionStatus.REGRESSED.value:
            slowdowns.append(bid)
    return {"per_benchmark": out, "regressions": regressions,
            "has_regression": bool(regressions),
            # visible pero NO blocker: puede deberse a carga de la máquina
            "slowdowns": slowdowns, "has_slowdown": bool(slowdowns)}
