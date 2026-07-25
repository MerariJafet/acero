# Caso científico ACERO — ¿La metalicidad estelar esculpe el valle de radios?

**Corrida end-to-end real con Codex + datos públicos (NASA Exoplanet Archive).**
Proyecto: `Valle de radios: metalicidad como discriminador`. Dominio: astronomía.
Fecha: 2026-07-25. Techo por diseño: candidato para revisión humana. **El LLM nunca
es evidencia**: las cifras salen de código ejecutado sobre datos reales descargados.

> **Veredicto final: `RESULTADO_INCONCLUSO`.**
> Estado en la escalera científica: **2 / EVIDENCIA_PRELIMINAR** (no alcanza el 3,
> «exploratorio robusto», porque un control placebo iguala la señal y la verificación
> cruzada independiente discrepó). Nada aquí es un descubrimiento.

---

## 1. Pregunta seleccionada y por qué importa

¿La ubicación del **valle de radios** de planetas pequeños (super-Tierras vs
sub-Neptunos) depende de la **metalicidad [Fe/H]** de la estrella anfitriona, y esa
dependencia **distingue fotoevaporación de pérdida de masa impulsada por el núcleo
(core-powered)**?

Importa porque es un debate abierto y activo (2022–2024): ambos mecanismos predicen un
valle, pero difieren en su dependencia de la química estelar. Es falsable, abordable con
datos públicos (Kepler/Gaia) y discrimina teorías rivales — no es una relación ya
establecida.

## 2. Hipótesis rivales (generadas por ACERO/Codex, no por plantilla)

- **H0** — el valle se desplaza con [Fe/H] **sólo tras condicionar por insolación**, no en el plano radio-periodo bruto (efecto condicional, consciente de confusión).
- **H1** — en estrellas metal-ricas el valle **se ensancha, no se desplaza** (mezcla de composiciones de núcleo).
- **H2** — la dependencia con [Fe/H] **invierte signo** entre estrellas frías y solares.
- **H3** — la metalicidad **sólo importa en sistemas multi-planeta** (firma de formación, no de escape).
- **H4** — a [Fe/H] bajo el valle conserva sub-Neptunos que core-powered no debería.
- **H5 (nulo/control)** — la señal de [Fe/H] es una **ilusión de sistemáticos de radios estelares Gaia**: el valle se mueve con el error, no con la química.

## 3. Prueba que las distingue

Motor epistémico: **18 vulnerabilidades** sobre 6 claims; prueba discriminante
**decisiva, 2.0 bits, separa 4** de las 6 rivales. El eje discriminante: ¿sobrevive el
coeficiente de [Fe/H] al condicionar por insolación **y** a un control de radios
estelares latentes/sistemáticos Gaia, frente a un nulo de permutación y un placebo?

## 4. Datos y procedencia

- **NASA Exoplanet Archive** vía TAP: `pscomppars` (Confirmed Planets), `q1_q17_dr25_koi` (Kepler DR25), `stellarhosts` (parámetros estelares).
- 20 papers reales con DOI (Crossref) indexados como literatura (novedad verificada).
- **Independencia alcanzada: Nivel 1 (una sola raíz de procedencia).** `pscomppars` y
  DR25 comparten la raíz NASA/Gaia → **no** cuentan como replicación (el sistema no la
  declaró). `find-replication` señala que una fuente independiente real requeriría
  TESS/K2 o CKS (Keck/HIRES) de otra raíz.

## 5. Protocolo (y por qué NO se congeló uno confirmatorio)

El régimen fue **exploratorio**. La constitución **impide avanzar** al estado 4
(PROTOCOLO_CONFIRMATORIO_CONGELADO) sin pasar antes por el 3 (exploratorio robusto).
Como la señal exploratoria **no** fue robusta, **congelar un protocolo confirmatorio y
sellar un holdout habría sido prematuro** — exactamente la mala práctica que ACERO evita.
El pipeline se detuvo, correctamente, antes de la confirmación.

## 6. Resultados y análisis de sensibilidad (8 experimentos, datos reales)

