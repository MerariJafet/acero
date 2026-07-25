# ACERO — Sistema operativo para el descubrimiento científico asistido
## Documento para revisión por especialista en publicación y creación de conocimiento

*Preparado para obtener una perspectiva externa. Escrito con el objetivo explícito de
no sobrevender: se describe lo que el sistema hace de verdad, cómo lo hace, con qué
datos, y — con igual énfasis — dónde están sus límites y su techo epistémico.*

---

## 1. Qué es (en una frase honesta)

ACERO es un **sistema operativo de investigación local, con el humano en el centro
del control**, que toma una pregunta científica y recorre de forma autónoma el ciclo
completo — revisión de literatura, formulación de hipótesis, diseño y **ejecución real
de experimentos computacionales sobre datos públicos verificables**, síntesis, y
crítica adversarial — produciendo al final un **dossier reproducible**. 

Lo que ACERO **no** es, y por diseño nunca afirma ser: no es un oráculo que "descubre"
solo. Su producto máximo es *un candidato a revisión humana*, no un hallazgo. Toda
salida de un modelo de lenguaje se trata como **ayuda de razonamiento y redacción,
nunca como evidencia**.

---

## 2. Principios epistémicos (el corazón del diseño)

Estos principios están codificados en el sistema (reglas de un "gate" epistémico,
políticas y guardas de código), no son solo aspiracionales:

1. **Nada es un descubrimiento** hasta que hay revisión humana experta *y* replicación
   independiente. El sistema tiene una escalera de estados cuyo techo es
   `LISTO_PARA_REVISIÓN_CIENTÍFICA_HUMANA`; estados como "descubrimiento confirmado"
   están deliberadamente **no implementados**.
2. **La síntesis de un LLM nunca es evidencia.** El modelo propone, razona y redacta;
   la evidencia siempre proviene de datos reales procesados por código auditable
   ejecutado en un entorno controlado.
3. **No se fabrican datos, citas, DOIs ni resultados.** Cada dato se descarga con una
   petición real y queda registrado con URL, tamaño en bytes y hash SHA-256. Cada cita
   proviene de un índice bibliográfico real.
4. **Un resultado negativo bien hecho vale más que un positivo mal hecho.** Los
   resultados que refutan o que son inconclusos se preservan; no se "limpian" ni se
   reinterpretan a conveniencia.
5. **Reejecución ≠ replicación.** El sistema distingue explícitamente entre volver a
   correr su propio código (reproducibilidad de proceso) y una replicación externa
   independiente (que solo puede hacer un tercero humano).
6. **El humano tiene la última palabra en todo lo irreversible**: publicar, fusionar a
   la rama principal, o declarar un hallazgo. El sistema prepara, nunca publica.

---

## 3. El ciclo de investigación, paso a paso

### 3.1 Formulación de hipótesis orientada al descubrimiento
El sistema no genera hipótesis "confirmatorias" por defecto. Cada hipótesis se etiqueta
con un **filtro de novedad** que la clasifica en:
- `asentada` (ya se sabe — señal roja),
- `en_debate` (hay controversia activa),
- `abierta` (pregunta reconocida pero sin respuesta),
- `inexplorada` (frontera).

Además cada hipótesis lleva un **ángulo de descubrimiento**: cruce de datos entre
catálogos, caza de anomalías, predicción no probada, o pregunta abierta no atacada.
El objetivo declarado es empujar hacia la frontera, no reconfirmar lo conocido.

### 3.2 Revisión de literatura real
- Búsqueda **multi-fuente**: OpenAlex, arXiv y Crossref (la consulta en inglés la
  extrae el modelo, pero las fuentes son índices reales).
- **Lectura de texto completo**: descarga y lee PDFs de acceso abierto (p. ej. arXiv)
  con extracción de texto, no solo abstracts.
- **Snowballing** real: sigue las referencias citadas (referenced_works de OpenAlex)
  para profundizar dos niveles.
- **Búsqueda semántica** con *embeddings* (modelo de frases local, con respaldo por
  palabras clave) para recuperar lo relevante del corpus del proyecto.
- **Detección de retracciones**: verifica vía Crossref si un trabajo citado fue
  retractado (probado con el caso Wakefield 1998 → marcado como retractado).

### 3.3 La Fábrica de Experimentos (el diferenciador técnico)
Aquí es donde una hipótesis deja de ser una charla y se convierte en un experimento
**ejecutado**. El pipeline tiene cinco etapas con separación estricta de
responsabilidades:

1. **PLAN (modelo):** decide qué datasets públicos se necesitan. Solo puede nombrar
   fuentes de una **lista blanca de hosts científicos**; no inventa URLs.
