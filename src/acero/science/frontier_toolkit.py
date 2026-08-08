"""FRONTIER TOOLKIT — maquinaria de teoría de números que sympy/Z3 solos no orquestan.

Da a ACERO capacidad REAL más allá de "verificar una identidad": descubre y PRUEBA
familias paramétricas, mapea obstrucciones por clases de residuos (coberturas), y
deriva/verifica condiciones necesarias sobre contraejemplos.

v3 — plantillas TIPO II: además de x,y lineales ((n+b)/c) se buscan términos PRODUCTO
y=(n+t1)(n+t2)/m, que son los que usan las identidades clásicas (Mordell) para las
clases n≡1 mod 4 (p.ej. n≡5 mod 8: x=(n+3)/4, y=n(n+3)/8, z=n(n+3)/4). La integridad
en toda la clase ya NO se muestrea: se PRUEBA sobre un período modular completo.

Honestidad: reproducir maquinaria clásica de forma AUTÓNOMA y VERIFICABLE es fiabilidad,
no descubrimiento; el valor de frontera está en las clases que quedan SIN cubrir.
"""
from __future__ import annotations

from fractions import Fraction
from math import ceil, gcd
from typing import Any

from sympy import Poly, Rational, Symbol, simplify, together


# --- descomposición egipcia de a/b en 3 términos (una, para muestrear) --------------
def egyptian3(a: int, b: int, xcap: int = 4, span: int = 6) -> tuple[int, int, int] | None:
    """Encuentra (x,y,z) con a/b = 1/x+1/y+1/z, x<=y<=z. Búsqueda acotada y exacta."""
    if a <= 0 or b <= 0:
        return None
    x_lo = ceil(Rational(b, a))                 # x >= b/a (para que 1/x <= a/b)
    for x in range(max(1, x_lo), x_lo + span * xcap + 2):
        r1 = Rational(a, b) - Rational(1, x)    # resto = 1/y + 1/z
        if r1 <= 0:
            continue
        p, q = r1.p, r1.q                        # p/q, con y<=z
        y_lo = ceil(Rational(q, p))
        for y in range(max(x, y_lo), y_lo + span * xcap + 2):
            r2 = r1 - Rational(1, y)
            if r2 <= 0:
                continue
            if r2.p == 1 and r2.q >= y:          # z entero, z>=y
                return (x, y, int(r2.q))
    return None


# --- prueba de integridad/positividad en TODA una clase de residuos -----------------
def _int_pos_on_class(expr: Any, n: Symbol, residue: int, modulus: int) -> bool:
    """PRUEBA (no muestreo) de que expr(n) es entero >=1 para todo n≡residue
    (mod modulus) con n>=2. Exige expr = p(n)/D con p de coeficientes enteros >=0
    (limitación declarada) y verifica p(n)≡0 (mod D) sobre un período COMPLETO:
    con coeficientes enteros, p(n) mod D solo depende de n mod D, y la clase
    recorre toda su órbita mod D en <=D pasos."""
    e = together(simplify(expr))
    num, den = e.as_numer_denom()
    if den.free_symbols:                          # denominador con n → no polinómico
        return False
    try:
        p = Poly(num, n)
        dq = Rational(den)
        coefs = [Rational(c) for c in p.all_coeffs()]
    except Exception:  # noqa: BLE001
        return False
    mult = 1                                       # escalar a enteros
    for c in [*coefs, dq]:
        q = int(c.q)
        mult = mult * q // gcd(mult, q)
    coefs_i = [int(c * mult) for c in coefs]
    d_int = int(dq * mult)
    if d_int < 0:
        d_int, coefs_i = -d_int, [-c for c in coefs_i]
    if d_int == 0 or any(c < 0 for c in coefs_i) or all(c == 0 for c in coefs_i):
        return False

    def pv(nv: int) -> int:
        v = 0
        for c in coefs_i:
            v = v * nv + c
        return v

    for i in range(d_int):                         # período completo mod D
        if pv(residue + i * modulus) % d_int:
            return False
    first = next(v for v in (residue + k * modulus for k in range(d_int + 3))
                 if v >= 2)
    return pv(first) >= d_int                      # >=1 en la clase (coefs no neg.)


