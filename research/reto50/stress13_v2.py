"""Estrés a GRAN escala del lema de covering sets de Erdős–Straus (clases duras).

v2 — diseñado para 10⁸/10⁹:
- COBERTURA UNIVERSAL con salida temprana: para cada primo se prueban los k en
  orden de potencia empírica (23, 47, 11, …) y se registra el PRIMER k que cubre;
  un primo sin k ≤ KMAX es un hallazgo mayor (se reporta de inmediato).
- MATRIZ COMPLETA solo en una muestra estratificada (1 de cada SAMPLE_EVERY),
  para estimar el crecimiento del cover mínimo sin pagar el costo total.
- multiprocessing sobre trozos de primos; aritmética exacta (Fraction) en la
  verificación de cada certificado hallado.

Uso: python stress13_v2.py N [KMAX] [SAMPLE_EVERY] [WORKERS]
"""
from __future__ import annotations

import sys
import time
from fractions import Fraction
from multiprocessing import Pool

from sympy import factorint, primerange

BAD = frozenset({1, 121, 169, 289, 361, 529})
# orden de potencia empírica observado en 1e5/1e6/1e7 (los demás k después)
K_ORDER_HEAD = [23, 47, 11, 31, 71, 39, 119, 95, 59, 7, 15, 3, 19, 63, 127, 167]


def _divisors(fac: dict[int, int]) -> list[int]:
    divs = [1]
    for q, e in fac.items():
        divs = [d * q**i for d in divs for i in range(e + 1)]
    return divs


def _solvable(p: int, k: int) -> bool:
    p, k = int(p), int(k)          # sympy Integer rompe Fraction tras pickling
    if (p + k) % 4:
        return False
    x = (p + k) // 4
    px = p * x
    fac: dict[int, int] = {p: 2}
    for q, e in factorint(x).items():
        fac[int(q)] = fac.get(int(q), 0) + 2 * int(e)
    target = (-px) % k
    for t in _divisors(fac):
        if t % k == target:
            y = (px + t) // k
            num = px * (px + t)
            if num % (k * t) == 0:
                z = num // (k * t)
                if Fraction(4, p) == (Fraction(1, x) + Fraction(1, y)
                                      + Fraction(1, z)):
                    return True
    return False


def _work(args: tuple[list[int], list[int], int]) -> tuple[dict, list, list]:
    primes, ks, sample_every = args
    first_k: dict[int, int] = {}      # k → cuántos primos cubrió PRIMERO
    uncovered: list[int] = []
    sample_rows: list[tuple[int, list[int]]] = []   # (p, ks_que_lo_cubren)
    for i, p in enumerate(primes):
        hit = None
        for k in ks:
            if _solvable(p, k):
                hit = k
                break
        if hit is None:
            uncovered.append(p)
        else:
            first_k[hit] = first_k.get(hit, 0) + 1
        if i % sample_every == 0:                    # matriz completa muestreada
            sample_rows.append((p, [k for k in ks if _solvable(p, k)]))
    return first_k, uncovered, sample_rows


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10**8
    kmax = int(sys.argv[2]) if len(sys.argv) > 2 else 255
    sample_every = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    t0 = time.time()
    ks = K_ORDER_HEAD + [k for k in range(3, kmax + 1, 4)
                         if k not in K_ORDER_HEAD]
    print(f"N={n} kmax={kmax} muestra=1/{sample_every} workers={workers}",
          flush=True)
    primes = [int(p) for p in primerange(5, n + 1) if int(p) % 840 in BAD]
    print(f"primos_duros={len(primes)} (criba {time.time() - t0:.0f}s)",
          flush=True)
    chunk = max(1, len(primes) // (workers * 8))
    jobs = [(primes[i:i + chunk], ks, sample_every)
            for i in range(0, len(primes), chunk)]
    first_k: dict[int, int] = {}
    uncovered: list[int] = []
    sample: list[tuple[int, list[int]]] = []
    done = 0
    with Pool(workers) as pool:
        for fk, unc, smp in pool.imap_unordered(_work, jobs):
            for k, c in fk.items():
                first_k[k] = first_k.get(k, 0) + c
            uncovered.extend(unc)
            sample.extend(smp)
            done += 1
            if done % 8 == 0:
                print(f"  trozos {done}/{len(jobs)} "
                      f"({time.time() - t0:.0f}s)", flush=True)
    print(f"EVIDENCIA: sin_cobertura_con_k<={kmax}: {len(uncovered)} "
          f"{sorted(uncovered)[:10]}", flush=True)
    top_first = sorted(first_k.items(), key=lambda kv: -kv[1])[:10]
    print("EVIDENCIA: primer_k_que_cubre (orden de prueba): "
          + ", ".join(f"k={k}:{c}" for k, c in top_first), flush=True)
    # set-cover voraz sobre la MUESTRA (estimador del cover mínimo)
    universe = {p for p, kk in sample if kk}
    cov = {k: {p for p, kk in sample if k in kk} for k in ks}
    chosen: list[int] = []
    remaining = set(universe)
    while remaining:
        best = max(ks, key=lambda k: len(cov[k] & remaining))
        if not cov[best] & remaining:
            break
        chosen.append(best)
        remaining -= cov[best]
    print(f"EVIDENCIA: muestra={len(sample)} primos; cover_voraz_en_muestra="
          f"{len(chosen)} k={sorted(chosen)}", flush=True)
    ok = not uncovered
    print(f"VEREDICTO: {'CUBIERTO' if ok else 'INCOMPLETO'} hasta N={n} "
          f"({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
