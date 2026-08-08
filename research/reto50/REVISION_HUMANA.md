# Revisión humana de los supervivientes (needs_human_review) — Reto 50

Revisor: Claude (como par matemático, criterio crítico + intento real de rescate).
Fecha: 2026-08-08. Techo: nada aquí es descubrimiento sin revisión de expertos humanos.

## Método de revisión
Leí los bocetos reales de cada superviviente de teoría de números (donde las
herramientas formales de ACERO pueden morder) y, en el más prometedor (Lehmer),
endurecí el boceto en lemas PRECISOS y los verifiqué mecánicamente.

## Rescate ejecutado: Lehmer totiente
Afirmación madre (ABIERTA): no existe compuesto n con φ(n) | n−1.
Condiciones necesarias sobre cualquier contraejemplo, verificadas:
- **Lema A** (Z3, unsat): para p≥2 es imposible que p | n y p | (n−1). → base de "libre de cuadrados".
- **Lema B** (exhaustivo exacto): ningún compuesto n ≤ 2,000,000 cumple φ(n) | n−1.
- **Lema C** (deducción, consistente con datos ≤20000): todo contraejemplo sería impar y libre de cuadrados.

**Novedad: NULA.** Son exactamente los resultados de Lehmer (1932) y verificación
computacional ya conocida. Correcto ≠ nuevo. Valor real: el sistema los re-derivó y
verificó de forma autónoma — buena señal de fiabilidad, no un aporte.

## Veredicto honesto sobre los ~33 needs_human_review
Los bocetos son de buena calidad y señalan la grieta REAL de cada problema
(Brocard: exprimir congruencias sobre primos grandes; Beal: reducir a triples
primitivos = Fermat generalizado; Erdős–Moser: valuaciones p-ádicas). Pero en
TODOS, el paso de "grieta identificada" a "teorema nuevo" requiere maquinaria
matemática (curvas, cribas, formas modulares, geometría aritmética) que está
fuera del alcance de sympy/Z3 + búsqueda. No hay conocimiento nuevo rescatable
esta noche, y afirmar lo contrario sería precisamente el "Erdősgate" que este
programa existe para prevenir.

## Dónde SÍ vive el conocimiento nuevo (siguiente paso real)
El aporte no saldrá de re-atacar los 50 famosos, sino de VARIANTES abiertas y
acotadas donde las herramientas de ACERO son decisivas: casos finitos de
conjeturas combinatorias/de grafos verificables por Z3, cotas explícitas nuevas,
o condiciones necesarias más finas en un rango computable. Recomendación: elegir
1–2 problemas (p.ej. Erdős–Straus por residuos, o un caso finito de
Caccetta–Häggkvist) y pedir a Hipatia la novedad del LEMA (no de la conjetura
madre) antes de invertir un ciclo profundo.
