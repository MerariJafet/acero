"""De la evidencia al TEOREMA: clases de congruencia demostrables por llave.

Marco (regla tipo II): para primo p ≡ 1 (mod 4) y llave k ≡ 3 (mod 4),
x = (p+k)/4, y la llave decide a p ⇔ ∃ t | (p·x)² con t ≡ −p·x (mod k).

IDEA-TEOREMA: los divisores MONOMIALES t = p^a · x^b (a,b ∈ {0,1,2}) siempre
dividen (px)². Para cada monomio, la condición t ≡ −px (mod k) se convierte en
una CONGRUENCIA EXACTA sobre p mod k (usando 4x ≡ p+... y k∤p). Resolver esa
congruencia da CLASES DE RESIDUOS donde la llave decide SIEMPRE — un teorema
por clase, con prueba simbólica (identidad y divisibilidad verificadas con
sympy sobre la parametrización p = k·K·m + r, período completo).

Salida por llave: clases probadas, % de primos duros EXPLICADOS por teorema,
y el RESIDUAL (cubiertos solo por divisores compuestos — la parte 'aleatoria').

Uso: python teorema_llaves.py [N] [llaves...]
"""
from __future__ import annotations

import sys
from fractions import Fraction

from sympy import Symbol, divisors, factorint, gcd, primerange, simplify

BAD = {1, 121, 169, 289, 361, 529}
MONOMIOS = [(a, b) for a in range(3) for b in range(3)]  # t = p^a x^b


def clases_probadas(k: int) -> dict[tuple[int, int], list[int]]:
    """Para cada monomio (a,b): resuelve p^a x^b ≡ −p x (mod k) con 4x ≡ p (mod k)
    (pues x=(p+k)/4 ⇒ 4x = p+k ≡ p). Devuelve las clases r = p mod k solubles
    con gcd(r,k)=1 (p primo > k). Resolución EXACTA por enumeración de residuos."""
    inv4 = pow(4, -1, k)
    out: dict[tuple[int, int], list[int]] = {}
    for a, b in MONOMIOS:
        clases = []
        for r in range(1, k):
            if gcd(r, k) != 1:
                continue
            xr = (r * inv4) % k                      # x ≡ p/4 (mod k)
            t = (pow(r, a, k) * pow(xr, b, k)) % k
            if t == (-r * xr) % k:
                clases.append(r)
        out[(a, b)] = clases
    return out


def prueba_simbolica(k: int, a: int, b: int, r: int) -> bool:
    """PRUEBA del caso (monomio p^a x^b, clase p ≡ r mod k): sobre la
    parametrización p = 4k·m + r4 (todas las sub-clases r4 mod 4k con r4 ≡ r
    mod k y r4 ≡ 1 mod 4), verifica SIMBÓLICAMENTE que t | (px)²,
    t ≡ −px (mod k), y que y=(px+t)/k, z=px(px+t)/(k·t) son enteros positivos
    con 4/p = 1/x+1/y+1/z. Integridad por período modular completo (exacta)."""
    m = Symbol("m", positive=True, integer=True)
    ok_alguna = False
    for r4 in range(r % k, 4 * k, k):
        if r4 % 4 != 1 or r4 == 0:
            continue
        p = 4 * k * m + r4
        x = (p + k) / 4                              # entero: p ≡ 1 mod 4, k ≡ 3
        t = p**a * x**b
        y = (p * x + t) / k
        z = p * x * (p * x + t) / (k * t)
        ident = simplify(Fraction(4, 1) / p - (1 / x + 1 / y + 1 / z))
        if ident != 0:
            return False
        # integridad exacta por período: cada expresión debe ser entera para
        # TODO m (numerador ≡ 0 mod denominador en un período completo)
        for expr in (x, y, z):
            num, den = simplify(expr).as_numer_denom()
            if den.free_symbols:
                return False
            d = int(den)
            if any(int(num.subs(m, mm)) % d for mm in range(1, d + 2)):
                return False
        ok_alguna = True
    return ok_alguna


def cobertura_empirica(k: int, primos: list[int]) -> dict[int, tuple[int, int]]:
    """Por clase r = p mod k: (cubiertos con la llave k, total)."""
    stats: dict[int, list[int]] = {}
    for p in primos:
        r = p % k
        cub = 0
        if (p + k) % 4 == 0:
            x = (p + k) // 4
            px = p * x
            fac = {int(q): 2 * int(e) for q, e in factorint(x).items()}
            fac[p] = fac.get(p, 0) + 2
            target = (-px) % k
            divs = [1]
            for q, e in fac.items():
                divs = [d * q**i for d in divs for i in range(e + 1)]
            cub = int(any(t % k == target for t in divs))
        c, tot = stats.get(r, (0, 0)) if r in stats else (0, 0)
        stats[r] = (c + cub, tot + 1)
    return stats


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10**6
    llaves = [int(v) for v in sys.argv[2:]] or [23, 31, 47, 59, 71]
    primos = [int(p) for p in primerange(5, n + 1) if int(p) % 840 in BAD]
    print(f"N={n} primos_duros={len(primos)} llaves={llaves}", flush=True)
    for k in llaves:
        cp = clases_probadas(k)
        probadas: set[int] = set()
        detalles = []
        for (a, b), clases in cp.items():
            for r in clases:
                if r in probadas:
                    continue
                if prueba_simbolica(k, a, b, r):
                    probadas.add(r)
                    detalles.append(f"p≡{r} (t=p^{a}·x^{b})")
        emp = cobertura_empirica(k, primos)
        exp_n = sum(c for r, (c, tot) in emp.items() if r in probadas)
        exp_tot = sum(tot for r, (c, tot) in emp.items() if r in probadas)
        cub_n = sum(c for c, tot in emp.values())
        tot = sum(t for c, t in emp.values())
        parciales = {r: f"{c}/{t}" for r, (c, t) in sorted(emp.items())
                     if r not in probadas and c}
        print(f"\n=== LLAVE k={k} ===", flush=True)
        print(f"TEOREMA: decide SIEMPRE las clases {sorted(probadas)} (mod {k})"
              f" — {'; '.join(detalles)}", flush=True)
        if exp_tot:
            print(f"  verificación empírica de lo probado: {exp_n}/{exp_tot} "
                  f"(debe ser {exp_tot}/{exp_tot})", flush=True)
        print(f"  cobertura total de k={k}: {cub_n}/{tot} "
              f"({100 * cub_n / tot:.1f}%) | explicada por TEOREMA: "
              f"{exp_tot}/{tot} ({100 * exp_tot / tot:.1f}%) | residual "
              f"(divisores compuestos): {100 * (cub_n - exp_n) / tot:.1f}%",
              flush=True)
        print(f"  clases parciales (empíricas): {parciales}", flush=True)


if __name__ == "__main__":
    main()
