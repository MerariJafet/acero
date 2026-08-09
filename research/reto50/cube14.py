"""CUBE-AND-CONQUER para Caccetta–Häggkvist n=14 (k=3, outdeg>=5).

En vez de UNA búsqueda gigante, se parte el problema en 4096 CUBOS (asignaciones
de 12 aristas de ramificación) y se resuelve cada cubo en paralelo. Soundness:
los cubos son una partición COMPLETA del espacio sobre esas variables — si todos
son unsat, el problema original es unsat ⇒ n=14 PROBADO. Si algún cubo es sat,
hay contraejemplo (se verifica aparte). Escalación honesta: 60 s → los duros se
re-parten en 16 sub-cubos con 30 min → lo que sobreviva se reporta como lista de
cubos duros (resultado PARCIAL declarado, no inflado).

Codificación idéntica a frontier_toolkit.caccetta_haggkvist_bounded (WLOG sanos:
outdeg exacto por AtLeast/AtMost + vecindad de v0 fijada).
"""
from __future__ import annotations

import itertools
import sys
import time
from multiprocessing import Pool

import z3

N, K, D = 14, 3, 5                      # ceil(14/3) = 5
PHASE1_MS = 60_000
PHASE2_MS = 30 * 60_000
WORKERS = int(sys.argv[1]) if len(sys.argv) > 1 else 16
# 12 aristas de ramificación (entre vértices tempranos, tras el WLOG de v0)
BRANCH = [(1, j) for j in (2, 3, 4, 5, 6, 7)] + [(2, j) for j in (3, 4, 5, 6, 7, 8)]
SPLIT2 = [(3, j) for j in (4, 5, 6, 9)]  # sub-split de cubos duros (16 sub-cubos)


def _solver_and_vars() -> tuple[z3.Solver, list[list[z3.BoolRef]]]:
    e = [[z3.Bool(f"e_{i}_{j}") for j in range(N)] for i in range(N)]
    s = z3.Solver()
    for i in range(N):
        s.add(z3.Not(e[i][i]))
        row = [e[i][j] for j in range(N) if j != i]
        s.add(z3.AtLeast(*row, D))
        s.add(z3.AtMost(*row, D))
        for j in range(i + 1, N):
            s.add(z3.Not(z3.And(e[i][j], e[j][i])))
    for i in range(N):
        for j in range(N):
            for m in range(N):
                if len({i, j, m}) == 3:
                    s.add(z3.Not(z3.And(e[i][j], e[j][m], e[m][i])))
    for j in range(1, N):                                     # WLOG N+(0) = {1..D}
        s.add(e[0][j] if j <= D else z3.Not(e[0][j]))
    return s, e


def _run_cube(args: tuple[int, tuple[int, ...], int]) -> tuple[int, str, float]:
    idx, bits, timeout_ms = args
    t0 = time.time()
    s, e = _solver_and_vars()
    s.set("timeout", timeout_ms)
    vars_ = BRANCH if len(bits) == len(BRANCH) else BRANCH + SPLIT2
    lits = [e[i][j] if b else z3.Not(e[i][j])
            for (i, j), b in zip(vars_, bits)]
    r = s.check(*lits)
    verdict = ("unsat" if r == z3.unsat else
               "sat" if r == z3.sat else "unknown")
    return idx, verdict, time.time() - t0


def main() -> None:
    t0 = time.time()
    cubes = list(itertools.product((0, 1), repeat=len(BRANCH)))
    print(f"CUBE-AND-CONQUER n={N}: {len(cubes)} cubos, {WORKERS} obreros, "
          f"fase1 {PHASE1_MS // 1000}s/cubo", flush=True)
    unsat = sat_hits = 0
    hard: list[tuple[int, ...]] = []
    jobs = [(i, c, PHASE1_MS) for i, c in enumerate(cubes)]
    with Pool(WORKERS) as pool:
        for idx, v, dt in pool.imap_unordered(_run_cube, jobs):
            if v == "unsat":
                unsat += 1
            elif v == "sat":
                sat_hits += 1
                print(f"!!! SAT en cubo {idx} — POSIBLE CONTRAEJEMPLO, "
                      "verificar aparte", flush=True)
            else:
                hard.append(cubes[idx])
            done = unsat + sat_hits + len(hard)
            if done % 256 == 0:
                print(f"  fase1: {done}/{len(cubes)} (unsat={unsat} "
                      f"duros={len(hard)}) {time.time() - t0:.0f}s", flush=True)
    print(f"FASE1: unsat={unsat} sat={sat_hits} duros={len(hard)} "
          f"({time.time() - t0:.0f}s)", flush=True)
    if sat_hits == 0 and not hard:
        print(f"VEREDICTO: n={N} PROBADO por cube-and-conquer "
              f"({time.time() - t0:.0f}s)", flush=True)
        return
    # FASE 2: re-partir los cubos duros en 16 sub-cubos de 30 min
    sub = [(i, tuple(c) + s2, PHASE2_MS)
           for i, c in enumerate(hard)
           for s2 in itertools.product((0, 1), repeat=len(SPLIT2))]
    print(f"FASE2: {len(hard)} cubos duros → {len(sub)} sub-cubos "
          f"({PHASE2_MS // 60000} min c/u)", flush=True)
    unsat2 = sat2 = 0
    hard2 = 0
    with Pool(WORKERS) as pool:
        for idx, v, dt in pool.imap_unordered(_run_cube,
                                              [(i, b, t) for i, b, t in sub]):
            if v == "unsat":
                unsat2 += 1
            elif v == "sat":
                sat2 += 1
                print(f"!!! SAT en sub-cubo {idx}", flush=True)
            else:
                hard2 += 1
            done = unsat2 + sat2 + hard2
            if done % 64 == 0:
                print(f"  fase2: {done}/{len(sub)} (unsat={unsat2} "
                      f"duros={hard2}) {time.time() - t0:.0f}s", flush=True)
    print(f"FASE2: unsat={unsat2} sat={sat2} duros_restantes={hard2}", flush=True)
    if sat_hits == 0 and sat2 == 0 and hard2 == 0:
        print(f"VEREDICTO: n={N} PROBADO por cube-and-conquer en 2 fases "
              f"({(time.time() - t0) / 3600:.1f}h)", flush=True)
    else:
        print(f"VEREDICTO: PARCIAL — {hard2} sub-cubos resisten; "
              f"{100 * (unsat + unsat2) / (len(cubes) - len(hard) + len(sub)):.1f}%"
              f" del espacio cerrado ({(time.time() - t0) / 3600:.1f}h)",
              flush=True)
    print("FIN CUBE14", flush=True)


if __name__ == "__main__":
    main()
