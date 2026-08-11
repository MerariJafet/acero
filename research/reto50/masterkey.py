"""LLAVE MAESTRA ADAPTABLE — de predecir k_min a CONSTRUIR (k, d) certificado.

Reformulación de Merari (2026-08-11), aceptada tras análisis. El cambio central:

    NO necesitamos predecir k_min(p).  Necesitamos encontrar ALGÚN k válido.

Eso suena menor y es enorme. Guardar solo k_min tira casi toda la información
estructural: si A(p) = {13, 23, 47, 91, 307}, quedarnos con 13 borra la evidencia
de que 307 podría seguir una regla preciosa. Por eso aquí se registra la FILA
COMPLETA de incidencia puerta×llave, no el mínimo.

Y el objetivo deja de ser una regresión k ≈ a·log p + b (los 420 pares de
kmin_law.json muestran que la llave típica NO crece con p: media plana ~13 sobre
seis órdenes de magnitud). Si la dificultad no depende del TAMAÑO de p, depende
de su ESTRUCTURA ARITMÉTICA. La función a descubrir es:

    Φ(p) ──► (k, d)      con d el TESTIGO que hace girar la llave

AUTOCERTIFICACIÓN (la lección más cara del proyecto): toda regla debe entregar el
divisor testigo d y pasar el verificador mecánico. En las rondas 3-4 el sistema
sustituyó el criterio fuerte por una condición modular más floja y gastó una
ronda entera en el problema equivocado. Aquí una regla sin certificado NO existe.

HOLDOUT DESDE EL DÍA UNO (la otra lección cara): en la Ronda 1 una cobertura
"universal" murió con p=5003 porque había MEMORIZADO las clases residuales
vistas. Las reglas se buscan solo en train; el holdout no se toca hasta evaluar.

Niveles de éxito, declarados para no confundir descubrimiento con prueba:
  1. PREDICTOR    — acierta casi siempre. Útil, no demuestra nada.
  2. CONSTRUCTOR CERTIFICADO — entrega (k,d) verificado en cada caso probado.
  3. CONSTRUCTOR UNIVERSAL — reglas C_i con demostración de que ∨C_i cubre TODO
     primo duro. Honestidad: el nivel 3 es esencialmente tan difícil como el
     problema abierto; no lo prometemos, lo declaramos como techo.
"""
from __future__ import annotations

import json
import math
import os
import time
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "masterkey.json")
LOG = os.path.join(HERE, "masterkey.log")

HARD_RES = {1, 121, 169, 289, 361, 529}
KMAX = int(os.environ.get("MK_KMAX", "400"))
SAMPLES_PER_DECADE = int(os.environ.get("MK_SAMPLES", "80"))
DECADES = [10**m for m in range(5, 12)]
HOLDOUT_FRAC = 0.30          # se reserva y NO se mira durante la minería


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


_PARI = None


def factor(n: int) -> dict[int, int]:
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


# --- el criterio FUERTE, ahora devolviendo el TESTIGO ------------------------------
def opens_with_witness(p: int, k: int) -> tuple[bool, dict[str, Any] | None]:
    """¿k abre p? Y si abre, DEVUELVE EL TESTIGO: el divisor t de (p·x)² con
    t ≡ −px (mod k), reconstruido explícitamente. Sin testigo no hay apertura —
    esa es la diferencia entre este criterio y la versión debilitada que costó
    la Ronda 4."""
    if (p + k) % 4 != 0:
        return False, None
    x = (p + k) // 4
    target = (-(p % k) * (x % k)) % k
    fac: dict[int, int] = {}
    for q, e in factor(p).items():
        fac[q] = fac.get(q, 0) + 2 * e
    for q, e in factor(x).items():
        fac[q] = fac.get(q, 0) + 2 * e
    # BFS sobre el retículo de divisores guardando CÓMO se llegó a cada residuo
    # (el exponente de cada primo) → el testigo es reconstruible y verificable
    reached: dict[int, dict[int, int]] = {1 % k: {}}
    for q, e in sorted(fac.items()):
        g = q % k
        nxt = dict(reached)
        for r, expo in reached.items():
            v = r
            for j in range(1, e + 1):
                v = (v * g) % k
                if v not in nxt:
                    nxt[v] = {**expo, q: j}
        reached = nxt
        if target in reached:
            break
    if target not in reached:
        return False, None
    expo = reached[target]
    t = 1
    for q, j in expo.items():
        t *= q ** j
    # VERIFICACIÓN mecánica del testigo (no confiamos en la construcción)
    sq = (p * x) ** 2
    ok = (sq % t == 0) and ((t - (-(p * x))) % k == 0)
    return ok, {"t": t, "exponentes": {str(q): j for q, j in expo.items()},
                "x": x, "verificado": ok,
                "chequeo": "t | (p*x)^2 y t ≡ -p*x (mod k)"}


