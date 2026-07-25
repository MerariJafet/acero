# Estudio 2 — Intento de réplica independiente (PAMPA) del hallazgo Caco-2

Objetivo: cerrar el hecho #4 del revisor (replicación en fuente independiente) para el
efecto "mayor polaridad molecular → menor permeabilidad".

## Resultado real
| Dataset | Ensayo | n | Medición | Efecto | Estadístico | Dirección |
|---|---|---:|---|---|---|---|
| caco2_wang | Caco-2 (célula) | 910 | logPapp continuo | +0.754 | t=16.3 | menos polar → más permeable |
| pampa_ncats | PAMPA (membrana artificial) | 2035 | permeable/no (binario) | +0.111 | z=6.92 | menos polar → más permeable |

**La dirección se sostiene** en un ensayo físicamente distinto, con otra medición y otra
cohorte (2035 moléculas nuevas). Es evidencia de robustez del efecto.

## Pero el IndependenceGraph lo degrada — y hace bien
```
caco2_wang vs pampa_ncats → SAME_STUDY
comparten: raíz de procedencia (TDC), pipeline de curación
difieren: assay/fuente, laboratorio, cohorte, instrumento
¿replicación-capaz?: False
```
Aunque el ensayo es distinto, **ambos datasets provienen del mismo ecosistema de curación
(TDC)**. El grafo se niega a llamarlo "replicación independiente" por compartir raíz de
procedencia. Estado: NO alcanza `REPLICADO_EN_DATASET_INDEPENDIENTE`.

## Conclusión honesta
El sistema funcionó como debe: registró que el efecto es **robusto entre ensayos** pero
**no lo sobrevendió como replicación independiente**. Cerrar el hecho #4 de verdad exige
una fuente de permeabilidad con **raíz de curación distinta a TDC** (p. ej. ChEMBL crudo,
o un dataset primario de literatura). Eso NO es un problema de volumen ni de almacenamiento
—descargamos 2945 moléculas sin fricción— sino de **descubrimiento y armonización de una
fuente genuinamente independiente**.

Reproducible: `scripts/study_pampa_replication.py`.
