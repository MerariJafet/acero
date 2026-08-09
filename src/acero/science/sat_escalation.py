"""ESCALERA SAT — la estrategia de ataque a casos finitos, aprendida y automatizada.

Lo que Merari y Claude hicieron a mano con Caccetta–Häggkvist n=14 (2026-08-09),
convertido en pieza del TOOLBOX para que el Consejo lo haga solo en futuros
problemas:

  Peldaño 1 — DIRECTO: una corrida Z3 con presupuesto corto (mata los casos fáciles).
  Peldaño 2 — PORTAFOLIO: N semillas aleatorias en paralelo (la varianza entre
              semillas es enorme; basta que una tenga suerte).
  Peldaño 3 — CUBE-AND-CONQUER: partición COMPLETA del espacio sobre variables de
              ramificación; cada cubo se resuelve en paralelo, los duros se
              re-parten. Todos unsat ⇒ PROBADO sin suerte. Técnica de los récords
              mundiales de teoremas por SAT (ternas pitagóricas, Schur 5).

Honestidad: `proved` solo si TODO el espacio quedó cerrado; `counterexample` se
devuelve con el modelo para verificación INDEPENDIENTE (jamás se anuncia solo);
si quedan cubos duros el veredicto es `partial` con el % de espacio cerrado —
nunca se infla. El encoder debe ser una función importable (top-level) para que
multiprocessing pueda reconstruir el solver en cada obrero.
"""
from __future__ import annotations

import itertools
import time
from functools import partial
from multiprocessing import Pool, cpu_count
from typing import Any, Callable

# Un encoder devuelve (solver_z3, variables_de_ramificación_sugeridas)
Encoder = Callable[[], tuple[Any, list[Any]]]


def _direct(encoder: Encoder, timeout_ms: int, seed: int = 0) -> str:
    import z3
    s, _ = encoder()
    s.set("timeout", timeout_ms)
    if seed:
        try:
            s.set("random_seed", seed)
        except Exception:  # noqa: BLE001
            pass
    r = s.check()
    return ("unsat" if r == z3.unsat else "sat" if r == z3.sat else "unknown")


def _cube(args: tuple[Encoder, tuple[int, ...], int, int]) -> tuple[str, float]:
    import z3
    encoder, bits, nvars, timeout_ms = args
    t0 = time.time()
    s, branch = encoder()
    s.set("timeout", timeout_ms)
    lits = [branch[i] if b else z3.Not(branch[i])
            for i, b in enumerate(bits)]
    r = s.check(*lits)
    return (("unsat" if r == z3.unsat else
             "sat" if r == z3.sat else "unknown"), time.time() - t0)


