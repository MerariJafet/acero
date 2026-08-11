# ACERO — Informe de Consolidación Nocturna
### Sprint autónomo del 2026-08-11 · baseline `c84db5f` → `29740b9`

---

## EXECUTIVE SUMMARY

El sprint tenía dos objetivos en tensión: hacer a ACERO **más riguroso** sin
destruir su **libertad creativa**. Se logró medir ambos:

- **Rigor**: el benchmark de descubrimiento pasó de **FDR 0.333 → 0.000** (cero
  falsos descubrimientos en los tres casos nulos), a costa de bajar el TDR de
  0.889 a 0.778. Intercambio deliberado y documentado.
- **Creatividad**: se añadió la capa LEGO (capacidades componibles), la jugada
  REINTERPRETAR (cambio de representación) y un presupuesto EXPLORE/EXPLOIT que
  impide que el PolicyEngine mate una idea rara por no tener prior histórico.
- **Prueba de fuego**: en una misión con ley oculta (`y = 4a/b²`, nunca revelada
  al descubridor), ACERO **encontró la ley** vía una representación que construyó
  solo — `corr(a/b, b·y) = 1.000`, que es la ley reordenada.

Suite unitaria: **verde, 0 fallos**.

---

## COMMITS DEL SPRINT

| Commit | Qué |
|---|---|
| `4f328a2` | procedencia de scores versionada + violaciones como evento auditable |
| `3d78a0a` | dossier de consolidación + historia experimental forense |
| `c84db5f` | gauntlet de descubrimiento (Fase 9) + decisión Turing registrada |
| `29740b9` | **capa LEGO + rivales/discriminación conectadas + descubrimiento sin falsos positivos** |

---

## ARQUITECTURA: ANTES → DESPUÉS

**Antes.** Bohr elegía una jugada de un menú fijo de 13. Los scores positivos
(peso total 4.0) eran autodeclaración del LLM. `information_gain`,
`discriminating`, `invariants`, `rival_theory_generator` y `symbolic_search`
existían sin un solo consumidor. Mendeleev producía correlaciones triviales con
puntaje perfecto.

**Después.**
```
    CREATIVIDAD (Bohr/Ramanujan/Feynman/Turing)
              ↓  ideas, analogías, representaciones
    LEGO: capacidades con conectores tipados (accepts/produces)
              ↓  composiciones que EMERGEN, no programadas
    POLICY ENGINE: administra ATENCIÓN y CÓMPUTO
       proposer (LLM) | mechanical (EIG real) | historical (ledger)
       + presupuesto EXPLORE para ideas sin prior
              ↓
    EXPERIMENTO → RESULTADO
              ↓
    CONSTITUCIÓN EPISTÉMICA: idea≠evidencia, patrón≠ley,
                             evidencia≠prueba, correlación≠causa
```

---

## CÓDIGO MUERTO CONECTADO

| Módulo | Estado antes | Ahora |
|---|---|---|
| `discovery/information_gain.py` | solo un benchmark | **calcula la información esperada del PolicyEngine** (EIG bayesiana con rivales; heurística log2(k) si no) |
| `inference/active_experiments/discriminating.py` | solo un benchmark | jugada `discriminar` de Bohr vía `science/rivals.py` |
| `inference/discovery/invariants.py` | fuera del ciclo | `InvariantDiscoverer` dentro de Mendeleev |
| `epistemic/rival_theory_generator.py` | endpoint aparte | jugada `rivales`, adaptada a matemáticas |

**Sigue muerto** (declarado, no escondido): `inference/discovery/symbolic_search.py`
(cero importadores), `science/holdout.py`, `science/nulls.py` — el holdout y los
nulos se implementaron *nuevos y conectados* en `patterns.py` porque los módulos
existentes no encajaban con el flujo de Mendeleev; consolidarlos queda pendiente.

---

## RESULTADOS DEL BENCHMARK DE DESCUBRIMIENTO

| Configuración | True Discovery Rate | False Discovery Rate |
|---|---|---|
| solo estadística | 0.444 (4/9) | **0.000** |
| + simbólico | 0.556 (5/9) | **0.000** |
| **Mendeleev completo** | **0.778 (7/9)** | **0.000** |

**Aporte marginal** del completo sobre solo-estadística: `lineal`, `recurrencia`,
`representacion_escondida` — los motores nuevos se ganaron su lugar.

**Los 2 que aún falla** (declarados, no maquillados): `modular` (y = x mod 7) y
`valor_absoluto_pearson0` — el endurecimiento del nulo los sacrificó. Son el
objetivo concreto del próximo ciclo.

---

## MISIÓN DE ACEPTACIÓN CONTROLADA (Fase 34)

