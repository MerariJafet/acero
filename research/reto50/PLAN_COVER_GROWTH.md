# PLAN — Ley de crecimiento de cover(N) con el criterio FUERTE

**Premisa sellada (jerarquía, nunca perderla):**
- **PORQUÉ (irrenunciable):** construir una **llave dinámica** k(p): una fórmula que
  dé la llave en función de la puerta e incorpore el patrón de crecimiento, con la
  **razón** de ese crecimiento explicada.
- **MEDIO:** medir cómo crece `cover(N)` = tamaño mínimo del llavero que abre todas
  las puertas (primos duros) hasta N.
- **DEFINICIÓN OPERATIVA EXACTA (no negociable):** la llave `k` abre la puerta `p`
  ⟺ `p+k ≡ 0 (mod 4)` (buena formación, x=(p+k)/4 entero) **Y** existe un divisor
  `t | (p·x)²` con `t ≡ −p·x (mod k)`. La condición mod 4 sola NO es abrir —
  es solo meter la llave en la cerradura. (La Ronda 4 se perdió exactamente aquí.)

**Puertas (primos duros):** p primo ≤ N con p mod 840 ∈ {1,121,169,289,361,529}
(los residuos cuadráticos que sobreviven el filtro clásico — paridad ya lograda).

**Llavero candidato:** k impar, gcd(k,840)=1, k ≤ 240.

## Fases

| Fase | N | Método | Estado |
|---|---|---|---|
| A | 10⁵ → 10⁸ (hitos 1,2,5×10ᵐ) | incidencia exacta + cover greedy y EXACTO (B&B sobre firmas) | script `cover_growth.py`, corre en background |
| B | 2×10⁸ → 10⁹ | misma incidencia, continúa incremental | encadenada en la misma corrida |
| C | 10¹⁰–10¹² | **muestreo estratificado** por bandas (no exhaustivo): estimar la tasa de aparición de puertas que exigen llave nueva; intervalos de confianza, jamás "cover exacto" | tras validar A/B |

## Salidas
- `cover_growth.json` — `{"rows": [{"N":…, "n_hard":…, "cover_greedy":…,
  "cover_exact":…, "keys_exact": […], "elapsed_s":…}, …]}` → dataset directo para
  **Mendeleev** (ley de crecimiento) y para la búsqueda simbólica de **k(p)**.
- `cover_growth.log` — bitácora con checkpoints (reanudable).

## Validación crítica (la reconciliación que la Ronda 3 nunca hizo)
En 10⁵/10⁶/10⁷ comparar contra los puntos externos (5, 8, 10). Si difieren, eso es
un DATO: las definiciones difieren — se documenta, no se maquilla.

## Nota de honestidad
`cover_exact` es exacto **respecto del llavero candidato k ≤ 240**: una llave óptima
mayor que 240 no se vería. El límite queda declarado en cada fila.
