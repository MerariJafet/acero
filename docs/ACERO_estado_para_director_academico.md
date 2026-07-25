# ACERO — Estado del sistema para revisión académica
## Documento para un investigador senior / director de tesis

*Escrito para obtener una segunda opinión experta. Objetivo declarado: no vender humo.
Se describe qué hace el sistema, con qué garantías, sobre qué datos, y — con el mismo
énfasis — dónde está el techo epistémico y qué NO puede afirmar todavía.*

---

## 1. Qué es, en una frase

ACERO es un **sistema operativo de investigación computacional local, con el humano en el
centro del control**, que recorre de forma autónoma el ciclo científico —literatura,
hipótesis, obtención de datos reales, diseño y **ejecución de análisis**, síntesis y
crítica adversarial— y produce un **dossier reproducible**. Su producto máximo es un
*candidato a revisión humana*, nunca un "descubrimiento".

La novedad de la última etapa no es "más datos ni más agentes", sino una **constitución
científica computable**: reglas de código que separan descubrimiento de confirmación,
hacen explícitas las hipótesis causales, contabilizan todo el espacio de búsqueda, gradúan
la independencia de la evidencia y **acotan la afirmación** que un resultado puede hacer.

---

## 2. Principios epistémicos (codificados, no aspiracionales)

1. **El LLM nunca es evidencia.** El modelo propone, razona y redacta; la evidencia
   proviene de código auditable sobre datos identificables.
2. **Nada es un descubrimiento** hasta revisión humana experta *y* replicación
   independiente. El estado máximo del sistema es "candidato a preprint".
3. **No se fabrican datos, citas, DOIs ni resultados.** Cada dato se descarga con petición
   real y queda con URL + bytes + SHA-256.
4. **Los negativos se preservan**; un resultado sin prueba nula se degrada a inconcluso;
   un positivo exige una segunda implementación.
5. **Reejecución ≠ replicación**; el sistema lo distingue por diseño.
6. **El humano decide todo lo irreversible** (publicar, declarar hallazgo). El sistema
   prepara, nunca publica.

---

## 3. El ciclo de investigación

- **Hipótesis orientadas a descubrimiento**, con filtro de novedad (asentada / en debate /
  abierta / inexplorada) y ángulos (cruce de datos, caza de anomalías, predicción no
  probada).
- **Literatura real**: OpenAlex + arXiv + Crossref, lectura de PDF de texto completo,
  snowballing por referencias citadas, búsqueda semántica por *embeddings*, y **detección
  de retracciones** (probada con Wakefield 1998 → retractado).
- **Fábrica de experimentos** (el diferenciador técnico), con separación estricta de
  responsabilidades:
  1. PLAN (modelo): qué datasets públicos hacen falta (solo hosts en lista blanca).
  2. FETCH (código, sin el modelo): descarga y registra URL + bytes + SHA-256.
  3. CODEGEN (modelo): script autocontenido; recibe el **esquema real** de columnas para
     no programar a ciegas; obliga a **controles nulos** y a un **discriminador**.
  4. RUN (sandbox): ejecución con **red deshabilitada**, límites de CPU/RAM, screening
     estático y bucle de reparación.
  5. VALIDATE + PACKAGE: veredicto `supports|refutes|inconclusive`; sin nulo → inconcluso;
     "supports" exige **verificación cruzada con 2ª implementación**; todo se empaqueta
     reproducible (script, datos, resultado, `run.sh`).
- **Síntesis** → Modelo del Mundo (creencias versionadas, nunca sobrescritas; confianza
  con máximo < 1) + **dossier** automático.
- **Autonomía**: Motor de Misiones (investigar → proponer → ejecutar → sintetizar → bucle
  de rigor), watchdog de literatura, motor de anomalías → hipótesis nuevas.

---

## 4. La Constitución Científica Computable (novedad principal)

Paquete `src/acero/science/` — 13 módulos, ~70 pruebas deterministas. Todo **aditivo**: no
altera el flujo que ya funcionaba.

