"""cover(N) con el criterio FUERTE del divisor — dataset para la llave dinámica.

Criterio (definición sellada, NUNCA debilitarla):
  k abre p  ⟺  p+k ≡ 0 (mod 4)  Y  ∃ t | (p·x)² con t ≡ −p·x (mod k), x=(p+k)/4.
La condición mod 4 sola es "la llave entra"; el divisor es "la llave GIRA".

Incremental por hitos (1,2,5 × 10^m hasta LIMIT): en cada hito se resuelve el
set-cover (greedy + EXACTO por branch&bound sobre firmas) y se anota una fila en
cover_growth.json — cada fila es un punto de la ley de crecimiento para Mendeleev.

Reanudable: el checkpoint guarda el último primo procesado y las firmas acumuladas.
Solo t coprimo con k importa (si p·x es coprimo con k, un t con gcd(t,k)>1 nunca
alcanza −px mod k), así que el DP corre en (Z/k)* con exponentes CAPADOS al orden
multiplicativo — y una caché por (k, patrón de factores mod k) lo vuelve barato.
"""
from __future__ import annotations

import json
import math
import os
import pickle
import sys
import time
from functools import lru_cache
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = os.path.join(HERE, "cover_growth.json")
LOG = os.path.join(HERE, "cover_growth.log")
CKPT = os.path.join(HERE, "cover_growth.ckpt")

LIMIT = int(float(os.environ.get("COVER_LIMIT", "1e9")))
KMAX = 240
HARD_RES = {1, 121, 169, 289, 361, 529}          # p mod 840 (residuos duros)
MILESTONES = sorted({int(a * 10 ** m) for m in range(5, 13) for a in (1, 2, 5)
                     if int(a * 10 ** m) <= LIMIT})