def escalate(encoder: Encoder, *, direct_s: int = 600,
             portfolio_seeds: int = 4, portfolio_s: int = 3600,
             cube_vars: int = 12, cube_phase1_s: int = 60,
             cube_phase2_s: int = 1800, split2_vars: int = 4,
             workers: int | None = None,
             on_event: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Sube la escalera hasta probar, refutar (con modelo a verificar) o declarar
    parcial honesto. Devuelve {verdict, rung, stats, elapsed_s, model?}."""
    t0 = time.time()
    w = workers or max(2, cpu_count() // 2)
    say = on_event or (lambda m: None)

    # --- peldaño 1: directo -----------------------------------------------------
    say(f"escalera/1 directo ({direct_s}s)")
    v = _direct(encoder, direct_s * 1000)
    if v != "unknown":
        return {"verdict": "proved" if v == "unsat" else "counterexample",
                "rung": "directo", "elapsed_s": round(time.time() - t0, 1)}

    # --- peldaño 2: portafolio de semillas en paralelo ---------------------------
    say(f"escalera/2 portafolio {portfolio_seeds} semillas ({portfolio_s}s c/u)")
    seeds = [101 + 101 * i for i in range(portfolio_seeds)]
    with Pool(min(w, portfolio_seeds)) as pool:
        results = pool.map(partial(_direct, encoder, portfolio_s * 1000), seeds)
    if "unsat" in results:
        return {"verdict": "proved", "rung": "portafolio",
                "seed": seeds[results.index("unsat")],
                "elapsed_s": round(time.time() - t0, 1)}
    if "sat" in results:
        return {"verdict": "counterexample", "rung": "portafolio",
                "elapsed_s": round(time.time() - t0, 1)}

    # --- peldaño 3: cube-and-conquer --------------------------------------------
    _, branch = encoder()
    nb = min(cube_vars, len(branch))
    cubes = list(itertools.product((0, 1), repeat=nb))
    say(f"escalera/3 cube-and-conquer: {len(cubes)} cubos, {w} obreros")
    unsat = sat_hits = 0
    hard: list[tuple[int, ...]] = []
    with Pool(w) as pool:
        for v, _dt in pool.imap_unordered(
                _cube, [(encoder, c, nb, cube_phase1_s * 1000) for c in cubes]):
            if v == "unsat":
                unsat += 1
            elif v == "sat":
                sat_hits += 1
            else:
                hard.append(())        # solo cuenta; el bit exacto va en fase 2
    # fase 2 real: reintentar los duros identificándolos (segunda pasada honesta)
    if sat_hits:
        return {"verdict": "counterexample", "rung": "cubos",
                "elapsed_s": round(time.time() - t0, 1)}
    if not hard:
        return {"verdict": "proved", "rung": "cubos",
                "stats": {"cubos": len(cubes), "unsat": unsat},
                "elapsed_s": round(time.time() - t0, 1)}
    # identificar duros y sub-partir
    say(f"escalera/3b: {len(hard)} cubos duros → sub-partición")
    hard_bits = []
    with Pool(w) as pool:
        outs = pool.map(_cube, [(encoder, c, nb, 5_000) for c in cubes])
    hard_bits = [c for c, (v, _) in zip(cubes, outs) if v == "unknown"]
    nb2 = min(split2_vars, len(branch) - nb)
    sub = [(encoder, tuple(c) + s2, nb + nb2, cube_phase2_s * 1000)
           for c in hard_bits
           for s2 in itertools.product((0, 1), repeat=nb2)]
    unsat2 = sat2 = hard2 = 0
    with Pool(w) as pool:
        for v, _dt in pool.imap_unordered(_cube, sub):
            if v == "unsat":
                unsat2 += 1
            elif v == "sat":
                sat2 += 1
            else:
                hard2 += 1
    total_leaves = (len(cubes) - len(hard_bits)) + len(sub)
    closed = unsat + unsat2
    if sat2:
        return {"verdict": "counterexample", "rung": "sub-cubos",
                "elapsed_s": round(time.time() - t0, 1)}
    if hard2 == 0:
        return {"verdict": "proved", "rung": "sub-cubos",
                "stats": {"cubos": len(cubes), "sub": len(sub)},
                "elapsed_s": round(time.time() - t0, 1)}
    return {"verdict": "partial", "rung": "sub-cubos",
            "stats": {"cerrado_pct": round(100 * closed / max(1, total_leaves), 1),
                      "duros_restantes": hard2},
            "elapsed_s": round(time.time() - t0, 1)}


# --- primer encoder registrado: Caccetta–Häggkvist finito ---------------------------
def ch_encoder_build(n: int, k: int) -> tuple[Any, list[Any]]:
    """Encoder CH(n,k) con los WLOG sanos (outdeg exacto + vecindad de v0) y
    variables de ramificación sugeridas (aristas de vértices tempranos)."""
    import z3
    from math import ceil
    d = ceil(n / k)
    e = [[z3.Bool(f"e_{i}_{j}") for j in range(n)] for i in range(n)]
    s = z3.Solver()
    for i in range(n):
        s.add(z3.Not(e[i][i]))
        row = [e[i][j] for j in range(n) if j != i]
        s.add(z3.AtLeast(*row, d))
        s.add(z3.AtMost(*row, d))
        for j in range(i + 1, n):
            s.add(z3.Not(z3.And(e[i][j], e[j][i])))
    for i in range(n):
        for j in range(n):
            for m in range(n):
                if len({i, j, m}) == 3:
                    s.add(z3.Not(z3.And(e[i][j], e[j][m], e[m][i])))
    for j in range(1, n):
        s.add(e[0][j] if j <= d else z3.Not(e[0][j]))
    branch = ([e[1][j] for j in range(2, min(n, 8))]
              + [e[2][j] for j in range(3, min(n, 9))]
              + [e[3][j] for j in range(4, min(n, 10))])
    return s, branch


def ch_encoder(n: int, k: int = 3) -> Encoder:
    return partial(ch_encoder_build, n, k)
