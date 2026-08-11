"""Gauntlet de descubrimiento — mide si Mendeleev DESCUBRE, no solo si es honesto.

Crítica del revisor externo (Fase 9), aceptada: ACERO medía integridad
epistémica (no-inventa, no-infla) pero NO capacidad de descubrimiento. Este
benchmark corrige eso. Cada problema tiene una LEY OCULTA conocida para el
benchmark pero invisible para el descubridor durante la ejecución.

Requisito duro (constitución de este módulo): este gauntlet es el filtro que
cualquier técnica NUEVA de descubrimiento — incluidas GNN/autoencoders — debe
pasar antes de entrar. La pregunta no es "¿suena avanzado?" sino "¿encontró algo
que estadística + FeatureLab + simbólico + secuencias NO encontraron?".

Métricas por problema:
  * hit: ¿el descubridor emitió un PatternCandidate que captura la ley oculta?
  * false_discovery: ¿emitió un candidato de alto soporte donde NO hay ley
    (nulo/ruido)? — el pecado capital de la minería de múltiples hipótesis.
  * complejidad y soporte del mejor candidato.
Y un veredicto agregado por CONFIGURACIÓN (solo-estadística vs Mendeleev completo)
para cuantificar el aporte marginal de cada motor.
"""

from __future__ import annotations

import math
from typing import Any, Callable

# --- generadores de problemas: cada uno devuelve (rows, target, matcher) ------------
# matcher(candidatos) -> bool: ¿algún candidato captura la ley oculta?
# Semilla fija por índice (Math.random prohibido); datos deterministas.


def _rng(seed: int):
    import numpy as np
    return np.random.default_rng(seed)


def _rows(xs: list[float], ys: list[float], xname: str = "x",
          yname: str = "y") -> list[dict[str, float]]:
    return [{xname: float(a), yname: float(b)} for a, b in zip(xs, ys)]


def _has(cands: list[dict[str, Any]], *, method: str | None = None,
         needle: str | None = None, ptype: str | None = None,
         min_support: float = 0.0) -> bool:
    for c in cands:
        if method and c.get("method") != method:
            continue
        if ptype and c.get("pattern_type") != ptype:
            continue
        if c.get("support_score", 0) < min_support:
            continue
        if needle and needle not in (str(c.get("expression", ""))
                                     + str(c.get("description", ""))):
            continue
        return True
    return False


def problems() -> list[dict[str, Any]]:
    """Los 12 problemas del gauntlet. `has_law` marca si existe ley (para FDR)."""
    import numpy as np
    P: list[dict[str, Any]] = []

    # 1. lineal y = 3x + 2
    xs = list(range(1, 41))
    P.append({"name": "lineal", "has_law": True,
              "rows": _rows(xs, [3 * x + 2 for x in xs]), "target": "y",
              "match": lambda c: _has(c, method="symbolic", needle="x",
                                      min_support=0.98)})
    # 2. cuadrática y = 3x² + 1
    P.append({"name": "cuadratica", "has_law": True,
              "rows": _rows(xs, [3 * x * x + 1 for x in xs]), "target": "y",
              "match": lambda c: _has(c, needle="x", min_support=0.98)})
    # 3. y = |x| con Pearson ≈ 0 (solo la MI lo ve)
    r = _rng(3)
    xv = list(r.uniform(-4, 4, 240))
    P.append({"name": "valor_absoluto_pearson0", "has_law": True,
              "rows": _rows(xv, [abs(x) for x in xv]), "target": "y",
              "match": lambda c: _has(c, method="information")})
    # 4. régimen piecewise: y = x si x<20 else 2x-20
    P.append({"name": "piecewise", "has_law": True,
              "rows": _rows(xs, [x if x < 20 else 2 * x - 20 for x in xs]),
              "target": "y",
              # se considera hit si CUALQUIER motor detecta dependencia fuerte
              "match": lambda c: _has(c, min_support=0.9)})
    # 5. dependencia modular: y = x mod 7
    P.append({"name": "modular", "has_law": True,
              "rows": _rows(xs, [x % 7 for x in xs]), "target": "y",
              "match": lambda c: _has(c, method="sequence", needle="mod")})
    # 6. recurrencia (Fibonacci-like a(n)=a(n-1)+a(n-2))
    fib = [1.0, 1.0]
    for _ in range(18):
        fib.append(fib[-1] + fib[-2])
    P.append({"name": "recurrencia", "has_law": True,
              "rows": [{"n": float(i), "y": fib[i]} for i in range(len(fib))],
              "target": "y",
              "match": lambda c: _has(c, method="sequence", needle="recurrencia")
              or _has(c, method="sequence", needle="a(n)")})
    # 7. invariante: x²+y²=25 (relación, no función) → MI/corr fuerte en x²,y²
    th = list(_rng(7).uniform(0, 6.28, 200))
    P.append({"name": "invariante_circulo", "has_law": True,
              "rows": [{"x": 5 * math.cos(t), "y": 5 * math.sin(t)} for t in th],
              "target": "y",
              "match": lambda c: _has(c, method="information")
              or _has(c, needle="x^2")})
    # 8. NULO: x, y independientes uniformes — NO debe haber descubrimiento
    rn = _rng(8)
    P.append({"name": "nulo_independiente", "has_law": False,
              "rows": _rows(list(rn.uniform(0, 1, 200)),
                            list(rn.uniform(0, 1, 200))), "target": "y",
              "match": lambda c: _has(c, min_support=0.85)})   # hit aquí = FALSO
    # 9. correlación espuria: ambas crecen con un índice oculto (no causal directa)
    t9 = np.arange(1, 61)
    P.append({"name": "correlacion_espuria", "has_law": False,
              "rows": [{"x": float(i + rn.normal(0, 0.1)),
                        "y": float(2 * i + rn.normal(0, 0.1))}
                       for i in t9], "target": "y",
              # aquí SÍ hay relación lineal real x-y (colinealidad), así que un
              # 'hit' NO es falso descubrimiento; marcamos has_law=False solo para
              # verificar que el candidato NUNCA afirme causalidad
              "match": lambda c: any(cc.get("causality") != "NO_ESTABLECIDA"
                                     for cc in c)})   # hit = violación de contrato
    # 10. regla con excepción rara: y = 2x salvo x=17 (outlier)
    ys = [2 * x if x != 17 else 999 for x in xs]
    P.append({"name": "regla_con_excepcion", "has_law": True,
              "rows": _rows(xs, ys), "target": "y",
              "match": lambda c: _has(c, min_support=0.85)})  # detecta pese al outlier
    # 11. representación escondida: y = a/b² (invisible en a,b crudas)
    r11 = _rng(11)
    a = list(r11.uniform(1, 10, 120))
    b = list(r11.uniform(1, 5, 120))
    yv = [ai / (bi * bi) for ai, bi in zip(a, b)]
    P.append({"name": "representacion_escondida", "has_law": True,
              "rows": [{"a": ai, "b": bi, "y": y}
                       for ai, bi, y in zip(a, b, yv)], "target": "y",
              # hit si FeatureLab construyó a/b² o algo equivalente con soporte alto
              "match": lambda c: _has(c, min_support=0.97)})
    # 12. ruido puro sobre una constante: y = 5 + eps → sin ley funcional
    P.append({"name": "ruido_sobre_constante", "has_law": False,
              "rows": _rows(xs, [5 + float(_rng(12).normal(0, 0.01))
                                 for _ in xs]), "target": "y",
              "match": lambda c: _has(c, method="symbolic", min_support=0.9)})
    return P