| Componente | Qué gobierna |
|---|---|
| **Régimen A/B + pre-registro** | Descubrimiento libre vs confirmación bloqueada. Plan congelado + hash sobre el contenido científico (detecta ediciones post-hoc). Prohíbe abrir datos confirmatorios sin protocolo congelado. |
| **Search Space Ledger** | Contabiliza TODO lo explorado (hipótesis/columnas/subsets/transformaciones/modelos/semillas/exclusiones) → *deuda de exploración*. Toda decisión tras ver los datos = exploratoria, por código. |
| **Holdout sellado** | Split determinista (aleatorio/temporal/por grupo) que solo se abre con un evento de *unblinding*; el split por grupo evita fuga de entidad (sujeto/centro/scaffold). |
| **Capa causal (CAUSA)** | DAG + criterio *back-door* por d-separación + estimando explícito + detección de colisionadores/mediadores. Si no es identificable → **prohíbe lenguaje causal**. |
| **Niveles de independencia (0–6)** | Una 2ª implementación NO es independencia. Afirmación fuerte = método distinto **y** dataset independiente. |
| **Claim Compiler** | Evidencia → afirmación máxima permitida (asociado / predice / efecto-bajo-supuestos / replicado). **Lintea** sobreafirmaciones (*demuestra, confirma, causa, descubrimiento*). |
| **Catálogo de nulos** | Nulos que preservan estructura (etiqueta/bloque/sujeto/temporal/espacial…) y avisa cuándo una permutación simple infla los falsos positivos. |
| **Simulation & Recovery Bench** | Universos sintéticos con verdad conocida: mide FPR/potencia/sesgo y **destapa** cuándo un método se deja engañar por confusión, lote o fuga. Una metodología no descubre hasta pasar el bench. |
| **Novedad (4 tipos) + ContributionScore** | Bibliográfica/datos/metodológica/científica; "no encontrado" ≠ "nuevo"; contribución = novedad × evidencia × importancia × robustez × mecanismo. |
| **Presupuesto de incertidumbre** | 9 dimensiones (medición, muestreo, modelo, preprocesamiento, selección, faltantes, generalización, causal, novedad), no un único número. |
| **Panel adversarial plural** | 8 revisores con mandatos incompatibles; preserva el desacuerdo; los mandatos duros (estadístico/causalista/detective de datos) bloquean. |
| **Máquina de estados** | IDEA → … → CANDIDATO_A_PREPRINT (**tope ACERO**) → revisión por pares / publicado / replicado externamente (solo agentes externos). |

---

## 5. Prueba en vivo de la Constitución (evidencia, no promesa)

### 5.1 Primer estudio bajo régimen de confirmación (datos reales)
**Validación de método** sobre 910 moléculas reales de Caco-2 (Therapeutics Data Commons,
descarga con hash). Pregunta: ¿mayor polaridad molecular (proxy de TPSA) predice **menor
permeabilidad**?

- Descubrimiento (n=619): efecto +0.746 logPapp, t=13.1.
- **Protocolo CONGELADO** (hash) antes de tocar el holdout.
- Holdout sellado (n=291) abierto **solo tras congelar** → régimen = confirmación.
- Confirmación: efecto +0.769, t=9.53, **misma dirección** con la regla congelada →
  estado **CONFIRMADO_EN_HOLDOUT**.

*Honestidad:* es una relación **ya conocida** (regla de Veber). Sirve para demostrar que el
sistema **no infla** un resultado exploratorio a "confirmado" sin holdout, no para reclamar
un hallazgo. El holdout es un split del mismo dataset, así que NO se reclama replicación
independiente.

### 5.2 Panel adversarial plural en vivo (8 voces vía LLM)
Sobre ese mismo resultado, cada revisor en su carril:

- **Causalista → defectuoso [BLOQUEA]**: estimando asociacional; **confusión no controlada**
  (peso molecular, lipofilia, clase química).
- **Detective de datos**: sin auditoría de duplicados/sales/tautómeros → posible fuga entre
  splits.
- **Revisor de novedad**: **no novedoso** (recapitula TPSA / Lipinski-Veber).
- **Abogado del mecanismo alternativo**: modelos rivales (tamaño molecular; lipofilia).
- **Redactor hostil**: el abstract debe ser asociativo, no causal.
- Agregado: *en disputa*, **bloqueado por el mandato duro del causalista**.

El panel es **más exigente que un crítico único** y bloqueó el lenguaje causal — el tipo de
disciplina que faltaba.

### 5.3 Otros resultados reales (etapas previas)
- **Astronomía (Fulton gap):** refutación autónoma de una hipótesis nula con datos NASA
  reales (valle recuperado en ~1.82 R⊕). Sin "descubrimiento" declarado.
- **Genómica (EWAS Parkinson, GSE111629):** matriz real de betas 485.512 CpGs × 572
  muestras; t-test + FDR + permutación con λ_gc reportado.
- **Física cuántica:** señales iniciales contradichas por la verificación cruzada →
  reportado *inconclusive* en lugar de forzar un positivo.

---

## 6. Fuentes de datos (públicas, reales, sin llave de pago)

