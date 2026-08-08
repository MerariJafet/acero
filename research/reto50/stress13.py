"""Estrés del lema de cobertura auxiliar de Erdős–Straus (clases duras mod 840).

Regla PRECISA y clásica (tipo II), sin ambigüedad:
  para primo p ≡ 1 (mod 4) y auxiliar k ≡ 3 (mod 4):  x = (p+k)/4;
  4/p = 1/x + 1/y + 1/z  es soluble con ese k  ⇔  ∃ t | (p·x)² con t ≡ −p·x (mod k)
  (entonces y = (p·x+t)/k, z = p·x·(p·x+t)/(k·t); todo verificado con Fraction).

Pregunta del lema: ¿existe un conjunto FIJO y pequeño S de auxiliares k que
DECIDA todos los primos de las 6 clases duras {1,121,169,289,361,529} mod 840
hasta N? En N=1e5 la corrida del Consejo halló cobertura total con 13 valores.
Aquí se estresa a N=1e6 / 1e7: cobertura por k, set-cover voraz + refinamiento,
y estabilidad del conjunto al crecer N. Todo exacto; muestra re-verificada.

Uso: python stress13.py N [KMAX]
"""
from __future__ import annotations

import sys
import time
from fractions import Fraction

from sympy import factorint, primerange

BAD = {1, 121, 169, 289, 361, 529}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 10**6
KMAX = int(sys.argv[2]) if len(sys.argv) > 2 else 127


def divisors_from_factors(fac: dict[int, int]) -> list[int]:
    divs = [1]
    for q, e in fac.items():
        divs = [d * q**i for d in divs for i in range(e + 1)]
    return divs


def solvable_with_k(p: int, k: int) -> tuple[int, int, int] | None:
    """Certificado (x,y,z) con el auxiliar k, o None. Exacto."""
    if (p + k) % 4:
        return None
    x = (p + k) // 4
    px = p * x
    fac = factorint(x)
    fac2: dict[int, int] = {p: 2}
    for q, e in fac.items():
        fac2[q] = fac2.get(q, 0) + 2 * e
    target = (-px) % k
    for t in divisors_from_factors(fac2):
        if t % k == target and (px + t) % k == 0:
            y = (px + t) // k
            num = px * (px + t)
            if num % (k * t) == 0:
                z = num // (k * t)
                if Fraction(4, p) == (Fraction(1, x) + Fraction(1, y)
                                      + Fraction(1, z)):
                    return (x, y, z)
    return None


def main() -> None:
    t0 = time.time()
    primes = [p for p in primerange(5, N + 1) if p % 840 in BAD]
    ks = [k for k in range(3, KMAX + 1, 4)]          # k ≡ 3 mod 4 (p ≡ 1 mod 4)
    print(f"N={N} primos_duros={len(primes)} auxiliares_k={len(ks)} "
          f"(k≡3 mod 4, k<={KMAX})", flush=True)
    cover: dict[int, set[int]] = {k: set() for k in ks}
    uncovered_any: list[int] = []
    for i, p in enumerate(primes):
        hit = False
        for k in ks:
            if solvable_with_k(p, k):
                cover[k].add(p)
                hit = True
        if not hit:
            uncovered_any.append(p)
        if (i + 1) % 500 == 0:
            print(f"  progreso {i + 1}/{len(primes)} "
                  f"({time.time() - t0:.0f}s)", flush=True)
    print(f"EVIDENCIA: sin_cobertura_con_ningun_k={len(uncovered_any)} "
          f"{uncovered_any[:10]}", flush=True)
    # set-cover voraz + poda (mínimo aproximado, exacto en tamaño pequeño)
    remaining = set(p for p in primes if p not in set(uncovered_any))
    chosen: list[int] = []
    while remaining:
        best = max(ks, key=lambda k: len(cover[k] & remaining))
        got = cover[best] & remaining
        if not got:
            break
        chosen.append(best)
        remaining -= got
    # poda: quitar elegidos redundantes
    for k in sorted(chosen, key=lambda k: len(cover[k])):
        rest = [c for c in chosen if c != k]
        if rest and set().union(*(cover[c] for c in rest)) >= set(
                p for p in primes if p not in set(uncovered_any)):
            chosen = rest
    chosen.sort()
    print(f"EVIDENCIA: set_cover_voraz+poda={len(chosen)} k={chosen}", flush=True)
    covered = set().union(*(cover[k] for k in chosen)) if chosen else set()
    print(f"EVIDENCIA: cubiertos_por_elegidos={len(covered)}/{len(primes)}",
          flush=True)
    # los k más potentes individualmente (para comparar entre rangos)
    top = sorted(ks, key=lambda k: -len(cover[k]))[:8]
    print("EVIDENCIA: top_k_individuales="
          + ", ".join(f"k={k}:{len(cover[k])}" for k in top), flush=True)
    ok = (not uncovered_any) and len(covered) == len(primes)
    print(f"VEREDICTO: {'CUBIERTO' if ok else 'INCOMPLETO'} con "
          f"{len(chosen)} auxiliares hasta N={N} "
          f"({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