# --- generadores de plantillas (pre-filtro en representantes; la prueba va después) -
def _linear_candidates(r: int, modulus: int, reps: list[int], kcap: int = 16,
                       scap: int = 33) -> list[tuple[list[int], tuple]]:
    """Plantillas x=(n+b)/c enteras y >=1 en los representantes."""
    out = []
    for c in range(1, kcap + 1):
        for b in range(scap):
            if any((nv + b) % c for nv in reps):
                continue
            vals = [(nv + b) // c for nv in reps]
            if all(v >= 1 for v in vals):
                out.append((vals, ("lin", b, c)))
    return out


def _quadratic_candidates(r: int, modulus: int, reps: list[int], tcap: int = 8,
                          scap: int = 33, mcap: int = 120
                          ) -> list[tuple[list[int], tuple]]:
    """Plantillas TIPO II y=(n+t1)(n+t2)/m — los términos producto de las identidades
    clásicas (Mordell) que cubren las clases n≡1 mod 4."""
    out = []
    for t1 in range(tcap):
        for t2 in range(t1, scap):
            vals = [(nv + t1) * (nv + t2) for nv in reps]
            for m in range(1, mcap + 1):
                if vals[0] % m == 0 and vals[1] % m == 0 and vals[2] % m == 0:
                    out.append(([v // m for v in vals], ("quad", t1, t2, m)))
    return out


def parametric_family(residue: int, modulus: int, coeff: int = 4
                      ) -> dict[str, Any] | None:
    """Para n ≡ residue (mod modulus): busca x=(n+b)/c y y lineal o TIPO II
    (n+t1)(n+t2)/m; deriva z = 1/(coeff/n − 1/x − 1/y) simbólicamente y PRUEBA
    (período modular completo + identidad exacta) que la familia vale en TODA la
    clase. Pre-filtro numérico EXACTO con Fraction para no pagar sympy en vano."""
    r = residue % modulus
    n = Symbol("n", positive=True, integer=True)
    reps = [r + k * modulus for k in range(12) if r + k * modulus >= 2][:3]
    if len(reps) < 3:
        return None
    xc = _linear_candidates(r, modulus, reps)
    yc = xc + _quadratic_candidates(r, modulus, reps)
    targets = [Fraction(coeff, nv) for nv in reps]

    def _expr(spec: tuple) -> Any:
        if spec[0] == "lin":
            _, b, c = spec
            return (n + b) / c
        _, t1, t2, m = spec
        return (n + t1) * (n + t2) / m

    for xvals, xspec in xc:
        rem = []
        for t, xv in zip(targets, xvals):
            rm = t - Fraction(1, xv)
            if rm <= 0:
                rem = None
                break
            rem.append(rm)
        if rem is None:
            continue
        for yvals, yspec in yc:
            ok = True
            for rm, yv in zip(rem, yvals):
                resid = rm - Fraction(1, yv)
                if resid <= 0 or resid.numerator != 1:   # z=1/resid entero>0
                    ok = False
                    break
            if not ok:
                continue
            # --- confirmación SIMBÓLICA + prueba de clase completa ----------------
            x = _expr(xspec)
            y = _expr(yspec)
            resid_s = simplify(Rational(coeff) / n - 1 / x - 1 / y)
            if resid_s == 0:
                continue
            z = simplify(1 / resid_s)
            if not z.free_symbols <= {n}:
                continue
            try:
                if (_int_pos_on_class(x, n, r, modulus)
                        and _int_pos_on_class(y, n, r, modulus)
                        and _int_pos_on_class(z, n, r, modulus)
                        and simplify(Rational(coeff) / n
                                     - (1 / x + 1 / y + 1 / z)) == 0):
                    return {"residue": r, "modulus": modulus,
                            "x": str(simplify(x)), "y": str(simplify(y)),
                            "z": str(z), "verified": True}
            except (TypeError, ValueError):
                continue
    return None


def erdos_straus_coverage_refined(base_mod: int, refined_mod: int, coeff: int = 4
                                  ) -> dict[str, Any]:
    """Cobertura con REFINAMIENTO de módulo: una clase r mod base_mod está cubierta si
    todas sus subclases mod refined_mod (refined_mod múltiplo de base_mod) tienen familia
    paramétrica verificada. Así se alcanza la cobertura clásica (que vive mod 840): el
    residuo duro real de Erdős–Straus son los cuadrados mod 840, todos ≡1 mod base_mod."""
    if refined_mod % base_mod:
        raise ValueError("refined_mod debe ser múltiplo de base_mod")
    base = erdos_straus_coverage(base_mod, coeff)
    hard = []
    for r in base["frontier"]:
        # refinar solo los residuos que la clase base no cubrió (rr=1 SÍ se examina:
        # la clase {1, 841, 1681, ...} tiene miembros válidos >= 2)
        for rr in range(r, refined_mod, base_mod):
            if not parametric_family(rr % refined_mod, refined_mod, coeff):
                hard.append(rr)
    return {"base_mod": base_mod, "refined_mod": refined_mod, "coeff": coeff,
            "hard_residues": sorted(hard), "n_hard": len(hard),
            "base_frontier": base["frontier"]}


def erdos_straus_coverage(modulus: int, coeff: int = 4) -> dict[str, Any]:
    """Mapa de cobertura de coeff/n = suma de 3 unitarias por clase de residuo mod
    `modulus`: qué residuos quedan CUBIERTOS por una familia paramétrica verificada y
    cuáles quedan en la FRONTERA (sin familia en el espacio de plantillas actual)."""
    covered, frontier, families = [], [], []
    for r in range(modulus):
        if r < 2 and r + modulus < 2:
            continue
        fam = parametric_family(r % modulus, modulus, coeff)
        if fam:
            covered.append(r)
            families.append(fam)
        else:
            frontier.append(r)
    return {"modulus": modulus, "coeff": coeff,
            "covered": covered, "frontier": frontier,
            "n_covered": len(covered), "n_frontier": len(frontier),
            "families": families[:12]}


# --- Caccetta–Häggkvist ACOTADO (k=3): prueba mecánica por Z3 caso a caso -----------
def caccetta_haggkvist_bounded(n_vertices: int, k: int = 3, timeout_ms: int = 300000
                               ) -> dict[str, Any]:
    """Caso FINITO de Caccetta–Häggkvist: todo digrafo simple (sin lazos ni digones
    como aristas dobles) con n vértices y grado de salida mínimo >= ceil(n/k) contiene
    un ciclo dirigido de longitud <= k. Para k=3, Z3 busca un contraejemplo (sin
    2-ciclos ni 3-ciclos y grado de salida >= ceil(n/3)); `unsat` = el caso n queda
    PROBADO mecánicamente. Devuelve proved / counterexample / unknown (timeout)."""
    import z3
    nv = n_vertices
    d = ceil(nv / k)
    e = [[z3.Bool(f"e_{i}_{j}") for j in range(nv)] for i in range(nv)]
    s = z3.Solver()
    s.set("timeout", timeout_ms)
    for i in range(nv):
        s.add(z3.Not(e[i][i]))                                   # sin lazos (C1)
        # WLOG outdeg EXACTO d: si hay contraejemplo con outdeg>=d, borrar aristas
        # (no crea ciclos) da uno con outdeg==d en todo vértice — reducción sana.
        # Cardinalidad NATIVA (AtLeast/AtMost): órdenes de magnitud mejor que Sum.
        row = [e[i][j] for j in range(nv) if j != i]
        s.add(z3.AtLeast(*row, d))
        s.add(z3.AtMost(*row, d))
        for j in range(i + 1, nv):
            s.add(z3.Not(z3.And(e[i][j], e[j][i])))              # sin 2-ciclos
    # WLOG (reetiquetado): los d vecinos de salida del vértice 0 son {1..d}
    for j in range(1, nv):
        s.add(e[0][j] if j <= d else z3.Not(e[0][j]))
    if k >= 3:
        for i in range(nv):
            for j in range(nv):
                for m in range(nv):
                    if len({i, j, m}) == 3:
                        s.add(z3.Not(z3.And(e[i][j], e[j][m], e[m][i])))  # sin 3-ciclos
    res = s.check()
    if res == z3.unsat:
        verdict = "proved"
    elif res == z3.sat:
        verdict = "counterexample"
    else:
        verdict = "unknown"
    out: dict[str, Any] = {"n": nv, "k": k, "min_outdeg": d, "result": verdict}
    if verdict == "counterexample":                              # ¡sería un bombazo!
        mdl = s.model()
        out["edges"] = [(i, j) for i in range(nv) for j in range(nv)
                        if z3.is_true(mdl.eval(e[i][j]))]
    return out


# --- condiciones necesarias sobre contraejemplos (generaliza Lehmer), Z3-verificadas -
def coprime_divisor_obstruction() -> bool:
    """Lema base verificado por Z3: para p>=2 es imposible que p|n y p|(n-1).
    Es la raíz de 'todo contraejemplo de divisibilidad d(n)|(n-1) es libre de cuadrados'."""
    try:
        import z3
        p, n = z3.Ints("p n")
        s = z3.Solver()
        s.add(p >= 2, n >= 1, n % p == 0, (n - 1) % p == 0)
        return s.check() == z3.unsat
    except Exception:  # noqa: BLE001
        return False
