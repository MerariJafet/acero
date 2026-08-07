"""MethodCatalog — la caja de "piezas de LEGO" matemáticas que ACERO POSEE.

Antes, el Explorador elegía métodos desde el conocimiento paramétrico del LLM (su
"tabla de pesos"): opaco, no auditable, no acumulable. Esto lo cambia: ACERO mantiene
un CATÁLOGO curado de técnicas — cada una con para-qué-sirve, cómo-funciona, un idiom
de código real (numpy/sympy/scipy) y señales de cuándo aplicarla.

El programa (no el LLM) hace la RECUPERACIÓN: dado un objetivo, puntúa y elige las
piezas relevantes por tags/keywords. Al LLM se le entrega esa caja concreta y su tarea
pasa de "recordá un método" a "ensamblá una solución con ESTAS piezas". Registramos qué
piezas usó → procedencia auditable. Y `learn()` deja AGREGAR piezas nuevas cuando el
sistema descubre un camino → el PROGRAMA acumula capacidad, no los pesos del modelo.

Diseño deliberado:
  * las piezas son datos (dataclasses + JSON persistente), versionables y auditables;
  * la recuperación es determinista (lógica del programa), no otra llamada al LLM;
  * incluye piezas que van MÁS ALLÁ de la recall típica, p.ej. reconocer que 1.6449…
    ES π²/6 (`sympy.nsimplify`) o acelerar series lentas (Richardson) — herramientas
    que un chat plano no invoca solo.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

_WORD = re.compile(r"[a-záéíóúñ0-9]+")


@dataclass(frozen=True)
class Technique:
    id: str
    name: str
    tags: tuple[str, ...]        # numerico algebra calculo series combinatoria geometria algebra_lineal recurrencia
    purpose: str                 # para qué sirve
    how: str                     # cómo funciona (una línea)
    idiom: str                   # snippet idiomático con la librería
    when: str = ""               # señales de cuándo aplicarla

    def brief(self) -> str:
        """Ficha compacta para inyectar al prompt como pieza disponible."""
        return (f"[{self.id}] {self.name} ({'/'.join(self.tags)})\n"
                f"    sirve para: {self.purpose}\n"
                f"    cómo: {self.how}\n"
                f"    idiom: {self.idiom}")


# --- catálogo semilla: piezas curadas, cubriendo el espacio de métodos ----------
_SEED: list[Technique] = [
    Technique("montecarlo_area", "Estimación Monte Carlo",
              ("numerico", "geometria", "calculo"),
              "estimar áreas/volúmenes/integrales muestreando puntos al azar",
              "cuenta la fracción de muestras que caen dentro de la región × área del marco",
              "rng=np.random.default_rng(0); pts=rng.random((N,2)); frac=inside(pts).mean()",
              "hay una región o integral difícil de cerrar analíticamente"),
    Technique("riemann_sum", "Suma de Riemann / cuadratura",
              ("numerico", "calculo"),
              "aproximar una integral definida por rectángulos/trapecios o cuadratura",
              "divide el dominio en n trozos y suma f(x_i)·Δx; o usa cuadratura adaptativa",
              "from scipy.integrate import quad; val,err=quad(f, a, b)",
              "se busca el valor de una integral definida"),
    Technique("sym_sum", "Sumatoria simbólica",
              ("algebra", "series", "combinatoria"),
              "obtener la forma cerrada exacta de una suma Σ f(k)",
              "sympy evalúa la suma simbólicamente en función del límite superior",
              "import sympy as sp; k,n=sp.symbols('k n'); sp.summation(k,(k,1,n))",
              "hay una suma con límite superior variable n"),
    Technique("sym_integrate", "Integración simbólica",
              ("calculo", "algebra"),
              "obtener la antiderivada o integral definida exacta",
              "sympy integra simbólicamente; usa (x,a,b) para definida",
              "sp.integrate(sp.exp(-x**2),(x,-sp.oo,sp.oo))",
              "se busca el valor exacto de una integral"),
    Technique("telescoping", "Telescopaje",
              ("algebra", "series"),
              "cerrar sumas donde términos consecutivos se cancelan",
              "escribe f(k)=g(k)-g(k+1); la suma colapsa a g(inicio)-g(fin)",
              "# 1/(k(k+1)) = 1/k - 1/(k+1)  → suma = 1 - 1/(n+1)",
              "el término se factoriza como diferencia de una misma función desplazada"),
    Technique("finite_diff_fit", "Diferencias finitas + ajuste polinómico",
              ("numerico", "algebra", "combinatoria"),
              "adivinar una forma cerrada polinómica a partir de valores",
              "si las d-ésimas diferencias son constantes, es un polinomio de grado d; ajústalo",
              "import numpy as np; c=np.polyfit(ns, vals, deg); # o sp.interpolate",
              "una sucesión parece polinómica en n"),
    Technique("generating_function", "Función generatriz",
              ("series", "combinatoria", "algebra"),
              "codificar una sucesión como coeficientes de una serie de potencias",
              "manipula Σ a_n x^n como función cerrada y extrae coeficientes",
              "sp.series(1/(1-x-x**2), x, 0, 10)  # Fibonacci",
              "una recurrencia o conteo combinatorio"),
    Technique("char_equation", "Ecuación característica de recurrencia",
              ("recurrencia", "algebra"),
              "resolver recurrencias lineales en forma cerrada",
              "sustituye a_n=r^n, resuelve el polinomio, combina las raíces",
              "sp.rsolve(f(n+2)-f(n+1)-f(n), f(n))  # Binet",
              "hay una recurrencia lineal con coeficientes constantes"),
    Technique("sym_limit", "Límite simbólico",
              ("calculo", "series"),
              "evaluar límites, incluidos los que definen constantes",
              "sympy calcula el límite exacto, incluso hacia el infinito",
              "sp.limit(harmonic(n)-sp.log(n), n, sp.oo)  # gamma de Euler",
              "una constante se define como límite de una sucesión"),
    Technique("taylor_series", "Serie de Taylor/Maclaurin",
              ("calculo", "series"),
              "expandir una función en potencias para analizar o sumar",
              "sympy da el desarrollo en serie alrededor de un punto",
              "sp.series(sp.atan(x), x, 0, 12)  # Leibniz para pi/4",
              "una serie conocida evalúa a la cantidad buscada"),
    Technique("nsimplify_identify", "Reconocimiento de constante (nsimplify/identify)",
              ("numerico", "series"),
              "reconocer qué constante cerrada es un número decimal (¡clave!)",
              "dado un valor numérico, busca una expresión cerrada con π, e, √, ζ…",
              "sp.nsimplify(1.6449340668, [sp.pi])  # -> pi**2/6",
              "un método numérico dio un decimal y quieres su forma exacta"),
    Technique("series_accel", "Aceleración de series (Richardson/Euler)",
              ("numerico", "series"),
              "converger series/productos lentos con pocos términos",
              "extrapola la cola de sumas parciales para acelerar la convergencia",
              "from mpmath import nsum, richardson; nsum(lambda k: 1/k**2, [1, mpmath.inf])",
              "una serie/producto converge muy lento (Wallis, Leibniz, Euler-Mascheroni)"),
    Technique("high_precision", "Alta precisión (mpmath)",
              ("numerico",),
              "calcular con cientos de dígitos para distinguir constantes cercanas",
              "usa mpmath.mp.dps para fijar la precisión y evaluar",
              "import mpmath; mpmath.mp.dps=50; mpmath.mpf(1)/7",
              "hay que decidir entre valores muy próximos o alimentar identify()"),
    Technique("linear_algebra", "Álgebra lineal / autovalores",
              ("algebra_lineal", "numerico"),
              "diagonalizar, autovalores, resolver sistemas, determinantes",
              "numpy/sympy para eig, det, solve; potencias de matriz cerradas",
              "np.linalg.eig(A); sp.Matrix(A).det()",
              "el problema es matricial o una recurrencia como potencia de matriz"),
    Technique("vandermonde_det", "Determinante estructurado (Vandermonde)",
              ("algebra_lineal", "algebra", "combinatoria"),
              "cerrar determinantes con estructura conocida",
              "det de Vandermonde = Π_{i<j}(x_j - x_i); verifícalo simbólicamente",
              "sp.Matrix(n,n, lambda i,j: x[j]**i).det()",
              "aparece un determinante con patrón (Vandermonde, Cauchy, circulante)"),
    Technique("sym_solve", "Resolución simbólica de ecuaciones",
              ("algebra",),
              "despejar incógnitas o encontrar condiciones",
              "sympy resuelve ecuaciones y sistemas exactamente",
              "sp.solve(sp.Eq(a**2+b**2, c**2), c)",
              "hay que despejar una relación entre variables"),
    Technique("binomial_id", "Identidades binomiales/factoriales",
              ("combinatoria", "algebra"),
              "sumas y conteos con coeficientes binomiales",
              "usa C(n,k), factoriales, y sus identidades (Vandermonde, hockey-stick)",
              "sp.binomial(n,k); sp.summation(sp.binomial(n,k),(k,0,n))  # 2**n",
              "el problema cuenta subconjuntos, caminos o combinaciones"),
    Technique("asymptotic", "Expansión asintótica",
              ("calculo", "series", "numerico"),
              "aproximar el comportamiento para n grande (p.ej. Stirling)",
              "desarrolla en serie alrededor de infinito y compara razones",
              "sp.series(sp.gamma(n+1)/(sp.sqrt(2*sp.pi*n)*(n/sp.E)**n), n, sp.oo, 2)",
              "se busca una aproximación cuando n→∞ (factoriales, sumas grandes)"),
    Technique("induction_check", "Verificación por inducción (paso + base)",
              ("algebra", "combinatoria"),
              "confirmar una fórmula cerrada probando base y paso inductivo",
              "verifica P(0) y simplifica P(n+1)-P(n) al término añadido",
              "sp.simplify(F.subs(n,n+1)-F - term)  # == 0 ?",
              "ya tienes una fórmula candidata y quieres soportarla formalmente"),
    Technique("dimensional", "Análisis dimensional / escalado",
              ("geometria", "numerico"),
              "restringir la forma de una fórmula por cómo escala con sus variables",
              "mira cómo cambia el resultado al escalar cada variable de entrada",
              "# duplicar r ⇒ área ×4 ⇒ área ∝ r^2",
              "hay magnitudes con unidades o simetrías de escala"),
    Technique("graph_enum", "Grafos: enumeración y invariantes (networkx)",
              ("grafos", "combinatoria", "numerico"),
              "explorar/enumerar grafos pequeños y calcular invariantes (dominación, "
              "matching, cromático, conectividad, ciclos)",
              "genera todos los grafos/árboles pequeños y evalúa la propiedad; busca "
              "contraejemplos por fuerza bruta estructurada",
              "import networkx as nx; [T for T in nx.nonisomorphic_trees(8)]; "
              "nx.domination.dominating_set(G); nx.max_weight_matching(G)",
              "la conjetura es sobre grafos, árboles, redes, matchings o dominación"),
    Technique("number_theory", "Teoría de números (sympy.ntheory)",
              ("numeros", "algebra", "combinatoria"),
              "primos, factorización, divisores, congruencias, funciones aritméticas",
              "usa sympy.ntheory: isprime, factorint, divisors, totient, mobius, jacobi",
              "from sympy import factorint, totient, divisors, isprime, primerange",
              "aparecen primos, divisibilidad, residuos o funciones aritméticas"),
    Technique("smt_logic", "Prueba lógica / SMT (Z3 = Gödel)",
              ("logica", "combinatoria", "numeros"),
              "DEMOSTRAR o refutar afirmaciones lógicas/cuantificadas sobre enteros/"
              "booleanos, y argumentos de conteo/casillas (donde sympy no llega)",
              "declara variables z3.Int/Bool, añade hipótesis, y comprueba UNSAT de la "
              "negación para probar ∀; SAT da contraejemplo/testigo",
              "import z3; s=z3.Solver(); n=z3.Int('n'); s.add(z3.Not(n*n>=0)); s.check()",
              "hay un ∀/∃ sobre enteros o booleanos, restricciones lógicas o conteo exacto"),
    Technique("combinatorial_enum", "Enumeración combinatoria (itertools/sympy)",
              ("combinatoria",),
              "recorrer permutaciones, subconjuntos, particiones, palabras y contar/verificar",
              "itertools.permutations/combinations/product; sympy.utilities.iterables",
              "from itertools import permutations, combinations, product; "
              "from sympy.utilities.iterables import partitions, multiset_permutations",
              "el objeto es una permutación, subconjunto, partición o palabra"),
    Technique("optimization", "Optimización (scipy.optimize / linprog)",
              ("numerico", "algebra_lineal"),
              "hallar máximos/mínimos, resolver programas lineales, ajustar parámetros",
              "scipy.optimize: minimize, linprog, curve_fit, root; para cotas extremales",
              "from scipy.optimize import linprog, minimize; linprog(c, A_ub=A, b_ub=b)",
              "buscas el caso extremo, una cota óptima o el mejor ajuste"),
    Technique("statistics", "Estadística e inferencia (scipy.stats)",
              ("numerico", "datos"),
              "distribuciones, pruebas de hipótesis, correlación, remuestreo",
              "scipy.stats: distribuciones, ttest, pearsonr, bootstrap; numpy para datos",
              "from scipy import stats; stats.pearsonr(x, y); stats.bootstrap(...)",
              "la afirmación involucra datos, aleatoriedad o significancia estadística"),
]


class MethodCatalog:
    """Caja de piezas LEGO del programa, con recuperación determinista y aprendizaje."""

    def __init__(self, techniques: list[Technique] | None = None,
                 store: Path | None = None) -> None:
        self._store = store
        base = list(techniques if techniques is not None else _SEED)
        base.extend(self._load_learned())
        # de-dup by id, last wins
        self._by_id: dict[str, Technique] = {t.id: t for t in base}

    @classmethod
    def default(cls) -> MethodCatalog:
        return cls(store=_default_store())

    # --- retrieval: THE PROGRAM picks the pieces (no LLM call) -----------------
    def retrieve(self, goal: str, k: int = 8) -> list[Technique]:
        toks = set(_WORD.findall(goal.lower()))
        scored: list[tuple[float, Technique]] = []
        for t in self._by_id.values():
            hay = f"{t.name} {t.purpose} {t.how} {t.when} {' '.join(t.tags)}".lower()
            htoks = set(_WORD.findall(hay))
            overlap = len(toks & htoks)
            # small boost for tag hits and for pieces flagged for numeric constants
            tagboost = sum(1 for tag in t.tags if tag in toks)
            score = overlap + 0.5 * tagboost
            scored.append((score, t))
        scored.sort(key=lambda x: (-x[0], x[1].id))
        top = [t for s, t in scored if s > 0][:k]
        # always keep a diverse floor even if keyword overlap is thin
        if len(top) < min(k, 6):
            for _s, t in scored:
                if t not in top:
                    top.append(t)
                if len(top) >= min(k, 6):
                    break
        return top

    def toolbox_text(self, goal: str, k: int = 8) -> str:
        pieces = self.retrieve(goal, k)
        return "\n".join(p.brief() for p in pieces)

    def ids(self) -> list[str]:
        return sorted(self._by_id)

    def get(self, tid: str) -> Technique | None:
        return self._by_id.get(tid)

    # --- learning: the PROGRAM accumulates capability --------------------------
    def learn(self, tech: Technique) -> None:
        self._by_id[tech.id] = tech
        self._persist_learned(tech)

    def _default_learned_path(self) -> Path | None:
        return (self._store / "learned.json") if self._store else None

    def _load_learned(self) -> list[Technique]:
        p = self._default_learned_path()
        if not p or not p.exists():
            return []
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
            return [Technique(id=d["id"], name=d["name"], tags=tuple(d.get("tags", ())),
                              purpose=d.get("purpose", ""), how=d.get("how", ""),
                              idiom=d.get("idiom", ""), when=d.get("when", ""))
                    for d in raw]
        except Exception:  # noqa: BLE001
            return []

    def _persist_learned(self, tech: Technique) -> None:
        p = self._default_learned_path()
        if not p:
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if p.exists():
            try:
                existing = json.loads(p.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                existing = []
        existing = [d for d in existing if d.get("id") != tech.id]
        existing.append(asdict(tech) | {"tags": list(tech.tags)})
        p.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_store() -> Path:
    import os
    return Path(os.environ.get("ACERO_DATA_DIR", "acero_data")) / "method_catalog"