2. **FETCH (código confiable, sin el modelo):** el sistema —no el LLM— descarga los
   datos por HTTPS desde hosts permitidos, y registra **URL + bytes + SHA-256** como
   procedencia verificable. El modelo nunca toca la red.
3. **CODEGEN (modelo):** escribe un script de análisis autocontenido. Antes se le
   entrega el **esquema real** de los datos (nombres de columna e ítems reales, leídos
   del archivo descargado — CSV/TSV y también arrays JSON), de modo que no programa "a
   ciegas". El script debe aplicar **controles nulos** y un **discriminador** explícito,
   y emitir el resultado en un contrato estructurado.
4. **RUN (sandbox):** ejecuta el script con **la red deshabilitada**, límites de CPU y
   memoria, y screening estático. Si falla, hay un **bucle de reparación** (hasta 2
   rondas) que devuelve el error al modelo para corregir.
5. **VALIDATE + PACKAGE:** el resultado se valida contra un esquema (el veredicto debe
   ser `supports | refutes | inconclusive`; **si falta el test nulo, se degrada a
   inconclusive** automáticamente). Para un veredicto de "supports" se exige una
   **verificación cruzada con una segunda implementación independiente** (o se degrada).
   Todo — script, datos, resultado, salida estándar, `run.sh` — se empaqueta en un
   **directorio de artefactos reproducible**.

Guardas relevantes: deadline de descarga por archivo (mata descargas desbocadas),
caché por hash de URL, auto-descompresión (.gz/.zip), saneado de bytes de control, y
poda de datos voluminosos tras el éxito.

### 3.4 Síntesis → Modelo del Mundo + dossier
Los veredictos se integran en un **Modelo del Mundo** (grafo de conocimiento):
- Las creencias se guardan como nodos versionados y **nunca se sobrescriben** (se
  versiona la historia); las relaciones **nunca se borran** (se debilitan/desactivan).
- La confianza tiene un **máximo estricto menor que 1** (nunca certeza total).
- De cada hipótesis se genera un **dossier** automático (afirmación, evidencia a favor
  y en contra, tarjeta de fiabilidad, nivel de preparación, limitaciones, descargos).

### 3.5 Aristóteles — el revisor adversarial residente
Un agente crítico con "alma" definida (persona de revisor senior escéptico: Popper,
Lakatos, Kuhn; conoce p-hacking, HARKing, look-elsewhere, sesgo de publicación, y
errores históricos célebres como los neutrinos superlumínicos o BICEP2). Tras **cada
tarea** (generar hipótesis, confrontar literatura, correr un experimento) se activa,
lee los abstracts reales del proyecto como contexto, y emite una crítica estructurada:
veredicto (`sólido|prometedor|débil|defectuoso`), objeciones concretas, explicaciones
alternativas no descartadas, sugerencias ejecutables, y "la pregunta más incómoda".
Sus objeciones son **rastreables**: se convierten en experimentos de refuerzo, se
resuelven con evidencia, y alimentan un *rigor score*. Su salida es material para el
revisor humano, **nunca evidencia**.

### 3.6 Autonomía: el Motor de Misiones
Una "misión" por hipótesis aprobada recorre el ciclo sola:
`investigar → proponer experimentos → ejecutar → sintetizar → bucle de rigor`
(auto-consulta a Aristóteles, convierte sus sugerencias en experimentos, los corre,
re-sintetiza y re-evalúa objeciones). Es persistente y reanudable (checkpoints), con
progreso 0–100%. Un **watchdog** vigila la literatura nueva de forma continua, y un
**motor de anomalías** convierte resultados inesperados en hipótesis nuevas.

---

## 4. Fuentes de conocimiento y datos estructurados

Todas las fuentes son **públicas, reales y sin llave de pago**. El sistema resuelve una
*referencia* (accesión, DOI o nombre de dataset) a una **URL descargable real**, y
aplica **compuertas por dominio** (anti-contaminación cruzada: un proyecto de química
nunca recibe datos de astronomía, y viceversa — tanto al resolver accesiones como al
filtrar URLs directas por host).

### Literatura / bibliografía
| Fuente | Qué aporta |
|---|---|
| **OpenAlex** | índice bibliográfico masivo, referencias citadas (snowballing) |
| **arXiv** | preprints + PDF de texto completo |
| **Crossref** | metadatos, DOIs, **detección de retracciones** |

