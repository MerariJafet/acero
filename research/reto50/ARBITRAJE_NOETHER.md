# Informe de referee — Noether (arbitraje interno)

**Veredicto:** revision_mayor

**Resumen del árbitro:** El manuscrito propone estudiar, para las seis clases duras módulo 840 de Erdős-Straus, una familia tipo II parametrizada por auxiliares k y el tamaño de conjuntos de cobertura finitos sobre primos duros hasta N. La idea de convertir la familia en un problema de cobertura auxiliar parece potencialmente útil como objeto computacional, pero en la forma actual mezcla teoremas algebraicos, evidencia empírica y conjeturas con varios desajustes lógicos. El principal problema técnico es que la definición de C(N) no fija el universo admisible de k ni exige k ≡ 3 mod 4, por lo que el “mínimo” no está formalmente definido como lo computado; además algunos claims de minimalidad no están respaldados si se usó voraz salvo donde haya ILP exacto reproducible. La parte de k=23 contiene álgebra plausible y dos subcasos monomiales verificables, pero el criterio reducido debe escribirse como una proposición con hipótesis exactas y prueba modular completa, no como mezcla de verificación y explicación heurística.

## Fortalezas

- Objeto computacional claro y falsable: grafo bipartito primo duro ↔ auxiliar k para una familia tipo II específica.
- Separación explícita, aunque imperfecta, entre evidencia acotada, conjetura global y comparación con la conjetura madre.
- El criterio de divisor t | (px)^2, t ≡ -px mod k es una reducción algebraica concreta y fácil de auditar.
- La anatomía de k=23 es el componente más prometedor: los casos p ≡ 19,22 mod 23 tienen pruebas cortas mediante t=p y t=x.
- El manuscrito declara limitaciones importantes: no reclama resolver Erdős-Straus, reconoce dependencia de cómputo y necesidad de attestation externa.
## Objeciones MAYORES (bloquean)

- Definición formal de C(N) incorrecta/incompleta. Se define como menor S ⊆ N, pero los cálculos usan auxiliares k ≡ 3 mod 4 y aparentemente k ≤ 255, quizá también k positivo. Debe definirse C_K(N), por ejemplo dentro de K_B={k≤B:k≡3 mod 4}, y distinguir: cobertura mínima exacta restringida a K_B, cobertura voraz, y cobertura universal con bound B. Sin esto, los números de |cover| no tienen significado matemático estable.
- La afirmación “minimal covering sets” no está probada para 10^8 y 10^9, y es ambigua para 10^5–10^7. Si hay ILP exacto solo hasta 10^7, la tabla debe decir “mínimo exacto por ILP” en esas filas y “cover encontrado sobre muestra” en las otras. “voraz+poda” no certifica minimalidad salvo que se acompañe de certificado dual/ILP de optimalidad.
- El claim “todo primo duro hasta 10^9 es decidido por algún k≤255” requiere certificado reproducible completo, no muestra estratificada. La tabla dice sin cobertura 0 para 10^9, pero luego los certificados explícitos completos solo se publican hasta 10^5 y la muestra estratificada a escalas mayores. Debe publicarse al menos un log auditable con hash, versión de código, conteos por k, y rutina independiente que reescanee los 1,587,420 primos.
- Inconsistencia sobre k=23 en 10^8–10^9: el resumen lo presenta como share de cobertura, pero la nota al pie dice “decide como PRIMERO en el orden de prueba”, que es solo una cota inferior dependiente del orden. Debe recalcularse cobertura intrínseca de k=23: número de p para los cuales existe certificado con k=23, independientemente de otros k.
- La conjetura C-ACERO-1 y la pregunta |C(N)|=O(log N) no son equivalentes y no deben presentarse como si fueran variantes cercanas sin aclaración. C-ACERO-1 es un bound individual k≤C log p para cada primo; |C(N)|=O(log N) habla del número de auxiliares en un cover posiblemente con valores grandes. Una no implica automáticamente la otra sin restricciones adicionales sobre el universo de k usado en C(N).
- La frase “Una prueba de cualquiera de las dos implicaría Erdős-Straus para las clases duras” es verdadera solo si el k correspondiente efectivamente produce el split con enteros positivos para todo primo duro; para |C(N)|=O(log N), en su formulación finitaria por N, se necesita una versión uniforme infinita o una familia S(N) que cubra todos los p≤N para todo N. Debe formalizarse como proposición.
- La comparación con arXiv:2605.23601 no es suficiente para afirmar “domina estrictamente”. Dominar en cobertura sobre el mismo estrato solo significa que esta familia resuelve los 9 wild primes dentro de k≤127; no implica dominancia conceptual ni minimalidad frente a la familia tame/wild. Debe incluir lista de los 9 wild primes, certificados k,t para cada uno, y una definición común de universo de comparación.
- El claim de novedad está demasiado fuerte para el estado bibliográfico actual. El manuscrito debe comparar explícitamente con parametrizaciones por divisores, identidades de Mordell, trabajos de congruencias y cómputos previos; si no se encuentra “minimal auxiliary covering set”, debe decir “no conocemos antecedente exacto”, no “nuevo”.
- La sección de reproducibilidad no basta para un journal serio. “una máquina, minutos” y nombres de scripts no sustituyen artefactos verificables: commit hash, entorno, generador de primos, formato de certificado, hashes de CSV/JSON, tests unitarios para el lema algebraico, y verificador independiente mínimo.
## Objeciones menores