KEYS = [k for k in range(3, KMAX + 1, 2) if math.gcd(k, 840) == 1]
KIDX = {k: i for i, k in enumerate(KEYS)}
# REGLA DEL 90% (orden de Merari tras el reinicio del 10-ago): la v1 usaba
# cpu-4=28 workers, cada uno con una caché de hasta 2M de frozensets → la RAM
# se agotó y la PC SE APAGÓ, matando de paso las 5 semillas CH. Ahora: pocos
# workers por defecto, cachés acotadas, nice(10), y una PAUSA (cola, no
# competencia) cuando la memoria del sistema pasa del 90%.
WORKERS = int(os.environ.get("COVER_WORKERS")
              or max(2, min(10, (os.cpu_count() or 8) // 3)))
MEM_FRAC_MAX = float(os.environ.get("COVER_MEM_FRAC", "0.90"))


def _mem_used_frac() -> float:
    try:
        info: dict[str, int] = {}
        with open("/proc/meminfo", encoding="ascii") as fh:
            for line in fh:
                k, v = line.split(":", 1)
                info[k] = int(v.strip().split()[0])
        return 1.0 - info["MemAvailable"] / info["MemTotal"]
    except Exception:  # noqa: BLE001 - sin lectura ⇒ asumir presión (conservador)
        return 1.0


def _wait_headroom() -> None:
    """Si el SISTEMA (no solo este proceso) pasa del 90% de RAM, este trabajo se
    FORMA EN LA FILA: pausa y reintenta. Preferimos tardar más a tirar la PC."""
    while (frac := _mem_used_frac()) > MEM_FRAC_MAX:
        log(f"PAUSA por memoria: sistema al {frac:.0%} (>{MEM_FRAC_MAX:.0%}) — "
            "en fila, reintento en 60s")
        time.sleep(60)


def log(msg: str) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


# --- factorización (worker) --------------------------------------------------------
_PARI = None


def _factor(n: int) -> dict[int, int]:
    """PARI primero (7× más rápido que sympy a escala 1e11, equivalencia
    verificada sobre 300 muestras); sympy como respaldo si PARI no está."""
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


@lru_cache(maxsize=200_000)
def _mult_order(g: int, k: int) -> int:
    o, cur = 1, g % k
    while cur != 1:
        cur = (cur * g) % k
        o += 1
        if o > k:
            return k
    return o


@lru_cache(maxsize=120_000)      # 2M entradas × 28 workers fue lo que apagó la PC
def _reachable(k: int, gens: tuple[tuple[int, int], ...]) -> frozenset[int]:
    """Residuos alcanzables como productos prod g_i^{j_i} (0≤j_i≤e_i) mod k.
    gens ya viene con g coprimo a k y e capado al orden de g."""
    cur = {1}
    for g, e in gens:
        nxt = set()
        for r in cur:
            v = r
            nxt.add(v)
            for _ in range(e):
                v = (v * g) % k
                nxt.add(v)
        cur = nxt
        if len(cur) == k - 1:      # ya es todo (Z/k)* posible: nada más que añadir
            break
    return frozenset(cur)


def _opens(p: int, k: int) -> bool:
    """¿k abre p con el criterio FUERTE?"""
    if (p + k) % 4 != 0:
        return False
    x = (p + k) // 4
    target = (-(p % k) * (x % k)) % k
    if math.gcd(target, k) != 1:
        # px comparte factor con k: el DP coprimo no aplica; caso raro → fuerza
        # bruta acotada sobre divisores pequeños del cuadrado
        sq = p * x * p * x
        d, found = 1, False
        while d * d <= sq and d <= 10_000_000:
            if sq % d == 0 and ((d - (-p * x)) % k == 0
                                or ((sq // d) - (-p * x)) % k == 0):
                found = True
                break
            d += 1
        return found
    fac = _factor(x)
    gens: list[tuple[int, int]] = []
    exps: dict[int, int] = {}
    exps[p % k] = 2 if math.gcd(p % k, k) == 1 else 0
    for q, e in fac.items():
        g = q % k
        if math.gcd(g, k) != 1:
            continue                                  # rompe coprimalidad de t
        exps[g] = exps.get(g, 0) + 2 * e
    for g, e in sorted(exps.items()):
        if g == 1 or e == 0:
            continue
        gens.append((g, min(e, _mult_order(g, k) - 1)))
    return target in _reachable(k, tuple(sorted(gens)))


def _work(chunk: list[int]) -> list[tuple[int, int]]:
    """Por primo duro: bitmask de llaves que lo abren (criterio fuerte)."""
    out = []
    for p in chunk:
        mask = 0
        for k in KEYS:
            if _opens(p, k):
                mask |= 1 << KIDX[k]
        out.append((p, mask))
    return out


# --- primos duros por segmentos -----------------------------------------------------
def hard_primes(start: int, stop: int):
    import numpy as np
    seg = 10_000_000
    lo = max(3, start)
    base_n = int(stop ** 0.5) + 1
    sieve = np.ones(base_n + 1, dtype=bool)
    sieve[:2] = False
    for i in range(2, int(base_n ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = False
    base = np.nonzero(sieve)[0]
    while lo <= stop:
        hi = min(lo + seg - 1, stop)
        arr = np.ones(hi - lo + 1, dtype=bool)
        for q in base:
            q = int(q)
            if q * q > hi:
                break
            first = max(q * q, ((lo + q - 1) // q) * q)
            arr[first - lo::q] = False
        if lo <= 2:
            pass
        idx = np.nonzero(arr)[0] + lo
        for p in idx:
            p = int(p)
            if p % 840 in HARD_RES:
                yield p
        lo = hi + 1


# --- set cover ----------------------------------------------------------------------
def cover_sizes(signatures: dict[int, int]) -> tuple[int, int | None, list[int]]:
    """(greedy, exacto|None, llaves_exactas). Firmas: mask→conteo. Exacto por B&B
    sobre las firmas DISTINTAS (pocas) — imposible ⇒ (-1,None,[])."""
    sigs = [s for s in signatures if s]
    if any(s == 0 for s in signatures):
        return (-1, None, [])                          # hay puerta sin llave ≤ KMAX
    # greedy
    uncovered = set(range(len(sigs)))
    chosen: list[int] = []
    while uncovered:
        best_k, best_gain = -1, -1
        for ki in range(len(KEYS)):
            gain = sum(1 for i in uncovered if sigs[i] >> ki & 1)
            if gain > best_gain:
                best_k, best_gain = ki, gain
        if best_gain <= 0:
            return (-1, None, [])
        chosen.append(best_k)
        uncovered = {i for i in uncovered if not sigs[i] >> best_k & 1}
    greedy = len(chosen)
    # exacto: B&B con cota = greedy
    best = {"size": greedy, "keys": [KEYS[i] for i in chosen]}
    order = sorted(range(len(KEYS)),
                   key=lambda ki: -sum(1 for s in sigs if s >> ki & 1))

    def bb(idx: int, used: list[int], covered_mask_i: set[int]) -> None:
        if len(used) >= best["size"]:
            return
        if len(covered_mask_i) == len(sigs):
            best["size"], best["keys"] = len(used), [KEYS[i] for i in used]
            return
        if idx >= len(order):
            return
        remaining = len(sigs) - len(covered_mask_i)
        # cota optimista: la mejor llave restante cubre a lo más max_gain firmas
        max_gain = max((sum(1 for i in range(len(sigs))
                            if i not in covered_mask_i and sigs[i] >> ki & 1)
                        for ki in order[idx:]), default=0)
        if max_gain == 0 or len(used) + math.ceil(remaining / max_gain) >= best["size"]:
            return
        ki = order[idx]
        gain = {i for i in range(len(sigs))
                if i not in covered_mask_i and sigs[i] >> ki & 1}
        if gain:
            bb(idx + 1, used + [ki], covered_mask_i | gain)
        bb(idx + 1, used, covered_mask_i)

    if len(sigs) <= 4000:                              # B&B solo si es tratable
        bb(0, [], set())
        return (greedy, best["size"], sorted(best["keys"]))
    return (greedy, None, [])


# --- main ---------------------------------------------------------------------------
def main() -> None:
    t0 = time.time()
    signatures: dict[int, int] = {}
    n_hard, last_p = 0, 2
    rows: list[dict] = []
    if os.path.exists(CKPT):
        with open(CKPT, "rb") as fh:
            st = pickle.load(fh)
        signatures, n_hard, last_p, rows = (st["sig"], st["n"], st["p"], st["rows"])
        log(f"REANUDANDO desde p={last_p} (n_hard={n_hard})")
    log(f"cover_growth: LIMIT={LIMIT:.0e} KMAX={KMAX} llaves={len(KEYS)} "
        f"workers={WORKERS} hitos={MILESTONES}")
    pending = [m for m in MILESTONES if m > last_p]
    pool = Pool(WORKERS, initializer=lambda: os.nice(10))
    try:
        for milestone in pending:
            buf: list[int] = []
            CH = 2000
            jobs = []
            for p in hard_primes(last_p + 1, milestone):
                buf.append(p)
                if len(buf) >= CH:
                    _wait_headroom()          # regla del 90%: fila, no competencia
                    jobs.append(pool.apply_async(_work, (buf,)))
                    buf = []
                if len(jobs) >= WORKERS * 3:
                    for j in jobs:
                        for p2, mask in j.get():
                            signatures[mask] = signatures.get(mask, 0) + 1
                            n_hard += 1
                    jobs = []
            if buf:
                jobs.append(pool.apply_async(_work, (buf,)))
            for j in jobs:
                for p2, mask in j.get():
                    signatures[mask] = signatures.get(mask, 0) + 1
                    n_hard += 1
            last_p = milestone
            greedy, exact, keys = cover_sizes(signatures)
            row = {"N": milestone, "n_hard": n_hard,
                   "n_signatures": len(signatures),
                   "cover_greedy": greedy, "cover_exact": exact,
                   "keys_exact": keys, "kmax": KMAX,
                   "criterio": "divisor t|(px)^2, t=-px mod k (FUERTE)",
                   "elapsed_s": round(time.time() - t0, 1)}
            rows.append(row)
            with open(OUT_JSON, "w", encoding="utf-8") as fh:
                json.dump({"rows": rows}, fh, indent=1)
            with open(CKPT, "wb") as fh:
                pickle.dump({"sig": signatures, "n": n_hard, "p": last_p,
                             "rows": rows}, fh)
            log(f"HITO N={milestone:.0e}: n_hard={n_hard} "
                f"cover_greedy={greedy} cover_exact={exact} keys={keys}")
        log(f"FIN cover_growth hasta {LIMIT:.0e} en "
            f"{(time.time() - t0) / 3600:.1f} h")
    finally:
        pool.close()
        pool.join()


if __name__ == "__main__":
    sys.setrecursionlimit(100_000)
    main()
