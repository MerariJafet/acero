"""MECANISMO DEL TESTIGO — los dientes de la llave dejan de ser metáfora.

Reformulación de Merari (2026-08-11), segunda vuelta. La primera vuelta cambió
k_min(p) por A(p); ésta baja un piso más, hasta el mecanismo.

El criterio sellado dice: k abre p ⟺ ∃ t | (p·x)² con t ≡ −p·x (mod k),
x = (p+k)/4. Como p es primo y x = q_1^{e_1}···q_r^{e_r}, TODO testigo posible
tiene forma forzada

    t = p^a · q_1^{b_1} ··· q_r^{b_r},   0 ≤ a ≤ 2,  0 ≤ b_i ≤ 2·e_i.

Es decir: los factores de p·x son las PIEZAS, el vector de exponentes
(a, b_1, …, b_r) son los DIENTES, y la congruencia dice qué forma deben tener.
El testigo t no se busca: se CONSTRUYE eligiendo exponentes.

Eso permite definir dos objetos y una equivalencia:

    R_k(p) = { t mod k : t | (p·x)² }        (residuos fabricables)
    r_k(p) = −p·x mod k                      (residuo que pide la cerradura)
    k abre p  ⟺  r_k(p) ∈ R_k(p)

Y hay una simplificación que Merari sacó a mano y aquí se verifica en cada
llamada: como k es impar, 4 es invertible mod k, y 4x = p+k ≡ p (mod k), luego
x ≡ p·4⁻¹ y por tanto

    r_k(p) ≡ −p²·4⁻¹ (mod k)

o sea que el objetivo NO depende de la factorización de x — solo de p y k. Lo
difícil está entero del otro lado: si las piezas disponibles pueden generarlo.

LO QUE ESTO PERMITE DISTINGUIR (y es la razón de existir del módulo): cuando k
NO abre p, hay dos causas cualitativamente distintas que la estadística de
superficie confunde en un solo "falló":

  * OBSTRUCCIÓN ESTRUCTURAL — r_k(p) no está ni en el subgrupo ⟨q_i mod k⟩.
    Ningún presupuesto de exponentes lo arreglaría: la llave no tiene esos
    dientes, punto.
  * PRESUPUESTO INSUFICIENTE — r_k(p) SÍ está en el subgrupo, pero exige
    exponentes mayores que los 2·e_i disponibles. Los dientes existen pero son
    demasiado cortos.

La segunda es accionable (más multiplicidad ⇒ abre) y la primera no. Confundirlas
es exactamente lo que hacía la regla `qr_11 == 10`, que comprimía todo esto en
un bit sobre p.
"""
from __future__ import annotations

import json
import math
import os
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))


_PARI = None


def factor(n: int) -> dict[int, int]:
    """PARI (7× sympy a escala 1e11); sympy de respaldo."""
    global _PARI
    if _PARI is None:
        try:
            import cypari2
            _PARI = cypari2.Pari()
        except Exception:  # noqa: BLE001
            _PARI = False
    if _PARI:
        m = _PARI(n).factor()
        return {int(m[0][i]): int(m[1][i]) for i in range(len(m[0]))}
    from sympy import factorint
    return {int(q): int(e) for q, e in factorint(n).items()}


def target_residue(p: int, k: int) -> int:
    """r_k(p) = −p·x mod k, con x=(p+k)/4.

    Se calcula por la vía corta (−p²·4⁻¹) y se CONTRASTA con la directa. No es
    paranoia decorativa: la identidad es el corazón de la reformulación, y si
    algún día se rompe (k par, gcd(k,4)≠1) queremos enterarnos aquí y no tres
    rondas después."""
    if (p + k) % 4 != 0:
        raise ValueError(f"p+k no divisible por 4: p={p} k={k}")
    x = (p + k) // 4
    directo = (-(p % k) * (x % k)) % k
    corto = (-pow(p, 2, k) * pow(4, -1, k)) % k
    if directo != corto:
        raise AssertionError(
            f"identidad rota: p={p} k={k} directo={directo} corto={corto}")
    return directo


def pieces(p: int, k: int) -> list[tuple[int, int, int]]:
    """Las PIEZAS disponibles: (primo q, residuo q mod k, exponente máximo).

    Solo entran los q coprimos con k. Justificación, no comodidad: el objetivo
    r_k(p) es unidad mod k siempre que gcd(p·x,k)=1, y entonces gcd(t,k)=1, así
    que un q con gcd(q,k)>1 tendría que llevar exponente 0 de todos modos."""
    x = (p + k) // 4
    fac: dict[int, int] = {}
    for q, e in factor(p).items():
        fac[q] = fac.get(q, 0) + 2 * e
    for q, e in factor(x).items():
        fac[q] = fac.get(q, 0) + 2 * e
    out = []
    for q, e in sorted(fac.items()):
        g = q % k
        if math.gcd(g, k) != 1 or g == 1:
            continue
        out.append((q, g, e))
    return out


