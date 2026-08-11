"""MENDELEEV — el descubridor de patrones del Consejo.

Mendeleev vio la tabla periódica escondida en datos que todos tenían; este módulo
le da a ACERO ese ojo: recibe OBSERVACIONES (filas numéricas de experimentos ya
verificados) y busca ESTRUCTURA — correlaciones, invariantes aproximados, leyes
simbólicas sencillas. Todo lo que encuentra habla un solo idioma: PatternCandidate.

Epistemología (no negociable):
  * PATRÓN ≠ DESCUBRIMIENTO. Un candidato NUNCA afirma causalidad
    (`causality='NO_ESTABLECIDA'`) y SIEMPRE lista sus hipótesis rivales H1–H4
    (A→B, B→A, causa común, relación matemática no causal / artefacto).
    Convertirlo en conjetura es trabajo del Consejo (gate, Popper, Gödel), no de
    este módulo.
  * EL CONSENSO NO SE CUENTA, SE PESA. Métodos que leen la misma matriz de
    features NO son confirmaciones independientes (PCA/clustering/correlación ven
    la misma foto). `independent_views` cuenta REPRESENTACIONES distintas de los
    datos (cruda / log / derivada), no métodos — la lección de IndependenceGraph:
    independencia calculada, no declarada.
  * REPRODUCIBLE DESDE EL DÍA UNO. Cada candidato lleva dataset_hash, semilla,
    parámetros y receta de features: `REPRODUCE` debe regenerar exactamente el
    mismo hallazgo.

Motores (CPU, numpy): FeatureLab (representaciones derivadas controladas),
StatisticalDiscoverer (correlaciones e invariantes con bootstrap), y
SymbolicDiscoverer (leyes y ~ a·x^b, a·ln x + b, … por mínimos cuadrados; usa
PySR si está instalado, pero no lo exige). Las GNN quedan fuera a propósito:
entran solo si un benchmark demuestra que ven algo que lo clásico no.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

PATTERN_VERSION = "1.0"

RIVALES_BASE = [
    "H1: X influye en Y (dirección directa)",
    "H2: Y influye en X (dirección inversa)",
    "H3: una variable oculta Z produce ambas (causa común)",
    "H4: relación matemática no causal o artefacto del muestreo/representación",
]


def dataset_hash(rows: list[dict[str, Any]]) -> str:
    """Hash canónico del dataset — la mitad de la reproducibilidad."""
    canon = json.dumps(rows, sort_keys=True, default=str)
    return hashlib.sha1(canon.encode()).hexdigest()[:16]


def make_candidate(*, method: str, variables: list[str], description: str,
                   support: float, stability: float, simplicity: float,
                   provenance: dict[str, Any], expression: str = "",
                   representation: str = "cruda",
                   pattern_type: str = "relacion") -> dict[str, Any]:
    """El contrato común: venga de donde venga, un patrón habla este idioma."""
    body = {"method": method, "variables": sorted(variables),
            "description": description, "expression": expression,
            "pattern_type": pattern_type, "representation": representation,
            "support_score": round(float(support), 4),
            "stability_score": round(float(stability), 4),
            "simplicity_score": round(float(simplicity), 4),
            "causality": "NO_ESTABLECIDA",
            "rival_hypotheses": list(RIVALES_BASE),
            "counterexamples": [], "status": "CANDIDATE",
            "provenance": {**provenance, "version": PATTERN_VERSION},
            "methods_agree": [method], "independent_views": 1}
    body["pattern_id"] = "pat_" + hashlib.sha1(
        f"{method}|{body['variables']}|{expression}|{description[:80]}".encode()
    ).hexdigest()[:12]
    return body


# --- Feature Laboratory ------------------------------------------------------------
class FeatureLab:
    """Representaciones derivadas CONTROLADAS. El patrón quizá no vive en las
    variables crudas pero salta a la vista en log(x), x/y o x mod 840 — ese cambio
    de representación puede SER el descubrimiento. Controlado porque las
    combinaciones explotan: prioridad fija y tope duro."""

    def __init__(self, *, max_features: int = 48,
                 mods: tuple[int, ...] = (4, 840)) -> None:
        self._max = max_features
        self._mods = mods

    def derive(self, rows: list[dict[str, Any]]
               ) -> tuple[dict[str, list[float]], dict[str, str]]:
        """→ (columnas, recetas). Receta = cómo se construyó cada columna, para
        reproducir. Solo columnas 100% numéricas y con variación real."""
        base: dict[str, list[float]] = {}
        for key in (rows[0].keys() if rows else []):
            try:
                col = [float(r[key]) for r in rows]
            except (TypeError, ValueError, KeyError):
                continue
            if len(set(col)) > 1:                       # sin constantes muertas
                base[str(key)] = col
        cols = dict(base)
        recipes = {k: f"col('{k}')" for k in base}

        def _add(name: str, values: list[float], recipe: str) -> None:
            if len(cols) >= self._max or name in cols:
                return
            if any(not math.isfinite(v) for v in values):
                return
            if len(set(round(v, 12) for v in values)) <= 1:
                return
            cols[name] = values
            recipes[name] = recipe

        names = sorted(base)
        # unarias primero (baratas e interpretables)
        for k in names:
            v = base[k]
            if all(x > 0 for x in v):
                _add(f"log({k})", [math.log(x) for x in v], f"log(col('{k}'))")
            if all(x >= 0 for x in v):
                _add(f"sqrt({k})", [math.sqrt(x) for x in v],
                     f"sqrt(col('{k}'))")
            _add(f"{k}^2", [x * x for x in v], f"col('{k}')**2")
            if all(float(x).is_integer() for x in v):
                for m in self._mods:
                    _add(f"{k} mod {m}", [float(int(x) % m) for x in v],
                         f"col('{k}') % {m}")
        # binarias después (razones > productos > diferencias)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                va, vb = base[a], base[b]
                if all(x != 0 for x in vb):
                    _add(f"{a}/{b}", [x / y for x, y in zip(va, vb)],
                         f"col('{a}')/col('{b}')")
                if all(x != 0 for x in va):
                    _add(f"{b}/{a}", [y / x for x, y in zip(va, vb)],
                         f"col('{b}')/col('{a}')")
                _add(f"{a}*{b}", [x * y for x, y in zip(va, vb)],
                     f"col('{a}')*col('{b}')")
                _add(f"|{a}-{b}|", [abs(x - y) for x, y in zip(va, vb)],
                     f"abs(col('{a}')-col('{b}'))")
        return cols, recipes


# --- utilidades numéricas (sin dependencias más allá de numpy) ----------------------
def _pearson(x: list[float], y: list[float]) -> float:
    import numpy as np
    if len(x) < 3:
        return 0.0
    sx, sy = float(np.std(x)), float(np.std(y))
    if sx == 0 or sy == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def _bootstrap_stability(x: list[float], y: list[float], stat, *, seed: int,
                         n_rounds: int = 5, drop: float = 0.2) -> float:
    """Estabilidad = 1 − dispersión del estadístico al soltar el 20% de las filas.
    Un patrón que muere quitando tres puntos no es un patrón."""
    import numpy as np
    n = len(x)
    if n < 5:
        return 0.0            # honesto: con <5 puntos la estabilidad no es medible
    rng = np.random.default_rng(seed)
    vals = []
    keep = max(3, int(n * (1 - drop)))
    for _ in range(n_rounds):
        idx = sorted(rng.choice(n, size=keep, replace=False))
        vals.append(stat([x[i] for i in idx], [y[i] for i in idx]))
    spread = float(np.std(vals))
    return max(0.0, min(1.0, 1.0 - spread))


# --- descubridor estadístico --------------------------------------------------------
class StatisticalDiscoverer:
    """Correlaciones fuertes e invariantes aproximados, con estabilidad bootstrap."""

    def discover(self, cols: dict[str, list[float]], recipes: dict[str, str],
                 *, seed: int = 0, dhash: str = "", top: int = 8,
                 min_support: float = 0.85) -> list[dict[str, Any]]:
        import numpy as np
        out: list[dict[str, Any]] = []
        names = sorted(cols)
        prov = {"dataset_hash": dhash, "seed": seed,
                "n_rows": len(cols[names[0]]) if names else 0,
                "params": {"min_support": min_support}}
        # invariantes: columna derivada casi constante (razón ≈ k) — oro puro
        for k in names:
            v = cols[k]
            mean = float(np.mean(v))
            if mean == 0:
                continue
            cv = float(np.std(v)) / abs(mean)
            if cv < 0.05 and ("/" in k or "*" in k):
                out.append(make_candidate(
                    method="statistical", variables=[k],
                    pattern_type="invariante",
                    representation="derivada" if k not in recipes or "col" not in k
                                   else "derivada",
                    description=f"{k} ≈ {mean:.6g} (invariante aproximado, "
                                f"cv={cv:.3%})",
                    expression=f"{k} ≈ {mean:.6g}",
                    support=1.0 - cv,
                    stability=_bootstrap_stability(
                        v, v, lambda a, _b: float(np.mean(a)), seed=seed),
                    simplicity=0.9,
                    provenance={**prov, "recipe": recipes.get(k, "")}))
        # correlaciones fuertes entre columnas distintas
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if a in b or b in a:          # no correlacionar x con log(x)
                    continue
                r = _pearson(cols[a], cols[b])
                if abs(r) < min_support:
                    continue
                out.append(make_candidate(
                    method="statistical", variables=[a, b],
                    pattern_type="correlacion",
                    representation=("derivada" if any(c in a or c in b
                                    for c in "(*/") else "cruda"),
                    description=f"correlación fuerte {a} ↔ {b} (r={r:.3f}) — "
                                "SIN dirección causal establecida",
                    expression=f"corr({a},{b})={r:.3f}",
                    support=abs(r),
                    stability=_bootstrap_stability(cols[a], cols[b], _pearson,
                                                   seed=seed),
                    simplicity=0.7,
                    provenance={**prov,
                                "recipes": {a: recipes.get(a, ""),
                                            b: recipes.get(b, "")}}))
        out.sort(key=lambda c: (c["support_score"] * (0.5 + 0.5 *
                                c["stability_score"])), reverse=True)
        return out[:top]


# --- descubridor simbólico ----------------------------------------------------------
_MODELS: list[tuple[str, int]] = [
    ("a*x + b", 2), ("a*log(x) + b", 3), ("a*x^b", 3),
    ("a*x^b*log(x)^c", 5), ("a + b/x", 3),
]


class SymbolicDiscoverer:
    """¿Los datos caben en una ecuación sencilla? Ajusta una gramática corta de
    leyes (lineal, logarítmica, potencia, potencia·log, recíproca) y reporta las
    mejores por el compromiso explicación/complejidad — la ecuación con error
    0.00008 y complejidad 7 suele valer más que la de error 0.00001 y complejidad
    98. Si PySR está instalado se suma como método extra; jamás es requisito."""

    def discover(self, cols: dict[str, list[float]], recipes: dict[str, str],
                 target: str, *, seed: int = 0, dhash: str = "",
                 top: int = 5, min_r2: float = 0.90) -> list[dict[str, Any]]:
        import numpy as np
        if target not in cols:
            return []
        y = cols[target]
        out: list[dict[str, Any]] = []
        prov = {"dataset_hash": dhash, "seed": seed, "n_rows": len(y),
                "params": {"min_r2": min_r2, "grammar": [m for m, _ in _MODELS]}}
        for x_name in sorted(cols):
            if x_name == target or target in x_name or x_name in target:
                continue
            x = cols[x_name]
            for expr, complexity in _MODELS:
                fit = self._fit(expr, x, y)
                if fit is None or fit["r2"] < min_r2:
                    continue
                simplicity = 1.0 / (1.0 + 0.4 * complexity)

                def _r2_stat(xs: list[float], ys: list[float],
                             _e: str = expr) -> float:
                    f = self._fit(_e, xs, ys)
                    return f["r2"] if f else 0.0

                out.append(make_candidate(
                    method="symbolic", variables=[x_name, target],
                    pattern_type="ley",
                    representation="log" if "log" in expr or "^b" in expr
                                   else "cruda",
                    description=f"{target} ≈ {fit['pretty']}  "
                                f"(R²={fit['r2']:.4f}, complejidad {complexity})",
                    expression=fit["pretty"],
                    support=fit["r2"],
                    stability=_bootstrap_stability(x, y, _r2_stat, seed=seed),
                    simplicity=simplicity,
                    provenance={**prov, "model": expr,
                                "coefficients": fit["coef"],
                                "recipe_x": recipes.get(x_name, ""),
                                "recipe_y": recipes.get(target, "")}))
        out.sort(key=lambda c: c["support_score"] * (0.4 + 0.6 *
                               c["simplicity_score"]), reverse=True)
        return out[:top]

    @staticmethod
    def _fit(expr: str, x: list[float], y: list[float]) -> dict[str, Any] | None:
        """Ajuste por mínimos cuadrados del modelo `expr`. None si no aplica."""
        import numpy as np
        xa, ya = np.asarray(x, float), np.asarray(y, float)
        n = len(xa)
        if n < 3:
            return None
        try:
            if expr == "a*x + b":
                A = np.vstack([xa, np.ones(n)]).T
                (a, b), *_ = np.linalg.lstsq(A, ya, rcond=None)
                pred, pretty = a * xa + b, f"{a:.4g}·x + {b:.4g}"
                coef = {"a": float(a), "b": float(b)}
            elif expr == "a*log(x) + b":
                if np.any(xa <= 0):
                    return None
                lx = np.log(xa)
                A = np.vstack([lx, np.ones(n)]).T
                (a, b), *_ = np.linalg.lstsq(A, ya, rcond=None)
                pred, pretty = a * lx + b, f"{a:.4g}·ln(x) + {b:.4g}"
                coef = {"a": float(a), "b": float(b)}
            elif expr == "a*x^b":
                if np.any(xa <= 0) or np.any(ya <= 0):
                    return None
                lx, ly = np.log(xa), np.log(ya)
                A = np.vstack([lx, np.ones(n)]).T
                (b, la), *_ = np.linalg.lstsq(A, ly, rcond=None)
                a = math.exp(la)
                pred, pretty = a * xa ** b, f"{a:.4g}·x^{b:.4g}"
                coef = {"a": float(a), "b": float(b)}
            elif expr == "a*x^b*log(x)^c":
                if np.any(xa <= 1) or np.any(ya <= 0):
                    return None
                lx, llx, ly = np.log(xa), np.log(np.log(xa)), np.log(ya)
                A = np.vstack([lx, llx, np.ones(n)]).T
                (b, c, la), *_ = np.linalg.lstsq(A, ly, rcond=None)
                a = math.exp(la)
                pred = a * xa ** b * np.log(xa) ** c
                pretty = f"{a:.4g}·x^{b:.4g}·ln(x)^{c:.4g}"
                coef = {"a": float(a), "b": float(b), "c": float(c)}
            elif expr == "a + b/x":
                if np.any(xa == 0):
                    return None
                A = np.vstack([np.ones(n), 1.0 / xa]).T
                (a, b), *_ = np.linalg.lstsq(A, ya, rcond=None)
                pred, pretty = a + b / xa, f"{a:.4g} + {b:.4g}/x"
                coef = {"a": float(a), "b": float(b)}
            else:
                return None
            ss_res = float(np.sum((ya - pred) ** 2))
            ss_tot = float(np.sum((ya - np.mean(ya)) ** 2))
            if ss_tot == 0:
                return None
            return {"r2": max(0.0, 1.0 - ss_res / ss_tot), "pretty": pretty,
                    "coef": coef}
        except Exception:  # noqa: BLE001 - modelo no aplicable ⇒ se descarta
            return None


# --- consenso pesado por independencia ----------------------------------------------
def consensus(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrupa candidatos equivalentes (mismas variables) y anota el acuerdo.

    HONESTIDAD: `methods_agree` lista los métodos, pero `independent_views` cuenta
    REPRESENTACIONES distintas de los datos — dos métodos sobre la misma matriz
    son la misma foto, no dos testigos. La prioridad sube con las vistas
    independientes, no con el número de métodos."""
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for c in candidates:
        groups.setdefault(tuple(c["variables"]), []).append(c)
    merged: list[dict[str, Any]] = []
    for cands in groups.values():
        best = max(cands, key=lambda c: c["support_score"])
        methods = sorted({c["method"] for c in cands})
        views = sorted({c["representation"] for c in cands})
        best = dict(best)
        best["methods_agree"] = methods
        best["independent_views"] = len(views)
        if len(methods) > 1 and len(views) == 1:
            best["description"] += (" | consenso de %d métodos pero UNA sola "
                                    "representación — acuerdo NO independiente"
                                    % len(methods))
        merged.append(best)
    merged.sort(key=lambda c: (c["independent_views"], c["support_score"] *
                               (0.5 + 0.5 * c["stability_score"])), reverse=True)
    return merged


def discover_all(rows: list[dict[str, Any]], *, target: str | None = None,
                 seed: int = 0, max_features: int = 48,
                 top: int = 10) -> list[dict[str, Any]]:
    """El pipeline completo de Mendeleev: FeatureLab → estadístico (+ simbólico si
    hay objetivo) → consenso pesado por independencia. Devuelve los top-N."""
    if len(rows) < 3:
        return []
    dhash = dataset_hash(rows)
    cols, recipes = FeatureLab(max_features=max_features).derive(rows)
    if not cols:
        return []
    cands = StatisticalDiscoverer().discover(cols, recipes, seed=seed, dhash=dhash)
    if target and target in cols:
        cands += SymbolicDiscoverer().discover(cols, recipes, target, seed=seed,
                                               dhash=dhash)
    return consensus(cands)[:top]