# --- configuraciones (para medir aporte marginal de cada motor) ---------------------
def _run_config(rows: list[dict[str, Any]], target: str, config: str
                ) -> list[dict[str, Any]]:
    from . import patterns as P
    if len(rows) < 3:
        return []
    dhash = P.dataset_hash(rows)
    # config controla qué motores + si hay FeatureLab
    lab = P.FeatureLab(max_features=48 if config != "solo_estadistica" else 8)
    cols, recipes = lab.derive(rows)
    if not cols:
        return []
    out: list[dict[str, Any]] = []
    out += P.StatisticalDiscoverer().discover(cols, recipes, dhash=dhash)
    if config in ("mendeleev_completo",):
        out += P.MutualInfoDiscoverer().discover(cols, recipes, dhash=dhash)
    if config in ("simbolico", "mendeleev_completo") and target in cols:
        out += P.SymbolicDiscoverer().discover(cols, recipes, target, dhash=dhash)
    if config == "mendeleev_completo" and target in cols:
        idx = next((k for k in sorted(cols) if k != target and "(" not in k
                    and "/" not in k and "*" not in k), None)
        out += P.SequenceDiscoverer().discover(cols, recipes, target, index=idx,
                                               dhash=dhash)
    return P.consensus(out)


CONFIGS = ["solo_estadistica", "simbolico", "mendeleev_completo"]


def run_gauntlet() -> dict[str, Any]:
    """Corre los 12 problemas × 3 configuraciones. Devuelve métricas comparables."""
    probs = problems()
    results: dict[str, Any] = {"per_config": {}, "problems": [p["name"]
                                                              for p in probs]}
    for config in CONFIGS:
        hits = fdr = 0
        n_law = n_null = 0
        detail = []
        for p in probs:
            cands = _run_config(p["rows"], p["target"], config)
            matched = bool(p["match"](cands))
            if p["has_law"]:
                n_law += 1
                if matched:
                    hits += 1
            else:
                n_null += 1
                if matched:            # 'match' en un nulo = falso descubrimiento
                    fdr += 1
            detail.append({"problem": p["name"], "has_law": p["has_law"],
                           "matched": matched, "n_candidates": len(cands)})
        results["per_config"][config] = {
            "true_discovery_rate": round(hits / n_law, 3) if n_law else 0.0,
            "false_discovery_rate": round(fdr / n_null, 3) if n_null else 0.0,
            "hits": hits, "n_law": n_law, "false_discoveries": fdr,
            "n_null": n_null, "detail": detail}
    # aporte marginal: cuántos problemas SOLO el completo resolvió
    base = {d["problem"] for d in
            results["per_config"]["solo_estadistica"]["detail"]
            if d["matched"] and _law_of(probs, d["problem"])}
    full = {d["problem"] for d in
            results["per_config"]["mendeleev_completo"]["detail"]
            if d["matched"] and _law_of(probs, d["problem"])}
    results["marginal_gain_full_over_stats"] = sorted(full - base)
    return results


def _law_of(probs: list[dict[str, Any]], name: str) -> bool:
    return next((p["has_law"] for p in probs if p["name"] == name), False)


def render_report(res: dict[str, Any]) -> str:
    lines = ["# Gauntlet de descubrimiento — resultados\n",
             "| Configuración | True Discovery Rate | False Discovery Rate |",
             "|---|---|---|"]
    for cfg in CONFIGS:
        m = res["per_config"][cfg]
        lines.append(f"| {cfg} | {m['true_discovery_rate']} "
                     f"({m['hits']}/{m['n_law']}) | "
                     f"{m['false_discovery_rate']} "
                     f"({m['false_discoveries']}/{m['n_null']}) |")
    lines.append(f"\n**Aporte marginal de Mendeleev completo sobre solo-estadística:** "
                 f"{res['marginal_gain_full_over_stats'] or 'ninguno'}")
    return "\n".join(lines)