### Datos científicos estructurados (por dominio)
| Dominio | Fuente | Contenido | Acceso |
|---|---|---|---|
| Astronomía | **NASA Exoplanet Archive (TAP)** | planetas confirmados, KOI DR25, parámetros estelares | consulta ADQL→CSV |
| Astronomía/física | **GWOSC** | ondas gravitacionales | público |
| Solar | **SILSO** | serie histórica de manchas solares | CSV |
| Genómica/biomedicina | **GEO (NCBI)** | matrices de expresión/metilación (series-matrix + suplementarios, p. ej. betas 450K) | FTP determinista |
| Química | **PubChem (PUG-REST)** | descriptores fisicoquímicos **calculados** (MW, XLogP, TPSA, HBD/HBA…) | CSV, sin llave |
| Química/farmacología | **ChEMBL (EBI)** | bioactividades **medidas** de dianas (IC50/Ki/EC50/Kd) + estructura | JSON, sin llave |
| Química ADME/Tox | **TDC (Therapeutics Data Commons)** | 22 datasets curados con SMILES + endpoint **medido** (Caco-2, solubilidad, hERG, BBB, CYP, DILI, LD50…) | Harvard Dataverse, ids verificados |
| Cualquier campo | **Zenodo, Figshare, Dryad** | repositorios generales de datos (DOI→archivos/bundle) | API pública |
| Química/bio/estructura | **PubChem, RCSB PDB, UniProt, EBI** | en lista blanca de descarga | público |

**Nota sobre la capa de química** (la más desarrollada recientemente, en tres estratos
complementarios): descriptores *calculados* (PubChem) + bioactividad de *diana* medida
(ChEMBL) + endpoints ADME/Tox *medidos* a nivel molécula (TDC). Cada id de dataset de
TDC fue **verificado con una descarga real** antes de cablearse (no se confió en el
mapa oficial sin comprobar).

### Cómo garantiza integridad de los datos
- **Lista blanca de hosts**: solo se descarga de fuentes científicas conocidas.
- **Procedencia criptográfica**: URL + bytes + SHA-256 por archivo.
- **Introspección de esquema real** antes de programar el análisis.
- **Compuerta por dominio** en dos ejes (resolvedor + host) para evitar mezclar campos.
- **Regla de cruce por coordenadas/ID normalizado**, no por nombre (un cruce por nombre
  de objeto/estrella falló de verdad y se corrigió).

---

## 5. Reproducibilidad y trazabilidad

- Cada experimento deja un **paquete reproducible**: script exacto, datos (con hash),
  resultado, salida estándar y un `run.sh` para reejecutar.
- Existe un **paquete independiente** (sin dependencias del propio ACERO, solo
  numpy/scipy/astropy) y una **sala limpia Docker** que reprodujo de forma aislada un
  resultado (periodo de tránsito de Kepler-8), alcanzando el estado
  `REPRODUCCIÓN_INDEPENDIENTE_DE_PROCESO` — que el sistema distingue explícitamente de
  una replicación externa.
- El conocimiento se exporta a un **vault Obsidian** dedicado (MOCs por proyecto,
  hipótesis con versiones y confrontación, literatura con abstract+DOI, experimentos),
  para lectura y anotación humana.
- Motor de **fiabilidad y calibración**: Brier score, ECE/MCE, cobertura, abstención;
  *red-teaming* con ataques→detectores; tarjeta de fiabilidad sin un único "score de
  confianza" opaco.

---

## 6. Evidencia de que funciona (pruebas reales de esta etapa)

Resultados obtenidos por el sistema operando de forma autónoma sobre datos reales
(reportados con honestidad, incluidos los negativos):

- **Astronomía — "Fulton gap" (valle de radios de exoplanetas):** con datos reales de
  la NASA, el sistema **refutó autónomamente** una hipótesis nula (que el valle fuese
  un artefacto de selección), recuperando el valle en ~1.82 R⊕; Aristóteles machacó el
  resultado, se resolvieron 2 objeciones con evidencia, y se llegó a un consenso real
  (valle físico, mecanismo aún abierto). Ningún "descubrimiento" declarado.
- **Genómica — EWAS de metilación (Parkinson, GSE111629):** descargó la matriz real de
  betas (~1.2 GB, **485,512 CpGs × 572 muestras**), corrió t-test + FDR + permutación →
  veredicto `supports` con λ_gc reportado (indicador honesto de inflación).
- **Física cuántica — memoria no-markoviana (datos de corrección de errores):** las
  señales iniciales (ACF, Fano) fueron **contradichas por la verificación cruzada** →
  el sistema reportó `inconclusive` en vez de forzar un positivo. Honestidad sobre
  entusiasmo.
- **Química (esta etapa):** se desbloqueó la ejecución con datos reales (PubChem +
  ChEMBL + TDC) tras cerrar un bug real de contaminación cruzada que el propio proceso
  de validación destapó.