def keys_for(p: int, kmax: int = KMAX) -> list[int]:
    """A_K(p) COMPLETO — todas las llaves que abren, no solo la mínima.
    Guardar solo el mínimo tira la estructura que queremos descubrir."""
    out = []
    for k in range(3, kmax + 1, 2):
        if math.gcd(k, 840) != 1:
            continue
        ok, _ = opens_with_witness(p, k)
        if ok:
            out.append(k)
    return out


# --- Φ(p): la huella aritmética de la puerta ---------------------------------------
FINGERPRINT_MODULI = (23, 5, 7, 11, 13, 17, 19, 29, 31, 840, 4)


def fingerprint(p: int) -> dict[str, Any]:
    """Φ(p) — las propiedades de la puerta que podrían determinar sus dientes.
    Deliberadamente ARITMÉTICAS (no el tamaño): los 420 pares mostraron que el
    tamaño no explica la dificultad."""
    phi: dict[str, Any] = {f"p_mod_{m}": p % m for m in FINGERPRINT_MODULI}
    # residuosidad cuadrática frente a primos chicos (símbolo de Legendre)
    for q in (3, 5, 7, 11, 13):
        phi[f"qr_{q}"] = pow(p % q, (q - 1) // 2, q) if p % q else 0
    # estructura de p-1 y p+1: a menudo gobiernan la existencia de divisores
    f1, f2 = factor(p - 1), factor(p + 1)
    phi["omega_pm1"] = len(f1)
    phi["omega_pp1"] = len(f2)
    phi["v2_pm1"] = f1.get(2, 0)
    phi["small_div_pm1"] = int(all(q <= 100 for q in f1))
    phi["max_prime_pm1"] = max(f1) if f1 else 0
    phi["log_max_prime_pm1_over_log_p"] = round(
        math.log(max(f1)) / math.log(p), 4) if f1 else 0.0
    return phi


def build_dataset(samples: int = SAMPLES_PER_DECADE,
                  kmax: int = KMAX) -> list[dict[str, Any]]:
    """Filas COMPLETAS: puerta, todas sus llaves válidas, su huella, y el testigo
    de la primera llave (prueba de que la fila no es una afirmación vacía)."""
    from sympy import nextprime
    rows: list[dict[str, Any]] = []
    for dec in DECADES:
        p = dec - 1
        got = 0
        while got < samples:
            p = int(nextprime(p))
            if p % 840 not in HARD_RES:
                continue
            got += 1
            ks = keys_for(p, kmax)
            witness = None
            if ks:
                _, witness = opens_with_witness(p, ks[0])
            rows.append({
                "p": p, "decade": int(math.log10(dec)),
                "keys": ks, "n_keys": len(ks),
                "k_min": ks[0] if ks else None,
                "sin_llave_hasta_kmax": not ks,
                "witness_de_k_min": witness,
                "phi": fingerprint(p),
                "kmax": kmax,
                "criterio": "FUERTE con testigo verificado",
            })
        log(f"década 1e{int(math.log10(dec))}: {got} puertas, "
            f"llaves válidas por puerta (media) "
            f"{sum(len(r['keys']) for r in rows[-got:])/got:.1f}")
    return rows


# --- minería de REGLAS Φ(p) ⇒ k (no regresión: reglas) ----------------------------
def mine_rules(train: list[dict[str, Any]], *, min_support: int = 8,
               min_purity: float = 1.0) -> list[dict[str, Any]]:
    """Busca reglas 'si p tiene esta propiedad, ENTONCES la llave k la abre'.

    `min_purity=1.0` por defecto: solo reglas SIN excepción en train — porque el
    objetivo no es predecir bien en promedio, es CONSTRUIR una llave que
    funcione. Una regla con 99% de acierto no sirve para una construcción.

    Devuelve las reglas con su soporte y la deuda de búsqueda (cuántas se
    probaron), que es lo que permite juzgar si sobrevivir es mérito o azar."""
    if not train:
        return []
    feats = [f for f in train[0]["phi"] if isinstance(train[0]["phi"][f], int)]
    all_keys = sorted({k for r in train for k in r["keys"]})
    rules: list[dict[str, Any]] = []
    tested = 0
    for feat in feats:
        valores = {r["phi"][feat] for r in train}
        if len(valores) > 60:            # evitar features casi-únicos (memorizar)
            continue
        for val in sorted(valores):
            grupo = [r for r in train if r["phi"][feat] == val]
            if len(grupo) < min_support:
                continue
            for k in all_keys:
                tested += 1
                abre = sum(1 for r in grupo if k in r["keys"])
                purity = abre / len(grupo)
                if purity >= min_purity:
                    rules.append({
                        "condicion": f"{feat} == {val}", "feature": feat,
                        "valor": val, "k": k, "soporte": len(grupo),
                        "pureza_train": round(purity, 4),
                        "tipo": "constructiva: Φ(p) ⇒ k abre p"})
    rules.sort(key=lambda r: (-r["soporte"], r["k"]))
    for r in rules:
        r["deuda_busqueda"] = {"reglas_probadas": tested,
                               "nota": "una regla sin excepciones entre miles "
                                       "probadas puede serlo por azar: el "
                                       "holdout es el juez"}
    return rules


def baseline_control(train: list[dict[str, Any]],
                     holdout: list[dict[str, Any]]) -> dict[str, Any]:
    """LÍNEA BASE TRIVIAL: la llave más frecuente en train, aplicada a TODO.

    Sin esto una precisión del 88% no significa nada. Si una sola llave fija ya
    abre el 85% de las puertas, unas reglas que llegan al 88% no descubrieron
    estructura: descubrieron que casi cualquier llave chica sirve. Este control
    es el equivalente al nulo de Mendeleev, y por la misma razón: el sistema ya
    se engañó una vez comparando contra nada."""
    from collections import Counter
    cnt = Counter(k for r in train for k in r["keys"])
    if not cnt or not holdout:
        return {"disponible": False}
    tabla = []
    for k, c in cnt.most_common(5):
        tabla.append({"k": k, "frecuencia_train": round(c / len(train), 4),
                      "cobertura_holdout": round(
                          sum(1 for r in holdout if k in r["keys"]) / len(holdout), 4)}
                     )
    mejor = max(tabla, key=lambda t: t["cobertura_holdout"])
    return {"disponible": True, "top5": tabla, "mejor_llave_fija": mejor,
            "nota": "una regla solo aporta si SUPERA claramente a mejor_llave_fija"}


def keys_por_decada(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cuántas llaves abren cada puerta, por década.

    Importa para leer cualquier resultado: si |A(p)| crece con p, las reglas se
    ven mejor en primos grandes por una razón que NO es estructura — hay más
    llaves válidas y acertar es más fácil. Confundir eso con una ley sería
    repetir la Ronda 4 en versión estadística."""
    out = []
    for dec in sorted({r["decade"] for r in rows}):
        sub = [r for r in rows if r["decade"] == dec]
        kms = [r["k_min"] for r in sub if r["k_min"]]
        out.append({"decada": dec, "n": len(sub),
                    "n_keys_medio": round(sum(r["n_keys"] for r in sub) / len(sub), 2),
                    "k_min_medio": round(sum(kms) / len(kms), 2) if kms else None,
                    "sin_llave": sum(1 for r in sub if r["sin_llave_hasta_kmax"])})
    return out


def evaluate_on_holdout(rules: list[dict[str, Any]],
                        holdout: list[dict[str, Any]]) -> dict[str, Any]:
    """El juez REAL. Una regla que solo reproduce lo que vio no vale nada: la
    Ronda 1 ya mató así una cobertura 'universal' (p=5003, clase nueva)."""
    resultados = []
    cubiertas = 0
    for r in holdout:
        aplicables = [rl for rl in rules if r["phi"].get(rl["feature"]) == rl["valor"]]
        if not aplicables:
            resultados.append({"p": r["p"], "regla": None, "abre": None})
            continue
        rl = aplicables[0]
        abre, w = opens_with_witness(r["p"], rl["k"])   # CERTIFICADO, no promesa
        cubiertas += int(bool(abre))
        resultados.append({"p": r["p"], "regla": rl["condicion"], "k": rl["k"],
                           "abre": bool(abre),
                           "testigo": (w or {}).get("t")})
    con_regla = [x for x in resultados if x["regla"]]
    return {"holdout_n": len(holdout), "con_regla_aplicable": len(con_regla),
            "aciertos_certificados": cubiertas,
            "precision_certificada": (round(cubiertas / len(con_regla), 4)
                                      if con_regla else None),
            "cobertura": round(len(con_regla) / len(holdout), 4) if holdout else 0,
            "fallos": [x for x in con_regla if x["abre"] is False][:10],
            "nota": "precisión sobre casos donde ALGUNA regla aplica; la "
                    "cobertura dice cuántas puertas quedan sin construcción"}


def main() -> None:
    t0 = time.time()
    log(f"llave maestra: {SAMPLES_PER_DECADE} puertas/década, KMAX={KMAX}, "
        f"holdout={HOLDOUT_FRAC:.0%}")
    rows = []
    if os.environ.get("MK_REUSE") == "1" and os.path.exists(OUT):
        # reanalizar sin recomputar: el cómputo de A(p) es lo caro, la minería no
        rows = json.load(open(OUT, encoding="utf-8")).get("rows", [])
        log(f"REUTILIZANDO {len(rows)} puertas ya calculadas (solo re-análisis)")
    if not rows:
        rows = build_dataset()
    # split determinista por p (no aleatorio: reproducibilidad del ledger)
    holdout = [r for r in rows if r["p"] % 10 < int(HOLDOUT_FRAC * 10)]
    train = [r for r in rows if r not in holdout]
    log(f"train={len(train)} holdout={len(holdout)} (split por p mod 10, "
        "determinista y declarado)")
    rules = mine_rules(train)
    log(f"reglas sin excepción en train: {len(rules)}")
    ev = evaluate_on_holdout(rules, holdout)
    log(f"HOLDOUT: cobertura {ev['cobertura']:.1%} | precisión certificada "
        f"{ev['precision_certificada']} | fallos {len(ev['fallos'])}")
    base = baseline_control(train, holdout)
    if base.get("disponible"):
        mej = base["mejor_llave_fija"]
        log(f"CONTROL TRIVIAL: la llave fija k={mej['k']} sola cubre "
            f"{mej['cobertura_holdout']:.1%} del holdout — las reglas solo aportan "
            f"si superan eso")
    porde = keys_por_decada(rows)
    log("llaves válidas por puerta: " + " ".join(
        f"1e{d['decada']}={d['n_keys_medio']}" for d in porde))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "rules": rules[:200], "holdout_eval": ev,
                   "control_trivial": base, "por_decada": porde,
                   "niveles": {"1_predictor": "acierta, no demuestra",
                               "2_constructor_certificado": "entrega (k,d) verificado",
                               "3_universal": "requiere probar que las condiciones "
                                              "cubren TODO primo duro — tan difícil "
                                              "como el problema abierto"},
                   "nota": "MUESTRA estratificada, no exhaustivo"}, fh, indent=1)
    log(f"FIN masterkey: {len(rows)} puertas en {(time.time()-t0)/60:.1f} min")


if __name__ == "__main__":
    main()
