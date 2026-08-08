# TOOLBOX — las piezas de LEGO matemáticas de ACERO

Catálogo vivo (código: `src/acero/science/toolbox.py`, máquina-legible para que
Ramanujan y Turing lo lean). Fecha: 2026-08-08.

## ¿Qué es "Sage completo" y cómo lo conseguimos?

**SageMath** es el sistema de matemáticas open-source más grande del mundo: envuelve
~100 bibliotecas (PARI, FLINT, GAP, Singular, Maxima…) bajo un solo lenguaje Python.
Cubre lo que ninguna pieza suelta cubre junta: geometría aritmética, grupos de Galois,
grupos de clases, variedades abelianas, combinatoria algebraica, teoría de esquemas.

Investigación de vías (2026-08-08, Ubuntu 24.04):
| Vía | Estado | Nota |
|---|---|---|
| `pip install sage` | ❌ imposible | Sage no se distribuye por pip (GB + compilación) |
| `apt install sagemath` | ❌ sin candidato | Ubuntu 24.04 lo retiró de sus repos |
| conda-forge (`mamba create -n sage sage`) | ⚪ viable no usada | exigiría instalar miniforge |
| **Docker `sagemath/sagemath`** | ✅ **INSTALADA** | Sage 10.9; mismo patrón jaulado que acero-agent |

Uso desde ACERO: `from acero.science.toolbox import run_sage; run_sage("E = EllipticCurve(...); print(E.rank())")`
— corre **sin red** en el contenedor y devuelve stdout. Verificado: rango de 11a1=0,
grupo de clases de ℚ(√−23)=3.

## El catálogo por niveles de honestidad

**prueba-simbólica / prueba-mecánica** (lo que sale de aquí PUEDE ser teorema):
- **sympy** — identidades, desigualdades, límites, sumas; simplificación exacta.
- **z3** — SMT/SAT: `unsat` es prueba mecánica; combinatoria finita, casos acotados con WLOG.
- **frontier_toolkit** (propio) — familias paramétricas probadas por período modular
  (paridad clásica Erdős–Straus lograda); CH k=3 acotado por Z3; obstrucciones.
- **formal_verify** (propio) — verificador formal con timeout duro (proceso hijo).

**cálculo-experto** (evidencia de altísima calidad, no teorema por sí sola):
- **cypari2 / PARI-GP** — curvas elípticas (rangos, ap, conductores), formas modulares, L-funciones.
- **python-flint** — polinomios/matrices exactos ultrarrápidos; primalidad PROBADA; arb (cotas de error rigurosas).
- **gmpy2** — enteros GMP gigantes; next_prime; potencia modular veloz.
- **sage (docker)** — TODO lo anterior más geometría aritmética, Galois, grupos, combinatoria algebraica.

**evidencia-numérica** (explora, sugiere, jamás prueba):
- **numpy / scipy** — barridos vectorizados, optimización, estadística.
- **networkx** — grafos: generación masiva, invariantes, contraejemplos.
- **mpmath** — precisión arbitraria flotante, funciones especiales.
- **math_probe** (propio) — probador experimental codegen+sandbox+repair.

**literatura**:
- **novelty_check / Hipatia** (propio) — ¿ya se hizo? multi-fuente con DOIs (anti-Erdősgate).

## El flujo de la chispa (nuevo)

1. **Frontera declarada** — "con lo actual no se puede" + por qué.
2. **Ramanujan** (`spark.py`) lee el catálogo y genera chispas: "¿y si mejor usamos
   matrices?" — analogías entre ramas, reformulaciones, puentes entre piezas; cada una
   con probabilidad honesta y el primer experimento barato que la mata o la aviva.
3. **El matemático (Gauss/Gödel)** elige piezas: "tengo estas, probemos" o "me falta
   esta" → `toolbox.ensure()` la instala (pip/docker) o Turing la construye.
4. **Turing** (`turing.py`) programa el experimento, lo corre, lee el error, repara y
   reintenta — presupuesto en HORAS, no en intentos. Todo al ledger.
5. El resultado vuelve al Consejo: Gödel intenta promover a prueba, Aristóteles
   critica, Hipatia dictamina novedad. **Una chispa jamás es un resultado.**