- El título promete “minimal auxiliary covering sets”, pero gran parte de la tabla son coberturas voraces o de muestras. Cambiar título o restringir claims.
- Usar una sola numeración: hay sección 3 y 3b/3c; en una nota formal conviene 3,4,5.
- La autoría ACERO/ledger/constitución distrae en el cuerpo matemático. Mover a acknowledgements o reproducibility appendix.
- “Schinzel's obstruction” debe enunciarse con precisión: qué tipo de identidad polinomial queda excluida y para cuáles clases.
- La frase “las seis clases duras clásicas” debe citar una fuente o explicar el criterio: clases p≡1 mod 4 no cubiertas por identidades conocidas módulo 840.
- En la definición de decisión, conviene exigir k positivo y coprimalidad/condiciones necesarias si se usan; si no son necesarias, decirlo.
- El símbolo C(N) para el conjunto mínimo y C para constante en C-ACERO-1 crea confusión.
- Los porcentajes deben incluir numerador/denominador y si son exactos o estimados.
- “monotonically increasing share” solo tiene valor descriptivo para los cinco cortes probados; no debe sugerir monotonicidad teórica.
- “C pequeña” debe omitirse o formularse como observación empírica dependiente de la base del logaritmo.
## Literatura faltante / a descartar

- Mordell: identidades/parametrizaciones clásicas para Erdős-Straus por clases de congruencia; citar edición/página exacta si se usa como base histórica.
- Schinzel: obstrucción a cubrir ciertas clases mediante identidades polinomiales; enunciar el resultado exacto y citar la fuente primaria o una exposición fiable.
- Swett y Salez: verificaciones computacionales de Erdős-Straus, en particular Salez 2014 hasta 10^17; dejar claro que esto cubre solubilidad bruta, no el objeto auxiliar minimal.
- Vaughan y Webb: resultados de densidad cero/excepciones para la conjetura; aclarar que son de naturaleza asintótica distinta.
- Elsholtz–Tao: conteo de soluciones/promedios para ecuaciones tipo Erdős-Straus; útil para contextualizar abundancia de representaciones frente a cobertura por una subfamilia.
- Elsholtz–Schinzel 2013 sobre divisibilidad en Erdős-Straus, si el manuscrito usa o roza criterios por divisores.
- Trabajos recientes por congruencias citados como arXiv:2404.01508, arXiv:2605.23601, arXiv:2606.10922: deben verificarse bibliográficamente, resumir teoremas relevantes y evitar depender solo de número arXiv.
- Literatura sobre set cover computacional/certificados de optimalidad, si se va a publicar minimalidad exacta de coberturas finitas.
## Chequeos sugeridos

- Probar algebraicamente el lema general: con x=(p+k)/4, k≡-p mod 4, t | (px)^2 y t≡-px mod k implican exactamente las fórmulas dadas para y,z y la identidad 4/p=1/x+1/y+1/z. Incluir también positividad e integridad.
- Para cada fila N≤10^7, ejecutar ILP exacto y publicar certificado de optimalidad: matriz primo-k, cover óptimo, y prueba de que no existe cover de tamaño |S|-1.
- Separar tres verificadores: generador de P(N), detector de decisión para un k, y verificador racional de certificados x,y,z. Idealmente uno en otro lenguaje o con librerías independientes.
- Recalcular k=23 como cobertura intrínseca: count({p: k=23 decide p}) por N, no “primero en orden”.
- Para 10^8 y 10^9, no reportar cover-size como mínimo. Reportar “cover encontrado en muestra estratificada” con metodología de muestreo, semilla, estratos, intervalos de confianza si se usan porcentajes, y una validación holdout.
- Auditar el criterio reducido de k=23 por tabla completa módulo 23: para cada r∈F_23^*, comprobar x≡6p, x^2≡13p^2, los objetivos 17p^2,17p,17, y los casos t=p/t=x. Esta prueba puede hacerse a mano en pocas líneas.
- Listar las clases mod lcm(840,23) que corresponden a los claims k=23 y verificar que contienen primos admisibles; evitar mezclar clases mod 23 con clases duras mod 840 sin CRT explícito.
- Para las nueve clases no-QR “llenas”, publicar conteos por clase mod 23 hasta 10^8 y el primer primo no cubierto si aparece en búsquedas mayores.
- Comparar con tame/wild: reproducir exactamente el estrato 24m+1, m≤30000; listar los 9 wild primes del otro trabajo y el k,t certificado por esta familia para cada uno.
- Hacer búsqueda de solapamiento bibliográfico por términos: “Erdos Straus divisor parameterization”, “Mordell type II”, “auxiliary congruence k”, “covering congruences”, “set cover” y los números arXiv citados.
## Dictamen de novedad

La reducción tipo II por divisor y la existencia de muchas soluciones en rangos computados son folclor/clásicas en espíritu; no deben venderse como novedad. Lo potencialmente nuevo es empaquetar una subfamilia fija como grafo de decisión primo-auxiliar, estudiar coberturas mínimas finitas y observar el papel anómalo de k=23 en las clases duras mod 840. El riesgo de solapamiento es moderado-alto con parametrizaciones por divisores y trabajos recientes de congruencias; el riesgo baja si el manuscrito reformula su aporte como dataset/certificación de set-cover restringido, con pruebas exactas solo para los lemas algebraicos y claims computacionales certificados.

---

*Este arbitraje es INTERNO (sistema autor). No sustituye la validación externa humana requerida por la constitución de ACERO.*