| Experimento (hip.) | Veredicto | Cifra clave |
|---|---|---|
| Modelo jerárquico radio–insolación–[Fe/H] (H0) | inconclusive | period_feh=**0.044** > nulo p95=0.012 (asociación débil en muestra) pero cv_delta=**0.0035** (sin ganancia fuera de muestra); local_bins=3 |
| Valle Kepler DR25 con completitud (H0) | inconclusive | cross-match KOI↔stellarhosts colapsó: match=**0.56%**, sólo **3 planetas** pasan cortes (se necesitan 54); nulo no corrido |
| Catálogo sintético con sesgos de detección (H0) | inconclusive | 160 MC; no separó limpio confusión vs señal |
| pscomppars vs DR25 (sistemáticos) (H5) | inconclusive | corr(radio,[Fe/H]) DR25=**0.240** vs pscomppars=0.025; bins insuficientes |
| Inyección de sesgo de radio ~[Fe/H] (H5) | inconclusive | nulo **pasa**, pero mejor inyección 0.123 **no reproduce** el 0.240 observado → *debilita* el puro artefacto |
| Modelo jerárquico químico vs Gaia (H5) | **refutes** | AIC_combinado **−4409** < AIC_gaia −4283 < AIC_químico −4136 < AIC_nulo −4075: el término [Fe/H] mejora predicción OOS por encima del nulo aun controlando radio latente |
| Prueba placebo (H5) | inconclusive | placebo `sy_kepmag` mejora **0.050 ≥** [Fe/H] 0.047 → la señal podría ser brillo/selección |
| Prueba falsable 3 modelos (H0) | **degradado por ACERO** | verificación cruzada con implementación independiente **discrepó** (supports vs inconclusive) → no se cuenta |

**Sensibilidad:** la única señal a favor (modelo químico OOS) queda **socavada** por (a) un
placebo de magnitud que la iguala y (b) la verificación cruzada que no coincidió. La
señal no es estable a cambios de muestra/implementación.

## 7. Críticas no resueltas (panel adversarial, 38 críticas)

- **Sobreafirmación** en ambos dossiers: «que el valle cambie al perturbar radios
  estelares no prueba que [Fe/H] sea ilusorio» (H5); «puede estar sobredimensionada si
  sólo se comparó radio-periodo vs radio-insolación» (H0).
- Muestra insuficiente tras cortes reproducibles (el cuello real del problema).
- Confusión brillo/selección no descartada (placebo positivo).
- Discrepancia entre implementaciones en la prueba falsable clave.

## 8. Nivel de independencia alcanzado

**Nivel 1** — una sola raíz de procedencia (NASA Exoplanet Archive / Gaia). No hay
replicación ni reproducción por implementación independiente (de hecho, la cruzada
*falló*). Un split del mismo dataset **no** contaría; el sistema no lo declaró.

## 9. Afirmación máxima permitida (claim compiler)

> «En datos del NASA Exoplanet Archive existe **a lo sumo una asociación débil y no
> robusta** entre [Fe/H] y la posición del valle de radios, que **no sobrevive** un
> control placebo (magnitud Kepler) ni la verificación cruzada con una implementación
> independiente. La evidencia **no distingue** fotoevaporación de core-powered.»

Prohibido: «predice», «efecto causal», «confirmado», «replicado», «demuestra».

## 10. Siguiente experimento necesario

Traer una **fuente de raíz independiente** (CKS spectroscópico [Fe/H] de Keck/HIRES, o
radios TESS/K2) y, **antes de mirarla**, preregistrar un protocolo con: estimando =
pendiente de la posición del valle vs [Fe/H] condicionada a insolación y masa estelar;
DAG con [Fe/H]→(composición, radio estelar), radio_estelar→radio_planeta_medido (sesgo),
insolación como confusor; nulo = permutación de [Fe/H] estratificada por Teff/masa/año de
descubrimiento; **placebo obligatorio** = magnitud Kepler; regla de decisión y tamaño
mínimo (≥54 planetas por bin) fijados de antemano. Sólo entonces tendría sentido un
holdout sellado.

---

*Producido por ACERO conduciendo su propio pipeline (tema→hipótesis→EVA→discriminante→
experimentos con datos reales→síntesis→rigor→dossier). Los dossiers quedan en estado
BORRADOR_AUTOMATICO — requiere revisión humana. El techo es un humano; nada es un
descubrimiento.*
