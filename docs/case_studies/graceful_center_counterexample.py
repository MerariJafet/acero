"""Contraejemplo (verificable) a la variante fuerte de graceful labeling con centro.
AFIRMACIÓN (refutada): para todo árbol T (3<=n<=11) existe un etiquetado graceful
en el que algún vértice CENTRO de T recibe una etiqueta en {0, n-1}.
Este árbol de n=6 la refuta: es graceful, pero ningún etiquetado graceful pone su
centro (vértice 1) en 0 o 5. Corre este archivo para verificarlo."""
from itertools import permutations
EDGES = [(0,1),(0,2),(0,3),(1,4),(4,5)]; N = 6; CENTERS = [1]
def is_graceful(lbl):
    ev=set()
    for u,v in EDGES:
        d=abs(lbl[u]-lbl[v])
        if d in ev: return False
        ev.add(d)
    return ev=={1,2,3,4,5}
gr=[p for p in permutations(range(N)) if is_graceful(p)]
center_ok=[p for p in gr if any(p[c] in (0,N-1) for c in CENTERS)]
ok = len(gr)>0 and len(center_ok)==0
print(f"etiquetados graceful: {len(gr)}; con centro en {{0,{N-1}}}: {len(center_ok)}")
print("RESULT_JSON:", {"claim_refuted": True, "n": N, "edges": EDGES,
      "centers": CENTERS, "graceful_labelings": len(gr),
      "with_center_extreme": len(center_ok), "confirmed": ok})
assert ok, "no es contraejemplo"
print("CONTRAEJEMPLO CONFIRMADO")
