# ACERO — Auditoría del cross-match (valle de radios DR25)

**Pregunta de la auditoría:** ¿la pérdida al 0.56 % de coincidencias en el experimento
«Valle Kepler DR25 con completitud» (45 filas útiles, **3 planetas** donde se necesitaban
~54) es un límite científico inevitable o un **defecto de integración**?

**Veredicto: defecto de integración.** `CROSSMATCH_NO_DEFENDIBLE` *tal como se ejecutó*,
pero la **pregunta SÍ es respondible** con las mismas fuentes: la estrategia correcta rinde
**2 841 planetas** en la región del valle — ~950× más que los 3 obtenidos.

---

## Evidencia (consultas TAP reales al NASA Exoplanet Archive)

La tabla `q1_q17_dr25_koi` **ya contiene la metalicidad estelar** (`koi_smet`), el radio
planetario (`koi_prad`) y el periodo (`koi_period`). **No hace falta ningún join externo.**

| Columna en `q1_q17_dr25_koi` | Filas no nulas | de 8054 |
|---|---|---|
| `koi_smet` (metalicidad [Fe/H]) | 7989 | 99.2 % |
| `koi_prad` (radio planetario) | 7995 | 99.3 % |
| `koi_period` (periodo) | 8054 | 100 % |

### Embudo de cobertura (estrategia correcta, una sola tabla)
Ver `ACERO_CROSSMATCH_COVERAGE_TABLE.csv`.

| Etapa | N | Retención |
|---|---|---|
| Total KOIs | 8054 | — |
| CONFIRMED + CANDIDATE (excluye falsos positivos) | 4089 | 50.8 % |
| + metalicidad `koi_smet` | 4083 | 99.9 % |
| + radio `koi_prad` | 4083 | 100 % |
| + periodo `koi_period` | 4083 | 100 % |
| Planetas pequeños (radio 1–4 R⊕) | 3053 | 74.8 % |
| + periodo 0.5–100 d (valle bien definido) | **2841** | 93.1 % |

**La metalicidad casi no cuesta cobertura (99.9 %).** El único recorte real y legítimo es
CONFIRMED/CANDIDATE (excluir falsos positivos) y el recorte físico a planetas pequeños.

---

## Causa raíz del fallo

El script generado por Codex hizo un **join externo** de `q1_q17_dr25_koi` con
`stellarhosts` para «traer» parámetros estelares que **ya estaban en la tabla KOI**. El
join emparejó por una clave que no corresponde entre ambas tablas (nombre de anfitrión vs
`kepid`/`kepoi_name`, con formatos distintos), colapsando a `join_match_fraction=0.0056`
(45 de 8009). Tras los cortes quedaron **3 planetas**.

- **No es** falta de datos (hay 4083 usables).
- **No es** un límite del fenómeno.
- **Es** una decisión de integración equivocada: join innecesario + clave/format mal
  emparejados. Un cross-match por nombre cuando existe un identificador estable
  (`kepid`/`kepoi_name`) es exactamente el antipatrón que la directiva prohíbe.

## Precisión/recall del cross-match ejecutado
- **Recall ≈ 0.011** (45 / 4083 objetos recuperables).
- La muestra de 45 que sí coincidió está **sesgada** por lo que sea que el emparejamiento
  parcial de nombres favoreció (no es una submuestra aleatoria) → cualquier análisis
  poblacional sobre ella es inválido. Se **bloquea**.

## Corrección recomendada (Fase 2 — implementación, siguiente commit)
1. **Codegen consciente del esquema**: antes de cualquier join, comprobar si las columnas
   objetivo ya existen en la tabla base; preferir columnas in-table.
2. **Prohibir join por nombre** cuando hay identificador estable; exigir `kepid`/`kepoi_name`
   con normalización de formato.
3. **Guardarraíl de cobertura**: si un join retiene < X % (p. ej. 60 %) o deja N < tamaño
   mínimo preregistrado, **abortar el análisis poblacional** y reportar `cobertura_insuficiente`
   (el sistema ya degradó el resultado; debe además señalar la causa como defecto, no como
   dato).
4. **Conjunto de verdad de referencia** (10–20 KOIs con [Fe/H] conocido) para validar el
   resolvedor con precisión/recall en un test de integración.

**Conclusión:** la primera corrida quedó inconclusa en parte por este defecto. Con la
integración corregida la muestra pasa de 3 a **2841**, habilitando una re-corrida
exploratoria con poder estadístico real (Fase 3). Esto **no** autoriza aún confirmación:
sólo restaura la base para un análisis exploratorio honesto.
