"""Lanza un ciclo del Consejo con el LEMA acotado de Caccetta-Haggkvist (k=3).

Uso: python launch_ch_council.py <N_MAX_PROBADO>
La novedad la dictamina Hipatia sobre el LEMA (no sobre la conjetura madre),
exactamente como pide el plan del RETO 50.
"""
import sys
import time

import requests

BASE = "http://127.0.0.1:8611/portal"
USER, PASS = "merari", "acero-local-2026"


def main() -> None:
    nmax = int(sys.argv[1])
    claim = (
        f"Para todo n <= {nmax}, todo digrafo simple sin lazos con n vertices y "
        "grado minimo de salida >= n/3 contiene un ciclo dirigido de longitud <= 3 "
        "(caso finito de Caccetta-Haggkvist k=3; los casos n multiplo de 3 NO estan "
        "implicados por el teorema de densidad de Hladky-Kral-Norin 0.3465n)"
    )
    s = requests.Session()
    r = s.post(f"{BASE}/api/login", json={"username": USER, "password": PASS},
               timeout=30)
    r.raise_for_status()
    hdr = {"x-csrf-token": r.json()["csrf"]}
    pr = s.post(f"{BASE}/api/workspace/project", headers=hdr, timeout=60,
                json={"title": f"Lema CH k=3 acotado (n<={nmax})",
                      "domain": "matemáticas", "topic": claim})
    pr.raise_for_status()
    pid = pr.json()["id"]
    print("proyecto:", pid, "(reused)" if pr.json().get("reused") else "(nuevo)")
    iv = s.post(f"{BASE}/api/projects/{pid}/investigate", headers=hdr,
                json={"claim": claim}, timeout=60)
    print("investigate:", iv.status_code, iv.text[:200])
    if iv.status_code == 409:
        return
    # seguir el ciclo hasta que termine (max 20 min)
    t0 = time.time()
    while time.time() - t0 < 1200:
        time.sleep(20)
        c = s.get(f"{BASE}/api/projects/{pid}/council", timeout=30).json()
        live = c.get("live") or {}
        if live.get("done"):
            print("CICLO TERMINADO —", live.get("label", ""))
            break
        print(f"  [{round(time.time()-t0)}s] etapa: {live.get('label', '?')}",
              flush=True)
    for it in c.get("items", []):
        if it.get("kind") in ("literature", "candidate", "decision"):
            p = it.get("payload", {})
            nov = p.get("novelty") or p.get("novelty_verdict")
            if nov:
                print("NOVEDAD (Hipatia):", nov)
    print("proyecto para revisar en el portal:", pid)


if __name__ == "__main__":
    main()
