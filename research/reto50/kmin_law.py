"""k_min(p) — el dataset de la LLAVE DINÁMICA (el porqué sellado).

Hasta ahora medíamos el MEDIO: cuántas llaves hacen falta para abrir todas las
puertas hasta N (cover). El hallazgo de 10¹¹ cambió la pregunta: existe una
puerta (p=75,119,463,721) que NINGUNA llave k≤240 abre — necesita k=307. Es
decir, el llavero acotado no es el objeto correcto; el objeto correcto es la
FUNCIÓN k_min(p): el tamaño de llave que cada puerta exige.

Eso es literalmente el PORQUÉ sellado (prem_B7JTWQPT_1): "construir una llave
DINÁMICA k(p) cuya fórmula incorpore el crecimiento, explicando la razón".

Definición SELLADA, sin debilitar:
    k abre p  ⟺  p+k ≡ 0 (mod 4)  Y  ∃ t | (p·x)² con t ≡ −p·x (mod k),
    donde x=(p+k)/4.  (mod 4 solo es buena formación, NO abrir.)
    k_min(p) = la menor k impar, gcd(k,840)=1, que abre p.

Muestreo ESTRATIFICADO y declarado: `SAMPLES_PER_DECADE` puertas por década,
tomadas de forma determinista (las primeras de cada banda). No es exhaustivo —
es una muestra, y así se declara en la salida: cualquier ley que salga de aquí
es sobre la muestra, no sobre todos los primos.

Salida: kmin_law.json con filas {p, k_min, decade, p_mod_840, log_p, ...} listas
para Mendeleev (simbólico + secuencias + invariantes, con su filtro de
trivialidad y su nulo family-wise).
"""
from __future__ import annotations

import json
import math
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "kmin_law.json")
LOG = os.path.join(HERE, "kmin_law.log")

HARD_RES = {1, 121, 169, 289, 361, 529}
SAMPLES_PER_DECADE = int(os.environ.get("KMIN_SAMPLES", "60"))
KMAX = int(os.environ.get("KMIN_KMAX", "2000"))     # techo alto: queremos VER k grande
DECADES = [10**m for m in range(5, 12)]              # 1e5 … 1e11
MEM_SOFT, MEM_HARD = 0.80, 0.88


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _mem_frac() -> float:
    try:
        info = {}
        with open("/proc/meminfo", encoding="ascii") as fh:
            for ln in fh:
                k, v = ln.split(":", 1)
                info[k] = int(v.strip().split()[0])
        return 1.0 - info["MemAvailable"] / info["MemTotal"]
    except Exception:  # noqa: BLE001
        return 1.0


def wait_headroom() -> None:
    """Regla del 90% (dos niveles) — igual que cover_growth."""
    frac = _mem_frac()
    if frac <= MEM_SOFT:
        return
    objetivo = MEM_SOFT if frac > MEM_HARD else MEM_HARD
    log(f"PAUSA por memoria: {frac:.0%} — en fila hasta bajar de {objetivo:.0%}")
    while _mem_frac() > objetivo:
        time.sleep(30)


_PARI = None


def factor(n: int) -> dict[int, int]:
    """PARI (7× sympy, benchmark en TOOLBOX/cypari2); sympy de respaldo."""
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


def opens(p: int, k: int) -> bool:
    """El criterio FUERTE, sin atajos: ¿existe divisor t de (px)² con t≡−px mod k?"""
    if (p + k) % 4 != 0:
        return False
    x = (p + k) // 4
    target = (-(p % k) * (x % k)) % k
    fac: dict[int, int] = {}
    for q, e in factor(p).items():
        fac[q] = fac.get(q, 0) + 2 * e
    for q, e in factor(x).items():
        fac[q] = fac.get(q, 0) + 2 * e
    res = {1 % k}
    for q, e in fac.items():
        g = q % k
        nxt = set(res)
        for r in res:
            v = r
            for _ in range(e):
                v = (v * g) % k
                nxt.add(v)
        res = nxt
        if target in res:
            return True
    return target in res


def k_min(p: int) -> int | None:
    """La menor llave admisible que abre p. None si ninguna ≤ KMAX (se declara)."""
    for k in range(3, KMAX + 1, 2):
        if math.gcd(k, 840) != 1:
            continue
        if opens(p, k):
            return k
    return None


def hard_primes_from(start: int, want: int):
    """Puertas duras a partir de `start`, en orden. Determinista."""
    from sympy import nextprime
    p = int(start) - 1
    got = 0
    while got < want:
        p = int(nextprime(p))
        if p % 840 in HARD_RES:
            got += 1
            yield p


def main() -> None:
    t0 = time.time()
    rows: list[dict] = []
    if os.path.exists(OUT):
        try:
            rows = json.load(open(OUT, encoding="utf-8")).get("rows", [])
            log(f"REANUDANDO con {len(rows)} filas ya calculadas")
        except Exception:  # noqa: BLE001
            rows = []
    done = {r["p"] for r in rows}
    log(f"k_min: {SAMPLES_PER_DECADE} puertas/década, décadas {DECADES}, "
        f"KMAX={KMAX}")
    for dec in DECADES:
        n_dec = 0
        for p in hard_primes_from(dec, SAMPLES_PER_DECADE):
            if p in done:
                n_dec += 1
                continue
            wait_headroom()
            km = k_min(p)
            rows.append({"p": p, "k_min": km, "decade": int(math.log10(dec)),
                         "p_mod_840": p % 840, "log_p": round(math.log(p), 6),
                         "loglog_p": round(math.log(math.log(p)), 6),
                         "k_over_logp": (round(km / math.log(p), 6)
                                         if km else None),
                         "k_over_logp2": (round(km / math.log(p) ** 2, 6)
                                          if km else None),
                         "criterio": "FUERTE: t|(px)^2, t=-px mod k",
                         "kmax_declarado": KMAX})
            n_dec += 1
            if n_dec % 10 == 0:
                with open(OUT, "w", encoding="utf-8") as fh:
                    json.dump({"rows": rows, "muestreo": "estratificado por década "
                               f"({SAMPLES_PER_DECADE} primeras puertas de cada una)",
                               "kmax": KMAX,
                               "nota": "MUESTRA, no exhaustivo: toda ley derivada "
                                       "de aquí es sobre la muestra"}, fh, indent=1)
        ks = [r["k_min"] for r in rows if r["decade"] == int(math.log10(dec))
              and r["k_min"]]
        if ks:
            log(f"década 1e{int(math.log10(dec))}: n={len(ks)} "
                f"k_min medio={sum(ks)/len(ks):.1f} máx={max(ks)} min={min(ks)}")
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "muestreo": "estratificado por década",
                   "kmax": KMAX,
                   "nota": "MUESTRA, no exhaustivo"}, fh, indent=1)
    log(f"FIN kmin_law: {len(rows)} pares (p, k_min) en "
        f"{(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