**Autoevaluación honesta del sistema (no independiente):** ~8.5–9/10 en razonamiento y
honestidad; algo menor en "generación de conocimiento *nuevo*" (descubrir es raro y
requiere rodaje). Comparable en ambición a iniciativas como AI Scientist (Sakana) o AI
co-scientist (Google), con énfasis diferencial en **honestidad y reproducibilidad**.
Aún **sin ningún descubrimiento validado** — y el sistema es el primero en decirlo.

---

## 7. Ruta de publicación prevista (donde entra el revisor humano)

El sistema prepara; la ciencia la avala una persona. La ruta diseñada:

`dossier ACERO → validación humana (comprensión + aprobación explícita, ligada por hash
al dossier exacto) → revisión por un experto del dominio → preprint (arXiv/bioRxiv) →
DOI de datos/código en Zenodo → revista con revisión por pares`

El **techo es siempre la revisión humana**: el sistema puede emitir
`APROBAR_PARA_REVISIÓN_EXTERNA` / `PEDIR_CAMBIOS` / `RECHAZAR`, pero **no existe**
`APROBAR_PARA_PUBLICACIÓN`. La IA nunca figura como autora (se declara su uso como
herramienta, siguiendo el espíritu de CRediT).

---

## 8. Límites y riesgos conocidos (lo que pediríamos que el revisor examine)

Con total franqueza, estas son las debilidades que más nos interesa que un especialista
juzgue:

1. **El cuello de botella no es el razonamiento sino el acceso a datos y la robustez del
   pipeline.** El razonamiento científico y la honestidad funcionan bien; la cobertura
   de datos por dominio es desigual (astronomía, genómica y química están bien; otros
   dominios menos).
2. **Riesgo de "descubrimiento" espurio por p-hacking / look-elsewhere / garden of
   forking paths.** Hay mitigaciones (nulos obligatorios, verificación cruzada,
   Aristóteles, degradación a inconclusive), pero merece escrutinio experto: ¿son
   suficientes los controles nulos y las correcciones por comparación múltiple?
3. **Reejecución vs replicación.** El sistema es cuidadoso con la distinción, pero una
   reproducción de proceso sobre los *mismos* datos no aporta independencia real.
4. **Dependencia de un modelo de lenguaje para redacción/razonamiento.** Aunque nunca es
   evidencia, sesga la formulación de hipótesis y la lectura de literatura (¿se lee "el
   paper incómodo" o el que confirma?).
5. **Novedad genuina.** Distinguir "inexplorado" de "ya publicado pero no indexado por
   nuestras fuentes" es difícil; ¿cómo evaluaría un experto la garantía de novedad?
6. **Autoevaluación no independiente.** El 8.5–9/10 es autorreporte; la evaluación real
   la debe hacer alguien externo — de ahí este documento.
7. **Endpoints y datasets concretos**: p. ej. TDC entrega un valor agregado por
   molécula (bueno para estructura-propiedad), no curvas dosis-respuesta; para SAR fina
   por diana hace falta ChEMBL. ¿Son adecuadas estas elecciones para una pregunta
   publicable?

---

## 9. Preguntas concretas para el revisor

1. Dado el pipeline (datos verificados → nulos → discriminador → verificación cruzada →
   crítica adversarial → dossier), **¿qué le falta para que un resultado positivo sea
   defendible ante un revisor hostil de Nature/PRL?**
2. ¿Qué controles estadísticos adicionales exigiría (pre-registro, hold-out externo,
   corrección por múltiples comparaciones específica, análisis de sensibilidad)?
3. ¿Qué tipo de pregunta científica —y en qué dominio— tendría la mejor relación entre
   "atacable con datos públicos" y "genuinamente abierta", para intentar un primer
   resultado *publicable* (aunque sea un negativo bien hecho)?
4. ¿La distinción reejecución/replicación y el techo de "revisión humana" son
   suficientes garantías de integridad, o ve riesgos de mal uso o de sobreinterpretación?
5. ¿Cómo estructuraría usted el paso de dossier → preprint para que el crédito, la
   declaración de uso de IA y la trazabilidad de datos sean irreprochables?

---

*Resumen de una línea para el revisor:* **ACERO automatiza el trabajo pesado y
reproducible de la investigación computacional sobre datos públicos, preservando
negativos y sometiéndose a crítica adversarial, pero se detiene deliberadamente en el
umbral del "descubrimiento" — que reserva al juicio y la replicación humana. Buscamos su
criterio sobre si ese umbral está bien puesto y qué haría falta para cruzarlo con rigor.*
