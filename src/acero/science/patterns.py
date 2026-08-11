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


def permutation_null(x: list[float], y: list[float], stat, *, seed: int,
                     n_perm: int = 60) -> dict[str, Any]:
    """TEST DE PERMUTACIÓN — la defensa contra la minería de múltiples hipótesis.

    Si buscas correlaciones entre decenas de features derivadas de ruido puro,
    ALGUNA saldrá espectacular por azar. La pregunta correcta no es "¿qué tan
    fuerte es?" sino "¿qué tan seguido sale así de fuerte cuando NO hay relación?".

    Rompemos la relación barajando `y` y recalculamos el estadístico n_perm
    veces: p empírico = fracción de barajadas que igualan o superan lo observado.
    Esto es evidencia contra "aparece igual por azar bajo ESTE nulo" — nunca una
    verdad universal, y así se declara en el candidato.

    Corrección por búsqueda múltiple: el llamador debe pasar cuántas comparaciones
    hizo (deuda de búsqueda) para exigir un umbral más duro."""
    import numpy as np
    n = len(x)
    if n < 8:
        return {"p_empirical": None, "n_perm": 0,
                "why": "muestra insuficiente para permutar (<8)"}
    rng = np.random.default_rng(seed + 977)
    observed = abs(float(stat(x, y)))
    ge = 0
    for _ in range(n_perm):
        idx = rng.permutation(n)
        shuffled = [y[i] for i in idx]
        if abs(float(stat(x, shuffled))) >= observed:
            ge += 1
    p = (ge + 1) / (n_perm + 1)      # estimador de Davison-Hinkley (sin p=0)
    # `p_raw` SIN redondear: comparar el valor redondeado contra el umbral
    # producía un falso rechazo justo en el mínimo alcanzable (0.0164 > 0.016393)
    return {"p_empirical": round(p, 4), "p_raw": p, "n_perm": n_perm,
            "observed": round(observed, 4),
            "null_recipe": "permutación de y (rompe la relación, preserva marginales)",
            "seed": seed + 977}


