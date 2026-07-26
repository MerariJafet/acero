# ACERO — Resultados del benchmark de recuperación (P1, corrida en vivo)

Primera prueba a nivel de pipeline completo: ¿ACERO recupera el veredicto correcto en
preguntas con respuesta conocida? 6 controles (3 positivos establecidos + 3 nulos
espurios), cada uno por el ciclo completo con Codex y datos reales del NASA Exoplanet
Archive. Fecha: 2026-07-25.

## Matriz de aciertos: **3/6 (50%)**

| Control | Esperado | Resultado | ¿Correcto? |
|---|---|---|---|
| metalicidad ↔ gigantes gaseosos | positivo | **refuted** | ❌ |
| periodo ↔ insolación (casi tautológico) | positivo | **inconclusive** | ❌ |
| relación masa–radio | positivo | **inconclusive** | ❌ |
| radio ↔ ascensión recta (RA) | nulo | refuted | ✅ |
| radio ↔ año de descubrimiento | nulo | refuted | ✅ |
| longitud del nombre ↔ periodo | nulo | inconclusive | ✅ |

## Lectura honesta

**Lo excelente — 3/3 nulos, CERO falsos positivos.** Ninguna correlación basura pasó como
positiva. La propiedad central de ACERO («te impide engañarte») queda **validada
empíricamente**: no inventa descubrimientos.

**Lo preocupante — 0/3 positivos.** ACERO NO recuperó ni una relación establecida, ni
siquiera periodo↔insolación (que es casi una tautología física: insolación ∝ L⋆/a² y a
crece con el periodo). Su «inconcluso» aquí es, en parte, **incapacidad**, no solo
honestidad — exactamente lo que el benchmark existía para detectar.

## Causa raíz (inspección de los experimentos)

1. **Sobre-complicación en la generación de hipótesis.** Ante una pregunta de respuesta
   obvia, ACERO NO prueba la relación directa: inventa un discriminador mecanístico
   elaborado y luego falla su propio umbral. Ejemplos reales de esta corrida:
   - periodo↔insolación se volvió *"enriquecimiento de parámetros estelares en los
     residuales negativos del valle"* con `delta_adj_R2` y nulos pareados — en vez de
     *"correlaciona el periodo con la insolación"*.
   - metalicidad↔gigantes se volvió *"función de detección plana vs ley de formación"* en
     vez de *"la ocurrencia de gigantes sube con [Fe/H]"*.
   El sistema tiene **sesgo hacia la complejidad**, y eso le hace perder verdades simples.

2. **La varianza del cross-check degrada positivos reales (P2 confirmado).** En
   metalicidad↔gigantes, 2 experimentos que daban `supports` fueron **degradados a
   inconclusive** porque la 2ª implementación discrepó (veredictos y métricas divergentes).
   El "degradado por ACERO" está, al menos en parte, **enmascarando señal real** por
   inestabilidad de codegen, no protegiendo de un artefacto.

## Implicación

El valor de ACERO hoy es **especificidad casi perfecta** (no falsos positivos) a costa de
**sensibilidad muy baja** (no recupera positivos). Para un descubridor útil hay que subir
la sensibilidad SIN perder la especificidad. Dos frentes, en orden:

1. **Hipótesis proporcionadas a la pregunta** — cuando la pregunta admite una prueba
   directa simple, generar/priorizar esa antes que un discriminador barroco.
2. **Estabilizar el cross-check** (P2) — reducir la varianza de codegen (fijar semilla,
   contrato de métricas más estricto, o exigir que la 2ª implementación comparta el mismo
   estimando) para que un positivo real no se degrade por desacuerdo verbal.

**El benchmark FUNCIONA**: dio un número accionable y localizó el problema. Correrlo tras
cada cambio dirá si subimos sensibilidad sin romper la especificidad.
