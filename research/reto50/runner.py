"""RETO 50 — el primer barrido autónomo de ACERO sobre 50 grandes problemas abiertos.

Corre SECUENCIALMENTE (para no saturar Codex): por cada problema crea el proyecto
(dedup por título), lanza el ciclo de Bohr y espera a que termine (o timeout).
Estado persistente en estado.jsonl — el cron de análisis lo lee cada 15 min.

Honestidad: el objetivo NO es 'resolver Riemann'; es mapear los 50 con el método
completo (novedad→ataque→segunda jugada→lema→crítica→informe) y encontrar variantes
donde un lema PARCIAL sí se pruebe — esos son los candidatos a paper.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8611/portal"
USER, PASS = "merari", "acero-local-2026"
HERE = Path(__file__).parent
ESTADO = HERE / "estado.jsonl"
TIMEOUT_MIN = 25          # máximo por problema antes de pasar al siguiente
POLL_S = 30

PROBLEMS: list[tuple[str, str]] = [
    ("R50-01 Collatz", "Para todo entero positivo n, la iteración de Collatz (n par -> n/2; n impar -> 3n+1) alcanza 1 en un número finito de pasos."),
    ("R50-02 Goldbach fuerte", "Todo número par mayor que 2 es suma de dos números primos."),
    ("R50-03 Primos gemelos", "Existen infinitos pares de primos p, p+2."),
    ("R50-04 Perfectos impares", "No existe ningún número perfecto impar."),
    ("R50-05 Cuboide perfecto", "No existe un cuboide perfecto: una caja con las tres aristas, las tres diagonales de cara y la diagonal espacial todas enteras."),
    ("R50-06 Erdos-Straus", "Para todo entero n>=2 existen enteros positivos x,y,z tales que 4/n = 1/x + 1/y + 1/z."),
    ("R50-07 Gamma irracional", "La constante de Euler-Mascheroni gamma es irracional."),
    ("R50-08 Pi normal", "Pi es un número normal en base 10: cada bloque de k dígitos aparece con frecuencia asintótica 10^-k."),
    ("R50-09 Brocard-Ramanujan", "Las únicas soluciones enteras positivas de n!+1=m^2 son n=4, 5 y 7."),
    ("R50-10 Erdos-Moser", "La única solución de 1^k+2^k+...+(m-1)^k = m^k con m>=2 es k=1, m=3."),
    ("R50-11 Legendre", "Para todo entero n>=1 existe un primo p con n^2 < p < (n+1)^2."),
    ("R50-12 Cramer", "Los huecos entre primos consecutivos cumplen p_{n+1}-p_n = O((log p_n)^2)."),
    ("R50-13 Lehmer totiente", "No existe número compuesto n tal que phi(n) divide a n-1."),
    ("R50-14 Beal", "Si A^x + B^y = C^z con enteros positivos y x,y,z > 2, entonces A, B y C comparten un factor primo."),
    ("R50-15 Fermat-Catalan", "Existen solo finitas soluciones coprimas de a^m + b^n = c^k con 1/m + 1/n + 1/k < 1."),
    ("R50-16 Hadamard matrices", "Para todo n múltiplo positivo de 4 existe una matriz de Hadamard n x n (entradas +-1 con filas ortogonales)."),
    ("R50-17 Corredor solitario", "Para k corredores con velocidades distintas en una pista circular unitaria, cada corredor está en algún instante a distancia >= 1/k de todos los demás."),
    ("R50-18 Frankl union-cerrada", "En toda familia finita de conjuntos cerrada por unión (distinta de la familia vacía), existe un elemento que pertenece a al menos la mitad de los conjuntos."),
    ("R50-19 Happy Ending exacto", "El mínimo número de puntos en posición general que garantiza n puntos en posición convexa es exactamente 2^(n-2)+1."),
    ("R50-20 Hadwiger-Nelson", "El número cromático del plano (prohibiendo distancia exactamente 1 en el mismo color) es exactamente 7."),
    ("R50-21 Reconstruccion grafos", "Todo grafo con al menos 3 vértices queda determinado salvo isomorfismo por su multiconjunto de subgrafos con un vértice borrado."),
    ("R50-22 Caccetta-Haggkvist", "Todo digrafo simple con n vértices y grado de salida mínimo al menos n/k contiene un ciclo dirigido de longitud a lo sumo k."),
    ("R50-23 Hadwiger grafos", "Todo grafo sin menor K_t es coloreable con t-1 colores."),
    ("R50-24 Erdos-Hajnal", "Para todo grafo H existe c>0 tal que todo grafo con n vértices sin copia inducida de H contiene una clique o un conjunto independiente de tamaño al menos n^c."),
    ("R50-25 Sidorenko", "Para todo grafo bipartito H y todo grafo G, la densidad de homomorfismos cumple t(H,G) >= t(K2,G)^{e(H)}."),
    ("R50-26 Falconer", "Todo conjunto en R^d con dimensión de Hausdorff mayor que d/2 determina un conjunto de distancias de medida de Lebesgue positiva."),
    ("R50-27 Kakeya d>=4", "Todo conjunto de Kakeya en R^d con d>=4 tiene dimensión de Hausdorff igual a d."),
    ("R50-28 Restriccion de Stein", "La conjetura de restricción de Fourier de Stein para la esfera en R^d: la desigualdad de restricción vale para todo q > 2d/(d-1)."),
    ("R50-29 Littlewood", "Para todos los reales alfa y beta: lim inf sobre n de n * ||n alfa|| * ||n beta|| = 0, donde ||.|| es la distancia al entero más cercano."),
    ("R50-30 Elliott-Halberstam", "Los primos tienen nivel de distribución 1: para todo theta<1 y todo A, la suma sobre q <= x^theta del error máximo en progresiones aritméticas es O(x/(log x)^A)."),
    ("R50-31 Chowla", "Para desplazamientos distintos h1<...<hk, la media de lambda(n+h1)*...*lambda(n+hk) tiende a 0, donde lambda es la función de Liouville."),
    ("R50-32 Sarnak-Mobius", "La función de Möbius es asintóticamente ortogonal a toda sucesión generada por un sistema dinámico determinista de entropía topológica cero."),
    ("R50-33 Lindelof", "Para todo epsilon>0, zeta(1/2+it) = O(t^epsilon) cuando t tiende a infinito."),
    ("R50-34 Cuatro exponenciales", "Si x1,x2 son linealmente independientes sobre Q y y1,y2 también, entonces al menos uno de e^{x_i y_j} (i,j en {1,2}) es trascendente."),
    ("R50-35 Schanuel", "Si z1,...,zn son linealmente independientes sobre Q, el grado de trascendencia de Q(z1,...,zn,e^{z1},...,e^{zn}) sobre Q es al menos n."),
    ("R50-36 Galois inverso", "Todo grupo finito aparece como grupo de Galois de alguna extensión finita de Q."),
    ("R50-37 Hilbert 10 sobre Q", "No existe algoritmo que decida si una ecuación polinómica con coeficientes racionales tiene solución racional."),
    ("R50-38 Jacobiano JC2", "Toda aplicación polinómica F de C^2 en C^2 con determinante jacobiano constante no nulo tiene inversa polinómica."),
    ("R50-39 Poincare suave 4D", "Toda 4-variedad suave homeomorfa a la esfera S^4 es difeomorfa a S^4."),
    ("R50-40 Andrews-Curtis", "Toda presentación balanceada del grupo trivial se transforma en la presentación trivial mediante movimientos de Andrews-Curtis."),
    ("R50-41 Hilbert-Smith", "Ningún grupo de enteros p-ádicos actúa fiel y continuamente sobre una variedad topológica conexa."),
    ("R50-42 Cannon", "Todo grupo hiperbólico cuya frontera de Gromov es la esfera S^2 actúa geométricamente sobre el espacio hiperbólico H^3."),
    ("R50-43 Tate", "Sobre un cuerpo finitamente generado, toda clase de Tate en cohomología l-ádica proviene de un ciclo algebraico."),
    ("R50-44 Bombieri-Lang", "En toda variedad proyectiva lisa de tipo general sobre Q, los puntos racionales no son densos de Zariski."),
    ("R50-45 Riemann", "Todos los ceros no triviales de la función zeta de Riemann tienen parte real exactamente 1/2."),
    ("R50-46 P vs NP", "P es distinto de NP: existe un problema verificable en tiempo polinómico que no es resoluble en tiempo polinómico."),
    ("R50-47 BSD", "Para toda curva elíptica sobre Q, el rango del grupo de puntos racionales es igual al orden de anulación de su función L en s=1."),
    ("R50-48 Hodge", "En toda variedad proyectiva compleja lisa, toda clase de Hodge racional es combinación lineal racional de clases de ciclos algebraicos."),
    ("R50-49 Navier-Stokes", "Toda solución de las ecuaciones de Navier-Stokes en 3D con dato inicial suave y de energía finita permanece suave para todo tiempo."),
    ("R50-50 Yang-Mills", "Existe una teoría cuántica de Yang-Mills sobre R^4 matemáticamente rigurosa cuyo espectro tiene un mass gap estrictamente positivo."),
]


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def estado(rec: dict) -> None:
    with ESTADO.open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> None:
    s = requests.Session()
    r = s.post(f"{BASE}/api/login", json={"username": USER, "password": PASS}, timeout=30)
    r.raise_for_status()
    csrf = r.json()["csrf"]
    hdr = {"x-csrf-token": csrf}
    log(f"login OK — arrancando {len(PROBLEMS)} problemas (secuencial)")
    estado({"event": "RUNNER_START", "total": len(PROBLEMS), "ts": time.time()})

    for i, (title, claim) in enumerate(PROBLEMS, 1):
        t0 = time.time()
        try:
            r = s.post(f"{BASE}/api/workspace/project", headers=hdr,
                       json={"title": title, "domain": "matemáticas", "topic": claim},
                       timeout=60)
            r.raise_for_status()
            pid = r.json()["id"]
            log(f"[{i}/50] {title} → proyecto {pid}"
                + (" (reusado)" if r.json().get("reused") else ""))
            # lanzar el ciclo (reintenta si el guard dice que hay otro vivo)
            for intento in range(20):
                rr = s.post(f"{BASE}/api/projects/{pid}/investigate", headers=hdr,
                            json={}, timeout=60)
                if rr.status_code == 409:
                    log(f"[{i}/50] guard 409 — espero 60s (intento {intento + 1})")
                    time.sleep(60)
                    continue
                rr.raise_for_status()
                break
            else:
                estado({"n": i, "title": title, "pid": pid, "status": "SKIP_GUARD",
                        "ts": time.time()})
                continue
            estado({"n": i, "title": title, "pid": pid, "status": "LAUNCHED",
                    "ts": time.time()})
            # esperar a que el ciclo cierre (o timeout) — el guard usa cstat.done
            disp = "TIMEOUT"
            deadline = time.time() + TIMEOUT_MIN * 60
            while time.time() < deadline:
                time.sleep(POLL_S)
                try:
                    c = s.get(f"{BASE}/api/projects/{pid}/council", timeout=30).json()
                    lv = c.get("live") or {}
                    if lv.get("done"):
                        disp = str(lv.get("disposition") or "done")
                        break
                except Exception as exc:  # noqa: BLE001
                    log(f"[{i}/50] poll error: {exc}")
            mins = round((time.time() - t0) / 60, 1)
            log(f"[{i}/50] {title} → {disp} en {mins} min")
            estado({"n": i, "title": title, "pid": pid, "status": "DONE",
                    "disposition": disp, "mins": mins, "ts": time.time()})
        except Exception as exc:  # noqa: BLE001 - un problema caído no detiene el reto
            log(f"[{i}/50] ERROR {title}: {exc}")
            estado({"n": i, "title": title, "status": "ERROR", "error": str(exc)[:200],
                    "ts": time.time()})
            time.sleep(30)
    estado({"event": "RUNNER_DONE", "ts": time.time()})
    log("RETO 50 COMPLETO — todos los problemas procesados")


if __name__ == "__main__":
    main()