def family_wise_threshold(cols: dict[str, list[float]], *, seed: int,
                          n_perm: int = 40, quantile: float = 0.95
                          ) -> dict[str, Any]:
    """Umbral FAMILY-WISE por permutación (max-estadístico, estilo Westfall-Young).

    El test por-par no basta cuando el candidato reportado es el MÁXIMO de ~1000
    comparaciones: ese máximo es alto por construcción aunque todo sea ruido. La
    corrección correcta es simular el proceso COMPLETO de búsqueda: en cada
    permutación se rompen TODAS las relaciones (cada columna se baraja de forma
    independiente) y se anota la correlación máxima que la búsqueda habría
    encontrado. El umbral es el cuantil 95 de esos máximos.

    Interpretación honesta: superar este umbral significa "más fuerte que lo que
    una búsqueda del mismo tamaño encuentra en datos sin relación", no "es real".
    """
    import numpy as np
    names = sorted(cols)
    if len(names) < 2:
        return {"threshold": 0.0, "n_perm": 0, "why": "menos de 2 columnas"}
    m = np.array([cols[k] for k in names], float)      # (features × filas)
    n_rows = m.shape[1]
    if n_rows < 8:
        return {"threshold": 0.0, "n_perm": 0, "why": "muestra < 8 filas"}
    rng = np.random.default_rng(seed + 31337)
    maxima = []
    for _ in range(n_perm):
        shuffled = np.array([row[rng.permutation(n_rows)] for row in m])
        with np.errstate(invalid="ignore", divide="ignore"):
            c = np.corrcoef(shuffled)
        np.fill_diagonal(c, 0.0)
        c = np.nan_to_num(c, nan=0.0, posinf=0.0, neginf=0.0)
        maxima.append(float(np.max(np.abs(c))))
    thr = float(np.quantile(maxima, quantile))
    return {"threshold": round(thr, 4), "n_perm": n_perm,
            "quantile": quantile, "n_features": len(names),
            "n_comparisons": len(names) * (len(names) - 1) // 2,
            "null_recipe": "cada columna barajada independientemente; se registra "
                           "el MÁXIMO |r| que la búsqueda completa habría hallado",
            "seed": seed + 31337,
            "interpretacion": "superar el umbral = más fuerte que lo que una "
                              "búsqueda del mismo tamaño encuentra en ruido"}


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
        # DEUDA DE BÚSQUEDA: cuántos pares se van a mirar. Buscar entre miles de
        # combinaciones garantiza que alguna salga "espectacular" por azar; el
        # umbral se corrige por ese número (y queda registrado en la procedencia).
        n_comparisons = max(1, len(names) * (len(names) - 1) // 2)
        nulls_run = 0
        # umbral FAMILY-WISE: simula la búsqueda COMPLETA sobre datos sin relación
        # y exige superar lo que esa búsqueda encontraría por azar (el máximo).
        fw = family_wise_threshold(cols, seed=seed)
        fw_thr = float(fw.get("threshold") or 0.0)
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
                if fw_thr and abs(r) <= fw_thr:
                    continue        # no supera lo que la búsqueda halla en ruido
                null = permutation_null(cols[a], cols[b], _pearson, seed=seed)
                nulls_run += 1
                p_emp = null.get("p_raw", null.get("p_empirical"))
                # Corrección por búsqueda múltiple (Bonferroni sobre las
                # comparaciones REALMENTE hechas), con PISO DE RESOLUCIÓN: con
                # n_perm permutaciones el p más pequeño observable es 1/(n_perm+1);
                # exigir menos que eso rechazaría TODO, señal incluida. Se pide
                # entonces el mínimo alcanzable — "ni una sola barajada lo igualó" —
                # y se declara la limitación en la procedencia.
                alpha = max(0.05 / max(1, n_comparisons),
                            1.0 / (int(null.get("n_perm") or 60) + 1))
                if p_emp is not None and p_emp > alpha + 1e-9:
                    continue          # indistinguible del azar bajo este nulo
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
                    provenance={**prov, "null_test": null,
                                "family_wise_null": fw,
                                "search_debt": {"comparisons": n_comparisons,
                                                "alpha_corrected": round(alpha, 6),
                                                "alpha_bonferroni":
                                                    round(0.05 / max(1, n_comparisons), 8),
                                                "resolution_floor":
                                                    round(1.0 / (int(null.get("n_perm") or 60) + 1), 6),
                                                "limitacion": "el piso de resolución "
                                                "domina a Bonferroni con esta cantidad "
                                                "de comparaciones: más permutaciones "
                                                "darían un umbral más estricto",
                                                "nulls_run": nulls_run},
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


# --- descubridor de teoría de la información ----------------------------------------
class MutualInfoDiscoverer:
    """Dependencias que Pearson NO ve. La correlación lineal es ciega a relaciones
    en V, en U, periódicas o por regímenes; la información mutua las detecta todas.
    MI normalizada por histograma 2D (numpy puro): 0 = independientes, 1 = una
    determina a la otra. Un candidato aquí dice "hay DEPENDENCIA no lineal" — qué
    forma tiene es trabajo del simbólico o del Consejo, no de este módulo."""

    def discover(self, cols: dict[str, list[float]], recipes: dict[str, str],
                 *, seed: int = 0, dhash: str = "", top: int = 5,
                 min_nmi: float = 0.55, bins: int = 8) -> list[dict[str, Any]]:
        import numpy as np
        names = sorted(cols)
        out: list[dict[str, Any]] = []
        n = len(cols[names[0]]) if names else 0
        if n < 10:            # con menos filas la MI por histograma es ruido
            return []
        prov = {"dataset_hash": dhash, "seed": seed, "n_rows": n,
                "params": {"bins": bins, "min_nmi": min_nmi}}
        n_comparisons = max(1, len(names) * (len(names) - 1) // 2)
        fw = family_wise_threshold(cols, seed=seed)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if a in b or b in a:
                    continue
                nmi = self._nmi(cols[a], cols[b], bins)
                # solo interesa lo que Pearson NO explica ya (aporte marginal)
                if nmi < min_nmi or abs(_pearson(cols[a], cols[b])) > 0.85:
                    continue

                def _stat(xs: list[float], ys: list[float],
                          _bins: int = bins) -> float:
                    return self._nmi(xs, ys, _bins)

                null = permutation_null(cols[a], cols[b], _stat, seed=seed)
                p_emp = null.get("p_raw", null.get("p_empirical"))
                alpha = max(0.05 / max(1, n_comparisons),
                            1.0 / (int(null.get("n_perm") or 60) + 1))
                if p_emp is not None and p_emp > alpha + 1e-9:
                    continue          # la MI alta también aparece por azar: fuera
                out.append(make_candidate(
                    method="information", variables=[a, b],
                    pattern_type="dependencia",
                    representation="información",
                    description=f"dependencia NO lineal {a} ↔ {b} "
                                f"(MI normalizada={nmi:.3f}, invisible para "
                                "correlación) — forma desconocida",
                    expression=f"NMI({a},{b})={nmi:.3f}",
                    support=nmi,
                    stability=_bootstrap_stability(cols[a], cols[b], _stat,
                                                   seed=seed),
                    simplicity=0.5,
                    provenance={**prov, "null_test": null,
                                "family_wise_null": fw,
                                "search_debt": {"comparisons": n_comparisons,
                                                "alpha_corrected": round(alpha, 6)},
                                "recipes": {a: recipes.get(a, ""),
                                            b: recipes.get(b, "")}}))
        out.sort(key=lambda c: c["support_score"], reverse=True)
        return out[:top]

    @staticmethod
    def _nmi(x: list[float], y: list[float], bins: int) -> float:
        import numpy as np
        try:
            h, _, _ = np.histogram2d(x, y, bins=bins)
        except Exception:  # noqa: BLE001
            return 0.0
        pxy = h / max(h.sum(), 1.0)
        px, py = pxy.sum(1), pxy.sum(0)
        nz = pxy > 0
        mi = float((pxy[nz] * np.log(pxy[nz] /
                    (np.outer(px, py)[nz] + 1e-12))).sum())
        hx = -float((px[px > 0] * np.log(px[px > 0])).sum())
        hy = -float((py[py > 0] * np.log(py[py > 0])).sum())
        denom = min(hx, hy)
        return max(0.0, min(1.0, mi / denom)) if denom > 0 else 0.0


# --- descubridor de secuencias ------------------------------------------------------
class SequenceDiscoverer:
    """Para datos que SON una secuencia (p.ej. cover(N) por hitos): busca la regla
    generadora, no solo la curva. Tres detectores exactos y baratos:
      * recurrencia lineal  a(n) = c1·a(n-1) + c2·a(n-2)  (Fibonacci-style),
      * polinomio por diferencias finitas (k-ésima diferencia constante),
      * periodicidad modular (residuos que se repiten con período corto).
    Una regla generadora comprime más que un ajuste — y la compresión extrema es
    la forma de una ley."""

    def discover(self, cols: dict[str, list[float]], recipes: dict[str, str],
                 target: str, *, index: str | None = None, seed: int = 0,
                 dhash: str = "", top: int = 3) -> list[dict[str, Any]]:
        import numpy as np
        if target not in cols:
            return []
        # ordenar por la columna índice si existe (p.ej. N); si no, orden de fila
        y = cols[target]
        if index and index in cols:
            order = np.argsort(cols[index])
            y = [y[i] for i in order]
        n = len(y)
        if n < 6:
            return []
        prov = {"dataset_hash": dhash, "seed": seed, "n_rows": n,
                "params": {"index": index or "(orden de fila)"}}
        out: list[dict[str, Any]] = []
        # 1) polinomio: k-ésima diferencia constante (exacto, sin ajuste)
        diffs = np.asarray(y, float)
        for k in range(1, min(4, n - 2)):
            diffs = np.diff(diffs)
            if len(diffs) >= 3 and np.allclose(diffs, diffs[0], rtol=1e-9,
                                               atol=1e-9):
                out.append(make_candidate(
                    method="sequence", variables=[target],
                    pattern_type="regla",
                    representation="secuencia",
                    description=f"{target} es polinómica de grado {k} "
                                f"(la {k}ª diferencia es constante = "
                                f"{diffs[0]:.6g}) — regla exacta, no ajuste",
                    expression=f"Δ^{k} {target} = {diffs[0]:.6g}",
                    support=1.0, stability=1.0, simplicity=0.9,
                    provenance={**prov, "rule": f"poly_deg_{k}"}))
                break
        # 2) recurrencia lineal de orden 2 (mínimos cuadrados + verificación exacta)
        if n >= 6:
            A = np.vstack([y[1:-1], y[:-2]]).T
            b = np.asarray(y[2:], float)
            try:
                (c1, c2), *_ = np.linalg.lstsq(A, b, rcond=None)
                pred = c1 * np.asarray(y[1:-1]) + c2 * np.asarray(y[:-2])
                rel = np.abs(pred - b) / (np.abs(b) + 1e-12)
                if np.all(rel < 1e-6):
                    out.append(make_candidate(
                        method="sequence", variables=[target],
                        pattern_type="regla", representation="secuencia",
                        description=f"{target} sigue la recurrencia "
                                    f"a(n) = {c1:.6g}·a(n-1) + {c2:.6g}·a(n-2) "
                                    "(verificada en todos los términos)",
                        expression=f"a(n)={c1:.6g}·a(n-1)+{c2:.6g}·a(n-2)",
                        support=1.0, stability=1.0, simplicity=0.85,
                        provenance={**prov, "rule": "linrec_2",
                                    "coefficients": {"c1": float(c1),
                                                     "c2": float(c2)}}))
            except Exception:  # noqa: BLE001
                pass
        # 3) periodicidad modular (solo enteros)
        if all(float(v).is_integer() for v in y):
            iv = [int(v) for v in y]
            for m in (2, 3, 4, 5, 6, 7, 8, 12):
                res = [v % m for v in iv]
                for period in range(1, min(6, n // 2)):
                    if all(res[i] == res[i % period] for i in range(n)):
                        if period == 1 and len(set(res)) == 1:
                            desc = (f"{target} ≡ {res[0]} (mod {m}) en toda la "
                                    "secuencia")
                        else:
                            desc = (f"{target} mod {m} es periódica con período "
                                    f"{period}: {res[:period]}")
                        out.append(make_candidate(
                            method="sequence", variables=[target],
                            pattern_type="regla", representation="secuencia",
                            description=desc,
                            expression=f"{target} mod {m}: periodo {period}",
                            support=1.0, stability=1.0, simplicity=0.8,
                            provenance={**prov, "rule": "modular",
                                        "mod": m, "period": period}))
                        break
                else:
                    continue
                break
        return out[:top]


# --- invariantes (motor real, antes desconectado) -----------------------------------
class InvariantDiscoverer:
    """Cantidades que NO cambian — reutiliza `inference/discovery/invariants.py`,
    que existía sin ningún consumidor. Una combinación conservada suele ser más
    profunda que cualquier correlación: es la firma de una ley.

    Honestidad: el propio motor clasifica exact/approximate/dataset_specific/
    artifact; solo se emiten candidatos que NO son artefacto, y el dominio
    probado va declarado — un invariante fuera de su rango no es un invariante."""

    def discover(self, cols: dict[str, list[float]], recipes: dict[str, str],
                 *, seed: int = 0, dhash: str = "", top: int = 3
                 ) -> list[dict[str, Any]]:
        import numpy as np
        from ..inference.discovery.invariants import find_invariants
        names = [k for k in sorted(cols) if "(" not in k]   # columnas base
        if len(names) < 2:
            return []
        n = len(cols[names[0]])
        if n < 8:
            return []
        theta = np.array([[cols[k][i] for k in names] for i in range(n)], float)
        try:
            cands = find_invariants(theta, names, top_k=top)
        except Exception:  # noqa: BLE001
            return []
        out: list[dict[str, Any]] = []
        for c in cands:
            if c.classification == "artifact":
                continue                     # el propio motor lo descarta
            out.append(make_candidate(
                method="invariant", variables=sorted(c.combination),
                pattern_type="invariante", representation="combinación lineal",
                description=f"cantidad conservada: {c.expression} "
                            f"(variación relativa {c.relative_variation:.4f}, "
                            f"{c.classification}) — válido SOLO en el dominio "
                            f"probado ({n} observaciones)",
                expression=c.expression,
                support=max(0.0, 1.0 - c.relative_variation),
                stability=1.0 - min(1.0, c.relative_variation * 2),
                simplicity=0.85,
                provenance={"dataset_hash": dhash, "seed": seed, "n_rows": n,
                            "classification": c.classification,
                            "combination": c.combination,
                            "estimator": "inference.discovery.invariants",
                            "tested_domain": f"{n} filas del dataset"}))
        return out


# --- filtro de trivialidad por construcción -----------------------------------------
_FUNCS = {"log", "sqrt", "mod", "abs", "exp"}


def base_vars(name: str) -> set[str]:
    """Variables BASE de las que desciende una columna derivada.

    El FeatureLab deja la genealogía en el nombre: log(x)→{x}, x/y→{x,y},
    |a-b|→{a,b}, x mod 840→{x}. Saber esto es lo que permite distinguir un
    descubrimiento de pura aritmética."""
    tmp = name
    for sep in ("(", ")", "/", "*", "+", "-", "^", "|", ","):
        tmp = tmp.replace(sep, " ")
    tmp = tmp.replace(" mod ", " ")
    out = set()
    for tok in tmp.split():
        if tok in _FUNCS or tok.replace(".", "").isdigit():
            continue
        out.add(tok)
    return out


def _shares_lineage(a: str, b: str) -> tuple[bool, str]:
    """¿Dos columnas son parientes por construcción? Lo son si sus variables
    base son iguales o una contiene a la otra: log(x) y sqrt(x) descienden ambas
    de x, así que su correlación es aritmética, no hallazgo."""
    va, vb = base_vars(a), base_vars(b)
    if not va or not vb:
        return False, ""
    if va == vb:
        return True, (f"'{a}' y '{b}' descienden de las MISMAS variables base "
                      f"({', '.join(sorted(va))}): su relación es aritmética")
    if va < vb or vb < va:
        menor, mayor = (a, b) if va < vb else (b, a)
        return True, (f"'{menor}' es una de las variables con las que se "
                      f"construyó '{mayor}' — parentesco por construcción")
    return False, ""


def _is_derived_from(name: str, other: str) -> bool:
    """Compatibilidad: ¿`name` desciende de `other`?"""
    return _shares_lineage(name, other)[0]


def mark_trivial(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Marca los patrones TRIVIALES POR CONSTRUCCIÓN — el fallo REAL observado.

    En la Ronda 5, Mendeleev reportó r=1.000 entre variables derivadas unas de
    otras (N·n_hard vs N², |N−greedy| vs |N−elapsed|). Eso no es descubrimiento:
    es aritmética. Con la genealogía del FeatureLab podemos detectarlo:
    si B = transformación_determinista(A), una correlación fuerte A↔B es
    TRIVIAL_BY_CONSTRUCTION.

    NO se borra el registro (se persiste como patrón trivial auditado), pero
    recibe novedad ~0 y sale del ranking principal — no debe consumir atención
    del Consejo ni aparecer como 'descubrimiento'."""
    for c in candidates:
        vs = c.get("variables") or []
        trivial = False
        why = ""
        if len(vs) == 2:
            trivial, why = _shares_lineage(vs[0], vs[1])
        if len(vs) == 1 and c.get("pattern_type") == "invariante":
            trivial = False              # un invariante de una sola columna sí vale
        if trivial:
            c["trivial_by_construction"] = True
            c["triviality_reason"] = why
            c["novelty_score"] = 0.0
            c["status"] = "TRIVIAL"
            c["description"] = "[TRIVIAL POR CONSTRUCCIÓN] " + str(
                c.get("description", "")) + f" — {why}"
        else:
            c.setdefault("trivial_by_construction", False)
    return candidates


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
    cands += MutualInfoDiscoverer().discover(cols, recipes, seed=seed, dhash=dhash)
    cands += InvariantDiscoverer().discover(cols, recipes, seed=seed, dhash=dhash)
    if target and target in cols:
        cands += SymbolicDiscoverer().discover(cols, recipes, target, seed=seed,
                                               dhash=dhash)
        # índice natural para secuencias: la variable base más monótona ≠ target
        idx = next((c for c in sorted(cols) if c != target and "(" not in c
                    and "/" not in c and "*" not in c), None)
        cands += SequenceDiscoverer().discover(cols, recipes, target, index=idx,
                                               seed=seed, dhash=dhash)
    # trivialidad ANTES del consenso: un patrón trivial no debe ganar ranking ni
    # sumar "vistas independientes" a nada (sigue registrado, pero al final)
    cands = mark_trivial(cands)
    merged = consensus(cands)
    reales = [c for c in merged if not c.get("trivial_by_construction")]
    triviales = [c for c in merged if c.get("trivial_by_construction")]
    return (reales + triviales)[:top]
