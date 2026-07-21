# Hubble Tension — Análisis Computacional ACERO
## Proyecto: Posición de la Tierra en el Universo

**Fecha:** 2026-07-19
**Dataset:** 46 mediciones de H0 (2003-2025), 4 categorías, 15+ métodos
**Herramienta:** ACERO v2.1 + scipy + numpy + pandas

---

## Hallazgos principales

### 1. La tensión es REAL y ESTADÍSTICAMENTE ROBUSTA
- Distance ladder: H0 = 72.82 ± 0.39 km/s/Mpc (pesado)
- CMB/BAO: H0 = 68.38 ± 0.44 km/s/Mpc (pesado)
- Diferencia: 4.45 km/s/Mpc (~4.2σ)
- Evidencia bayesiana FUERTE de que son 2 poblaciones (ΔBIC = 32.2)

### 2. Existe un gradiente con redshift (p=0.005)
- Métodos locales (z~0.05) → H0 alto (~73)
- Métodos intermedios (z~0.3-5) → H0 intermedio (~69)
- CMB (z=1100) → H0 bajo (~67.4)
- Esto sugiere: o el universo se expande a ritmos diferentes a distintas épocas, o hay un sesgo sistemático que crece con la distancia.

### 3. El vacío KBC puede explicar ~60% de la tensión
- Corrección teórica si δρ/ρ = -0.3: +3.5 km/s/Mpc
- Tensión residual después de corrección: ~2.2 km/s/Mpc (~2σ)
- Si el vacío es más profundo (δ=-0.5), podría explicar ~100%

### 4. Lee 2024 (JAGB) es un outlier BAJO en distance ladder
- H0 = 67.8 (a -3.3σ del grupo)
- Sugiere que la calibración JAGB da resultados diferentes a Cefeidas
- Si JAGB es correcto, gran parte de la tensión podría ser sistemático de Cefeidas

### 5. Gravitational lensing no resuelve nada (aún)
- Dispersión interna (std=5.23) mayor que la tensión misma (4.45)
- Se necesitan más mediciones de mayor precisión

---

## Hipótesis falsables

| ID | Hipótesis | Estado |
|---|---|---|
| H1 | Sesgo de calibración Cefeidas | PARCIALMENTE SOPORTADA |
| H2 | Vacío KBC sesga H0 local | PLAUSIBLE (~60%) |
| H3 | Early Dark Energy | ACTIVA |
| H4 | La tensión no es real | PARCIALMENTE REFUTADA |
| H5 | Dark radiation / neutrino estéril | TENSIÓN CON DATOS |

---

## Líneas de investigación recomendadas

1. **Modelar el efecto KBC cuantitativamente** con datos de galaxy surveys (2dFGRS, SDSS)
2. **Comparar JAGB vs Cefeidas** como calibradores — meta-análisis
3. **Esperar DESI DR3** — si confirma w(z) ≠ -1, soporta H3
4. **Análisis de manchas solares** como proxy para entender periodicidades en datos astronómicos
5. **Gravitational waves (LISA)**: futuras sirenas estándar darán H0 independiente

---

## Datos y reproducibilidad

- CSV: research/datasets/hubble_tension_h0_measurements.csv
- Script: research/datasets/hubble_tension_analysis.py
- Fuentes: arXiv:2601.00650v2, arXiv:2408.11031, Planck 2018, SH0ES 2022, DESI 2024