**Bibliografía:** OpenAlex, arXiv (PDF), Crossref (con retracciones).
**Datos estructurados por dominio, con compuertas anti-contaminación cruzada:**

| Dominio | Fuentes |
|---|---|
| Astronomía / física | NASA Exoplanet Archive (TAP), GWOSC, SILSO (solar) |
| Genómica / biomedicina | GEO (NCBI): matrices de expresión/metilación |
| Química — descriptores | PubChem (PUG-REST): MW, XLogP, TPSA, H-bond… (calculados) |
| Química — bioactividad | ChEMBL (EBI): IC50/Ki/EC50/Kd **medidos** con estructura |
| Química — ADME/Tox | TDC (22 datasets: Caco-2, solubilidad, hERG, BBB, CYP, DILI, LD50…) **medidos** |
| Cualquier campo | Zenodo, Figshare, Dryad |

Integridad: lista blanca de hosts, procedencia con SHA-256, introspección de esquema real,
compuerta por dominio (un proyecto de química nunca recibe datos de astronomía), regla de
cruce por coordenadas/ID normalizado (no por nombre).

---

## 7. Autoevaluación honesta (contra las 11 dimensiones de un revisor externo previo)

Un revisor experto previo calificó el sistema en **7.4/10** ("la ingeniería madura más que
la validación científica"). Tras construir la Constitución y probarla en vivo:

| Dimensión | Antes | Hoy (honesto) |
|---|---:|---:|
| Honestidad epistemológica | 9.3 | 9.5 |
| Reproducibilidad computacional | 8.7 | 8.8 |
| Procedencia de datos | 8.5 | 8.7 |
| Automatización del ciclo | 8.4 | 8.4 |
| Análisis estadístico general | 6.8 | 7.3 |
| Inferencia causal | 5.2 | 6.5 |
| Control del espacio de búsqueda | 5.5 | 7.0 |
| Garantía de novedad | 5.8 | 6.8 |
| Validación externa independiente | 4.5 | 5.3 |
| Preparación para publicación | 6.3 | 7.3 |
| Descubrimientos defendibles | 6.0 | 7.2 |

**Global honesto: ~7.4 → ≈8.2.**

---

## 8. Límites y riesgos que pedimos examinar

1. **La confirmación aún se demostró sobre un split del mismo dataset**, no sobre una
   cohorte independiente. `REPLICADO_EN_DATASET_INDEPENDIENTE` exige una 2ª fuente real.
2. **La capa causal está construida pero exige que se declaren DAGs** por hipótesis; hoy
   la mayoría de análisis son asociacionales (y el sistema lo dice).
3. **El panel plural corrió sobre un caso**; falta rodaje y calibración de sus umbrales de
   bloqueo.
4. **Novedad genuina:** distinguir "inexplorado" de "publicado pero no indexado" sigue
   siendo difícil (el revisor de novedad lo mitiga, no lo resuelve).
5. **Dependencia del LLM** para redacción/razonamiento (nunca evidencia, pero sesga la
   formulación).
6. **Autoevaluación no independiente:** por eso este documento.

---

## 9. Preguntas para el revisor

1. Dado el pipeline (datos con hash → nulos por estructura → discriminador → régimen de
   confirmación con protocolo congelado + holdout → panel plural con bloqueo causal →
   dossier), **¿qué falta para que un resultado positivo sea defendible ante un tribunal
   hostil de Nature/PRL?**
2. ¿Qué exigiría además (pre-registro público, hold-out temporal, corrección por
   multiplicidad específica, análisis de sensibilidad, *selective inference*)?
3. ¿Qué pregunta y en qué dominio ofrece la mejor relación "atacable con datos públicos" /
   "genuinamente abierta" para un **primer resultado publicable** (aunque sea un negativo
   robusto o un benchmark metodológico)?
4. ¿La distinción reejecución/replicación y el techo "revisión humana" son garantías
   suficientes, o ve riesgos de sobreinterpretación o mal uso?
5. Para pasar de dossier a preprint: ¿cómo estructuraría el crédito, la declaración de uso
   de IA (la IA nunca es autora) y la trazabilidad de datos para que sean irreprochables?

---

*Resumen de una línea:* **ACERO automatiza el trabajo pesado y reproducible de la
investigación computacional sobre datos públicos, preservando negativos y sometiéndose a un
panel adversarial plural que bloquea el lenguaje causal indebido; separa por código
descubrimiento de confirmación y se detiene deliberadamente en el umbral del
"descubrimiento", que reserva a la replicación y el juicio humano. Buscamos su criterio
sobre si ese umbral está bien puesto y qué haría falta para cruzarlo con rigor.***