def _order(g: int, k: int) -> int:
    o, cur = 1, g % k
    while cur != 1:
        cur = (cur * g) % k
        o += 1
        if o > k:
            return k
    return o


def reachable_bounded(p: int, k: int) -> dict[int, dict[int, int]]:
    """R_k(p): residuo → vector de exponentes que lo fabrica.

    Devolver el CÓMO y no solo el qué es lo que hace que un camino en este grafo
    sea directamente un certificado: de los exponentes sale t, y de t sale la
    verificación mecánica."""
    reached: dict[int, dict[int, int]] = {1 % k: {}}
    for q, g, e in pieces(p, k):
        tope = min(e, _order(g, k) - 1)       # más allá del orden solo se repite
        nxt = dict(reached)
        for r, expo in reached.items():
            v = r
            for j in range(1, tope + 1):
                v = (v * g) % k
                if v not in nxt:
                    nxt[v] = {**expo, q: j}
        reached = nxt
    return reached


def subgroup_closure(p: int, k: int) -> set[int]:
    """⟨q_i mod k⟩ — lo alcanzable con exponentes ILIMITADOS.

    Es la frontera de lo posible en principio. La diferencia con R_k(p) es
    exactamente el presupuesto de dientes."""
    cur = {1 % k}
    for _q, g, _e in pieces(p, k):
        nuevo = set()
        for r in cur:
            v = r
            for _ in range(_order(g, k)):
                v = (v * g) % k
                nuevo.add(v)
        cur |= nuevo
    return cur


def diagnose(p: int, k: int) -> dict[str, Any]:
    """Autopsia de una puerta y una llave. El objeto central de la Ronda 7."""
    if (p + k) % 4 != 0:
        return {"p": p, "k": k, "veredicto": "mal_formada",
                "razon": "p+k no es divisible por 4 (ni siquiera entra la llave)"}
    x = (p + k) // 4
    r = target_residue(p, k)
    R = reachable_bounded(p, k)
    S = subgroup_closure(p, k)
    pz = pieces(p, k)
    if r in R:
        expo = R[r]
        t = 1
        for q, j in expo.items():
            t *= q ** j
        sq = (p * x) ** 2
        ok = (sq % t == 0) and ((t - (-(p * x))) % k == 0)
        veredicto = "abre" if ok else "testigo_invalido"
    elif r in S:
        veredicto = "presupuesto_insuficiente"
        t, expo, ok = None, None, False
    else:
        veredicto = "obstruccion_estructural"
        t, expo, ok = None, None, False
    return {"p": p, "k": k, "x": x, "objetivo": r, "veredicto": veredicto,
            "testigo": t, "exponentes": {str(q): j for q, j in (expo or {}).items()},
            "verificado": ok,
            "n_piezas": len(pz),
            "piezas": [{"q": q, "q_mod_k": g, "exp_max": e} for q, g, e in pz],
            "n_alcanzables": len(R), "n_subgrupo": len(S),
            "alcanzables": sorted(R), "subgrupo": sorted(S),
            "faltan_del_subgrupo": sorted(S - set(R))}


# --- KPI correcto: no acertar a la primera, sino gastar pocos intentos ------------
def tries_until_open(p: int, orden: list[int]) -> int | None:
    """Cuántas llaves hay que PROBAR hasta obtener un certificado, siguiendo un
    orden dado. Éste es el KPI que importa: como cada candidato se verifica
    mecánicamente, equivocarse solo cuesta tiempo, no corrección. Medir accuracy
    al primer intento castiga a un sistema que acierta al segundo y sería
    igual de útil."""
    for i, k in enumerate(orden, 1):
        if (p + k) % 4 != 0:
            continue
        d = diagnose(p, k)
        if d["veredicto"] == "abre":
            return i
    return None


def evaluate_orders(rows: list[dict[str, Any]], ordenes: dict[str, list[int]]
                    ) -> dict[str, Any]:
    """Compara políticas de orden de llavero por intentos gastados.

    `static-ranked-keyring` (llaves por frecuencia global) es la línea base que
    cualquier política adaptativa tiene que superar de verdad — no basta con
    superar 'no hacer nada'."""
    out: dict[str, Any] = {}
    for nombre, orden in ordenes.items():
        intentos = []
        for r in rows:
            keys = set(r["keys"])
            n = None
            for i, k in enumerate(orden, 1):
                if k in keys:
                    n = i
                    break
            intentos.append(n)
        hechos = [n for n in intentos if n]
        out[nombre] = {
            "n": len(rows), "sin_llave_en_el_orden": sum(1 for n in intentos if not n),
            "media_intentos": round(sum(hechos) / len(hechos), 3) if hechos else None,
            "p_exito_1": round(sum(1 for n in hechos if n <= 1) / len(rows), 4),
            "p_exito_3": round(sum(1 for n in hechos if n <= 3) / len(rows), 4),
            "p_exito_5": round(sum(1 for n in hechos if n <= 5) / len(rows), 4),
            "peor_caso": max(hechos) if hechos else None,
        }
    return out