**Ley oculta**: `y = 4·a/b²`, jamás revelada al descubridor.
**Diseño**: 120 filas de entrenamiento, 40 de holdout selladas, representación
escondida (la relación es invisible en `a` y `b` crudas).

**Resultado**: ✅ **DESCUBIERTA**. El FeatureLab construyó `a/b` y `b*y`, y el
descubridor estadístico halló `corr(a/b, b·y) = 1.000` — que es exactamente
`b·y = 4·(a/b)`, la ley reordenada. El `InvariantDiscoverer` encontró además una
cantidad conservada exacta (variación relativa 0.0000).

**Higiene epistémica en la misma corrida**: 5 patrones marcados TRIVIALES por
linaje compartido y excluidos del ranking; todos los candidatos con
`causality = NO_ESTABLECIDA`; procedencia con hash de dataset y semilla.

---

## LO QUE ACERO APRENDIÓ SOBRE CÓMO INVESTIGAR

De la historia experimental (evidencia del ledger, no opinión):

1. **"No creer un positivo sin segunda opinión hostil"** es la estrategia más
   rentable del sistema — cazó todos los falsos positivos de 5 rondas.
2. **Sanear el instrumento antes que la hipótesis**: tres veces el "resultado"
   previo era artefacto del pipeline.
3. **Cambiar de representación importa más que cambiar de herramienta** — la
   Ronda 4 ejecutó todo bien sobre la mirada equivocada. De ahí nació
   REINTERPRETAR.
4. **Comparar contra números externos no reproducidos internamente** bloqueó una
   línea entera durante 3 rondas.

---

## LO QUE TODAVÍA IMPIDE EL DESCUBRIMIENTO AUTÓNOMO (sin marketing)

1. **El PolicyEngine aún no aprende de verdad.** El prior histórico v0 existe y
   funciona, pero es una tasa de utilidad simple; no distingue *por qué* una
   estrategia funcionó. El Research Genome sigue siendo esquema, no aprendizaje.
2. **Los experimentos del Consejo no son reproducibles exactamente** (scripts en
   caché mutable, entorno no registrado). El camino de misiones sí lo hace: hay
   dos estándares.
3. **El ledger tipado sigue vacío** (0 filas) mientras la ciencia vive en la
   tabla genérica mutable. `update_payload` aún muta sin dejar provenance.
4. **Pre-registro y régimen confirmatorio no participan del ciclo autónomo.**
5. **2 de 9 leyes del benchmark siguen sin detectarse.**
6. **Ninguna investigación real ha producido conocimiento nuevo validado** — y el
   sistema lo dice en cada cierre. El candidato (cover/k=23) sigue esperando
   validación humana externa.

---

## ESTADO DE LAS INVESTIGACIONES REALES

- **Erdős–Straus (Ronda 5)**: VIVA con premisa sellada. 2 derivas leves detectadas
  y ninguna grave — el guardián funciona. La reconciliación 6-vs-5 del cover sigue
  **UNKNOWN/UNRESOLVED**, como debe ser hasta que se documente el porqué.
- **cover_growth**: 5×10¹⁰ alcanzado, rumbo al corte de 10¹¹ para tu revisión.
- **Caccetta–Häggkvist**: 5 semillas n=14 corriendo (techos 168h/240h).

---

## TOP 10 SIGUIENTES TAREAS (por evidencia, no por novedad tecnológica)

1. Recuperar `modular` y `y=|x|` en el benchmark sin subir el FDR.
2. Cerrar el agujero de `update_payload` sin provenance.
3. Persistir script completo + entorno de cada experimento del Consejo.
4. Conectar pre-registro/holdout al régimen confirmatorio del ciclo.
5. Consolidar `holdout.py`/`nulls.py` con lo implementado en `patterns.py`.
6. Test de camino completo con herramienta REAL (hoy es parcial).
7. Reachability CI para capacidades (detectar inalcanzables, no solo huérfanas).
8. Resucitar o enterrar `symbolic_search.py` con criterio explícito.
9. Prior histórico v1: por (acción × estado), no solo por acción.
10. Gauss debe usar `publication/dossier.py` en vez de escribir a mano.

---

## DECISIONES QUE REQUIEREN HUMANO

- **Turing sin sandbox**: decidido por Merari (PC de entrenamiento aislada).
  Registrado como riesgo aceptado, con `PUBLICATION_SECURITY_GATE` documentado
  para antes de cualquier distribución.
- **Cover hacia 10¹²**: espera tu revisión de la tabla al llegar a 10¹¹.
- **Publicación de la nota de covering sets**: sigue esperando validación externa.
- **Driver GPU**: requiere tu reinicio; la política ya está lista.
