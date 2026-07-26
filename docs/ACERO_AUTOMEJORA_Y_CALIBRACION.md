# ACERO — Auto-mejora segura y memoria de calibración

Cómo el programa **recuerda cómo se afinó cada dominio** y se **auto-ajusta tras cada
proceso**, sin romperse. Responde a: "que guarde memoria de sus calibraciones y se ajuste
solo; que sirva para nuevos rubros; que use un cron con Claude CLI para mejorar constante".

## El principio que lo hace seguro

> La auto-mejora ajusta **parámetros (datos), nunca código**, y **jamás** puede cruzar el
> **piso de especificidad**: cero falsos positivos en los controles nulos. La propiedad
> "no te engaña" no se negocia — un ajuste que produzca un falso positivo se **revierte**.

Esto es lo que evita que "mejorar" degenere en "empezar a inventar descubrimientos".

## Las piezas (`src/acero/portal/calibration.py`)

- **Knobs por dominio, acotados.** Hoy: `cross_check_rel_tol` (0.05–0.30). Astronomía puede
  necesitar otra tolerancia que genómica; cada dominio guarda la suya. No se filtra entre
  dominios.
- **Memoria ("retro").** Cada corrida del benchmark de recuperación se registra:
  sensibilidad, especificidad, falsos positivos, y la decisión tomada, con su razón.
- **`auto_tune` — un paso, reversible, registrado:**
  1. ¿Falso positivo en un nulo? → **ROLLBACK** hacia más estricto (especificidad sagrada).
  2. ¿Especificidad perfecta pero sensibilidad < 1 y hay margen? → **afloja** un paso para
     recuperar más positivos.
  3. Si ya está bien o no hay margen seguro → **no toca nada**.
- **`last_safe`**: guarda la última calibración probada sin falsos positivos, para revertir.

Validado con datos REALES (run-1/run-2 de astronomía): 0/3→ aflojó 0.15→0.18; 1/3 aún
perfecto → aflojó 0.18→0.21. Solo aflojó porque la especificidad se mantuvo.

## El loop (`recovery_bench.learn`)

```
correr benchmark del dominio → score → learn(dominio, resultados)
                                          ├─ record_benchmark (retro)
                                          └─ auto_tune (ajuste seguro)
```
El pipeline **lee la tolerancia calibrada por dominio** en el cross-check, así que el ajuste
tiene efecto real en la siguiente corrida.

## Onboarding de un dominio nuevo (p. ej. "filosofía" o genómica)

No es re-tuneo por estudio; es **dar de alta un campo una vez**:
1. **Controles con respuesta conocida** (3 positivos establecidos + 3 nulos espurios) en
   `recovery_bench.CONTROL_SET` con `domain="<campo>"`.
2. **Resolvedores de datos** del campo (si no existen, la corrida lo revela en el paso de
   datos — eso ES el diagnóstico de qué falta).
3. Correr el benchmark → `learn()` calibra ese dominio desde cero, con los mismos
   guardarraíles. (Un campo sin datos numéricos, como filosofía "pura", no es medible con
   este motor: el sistema lo reportará como "sin evidencia ejecutable", honestamente.)

## Cron + Claude CLI (auto-mejora constante)

El provider `claude` ya existe (`ACERO_LLM_PROVIDER=claude`), separado de Codex para no
mezclar agentes. Un cron seguro:

```cron
# cada noche: re-calibra un dominio y registra el retro (NO toca código)
30 3 * * *  cd /ruta/Proyecto\ Acero && ACERO_LLM_PROVIDER=claude \
            ./.venv/bin/python scripts/recovery_selfimprove.py chemistry >> research/selfimprove.log 2>&1
```

**Reglas para que la auto-mejora ayude sin romper:**
- Solo corre el **driver acotado** (benchmark→learn); no deja que un agente reescriba código.
- Un cambio se **acepta solo si no baja la especificidad**; si baja, rollback automático.
- Todo queda en el **retro** (auditable) y es **reversible**.
- Si quisieras un agente Claude que proponga *cambios de código*, que abra un **PR para
  revisión humana**, nunca auto-merge. El techo sigue siendo el humano.

## Estado

- Memoria + auto-tune + guardarraíles: **hecho y probado** (6 tests + demo con datos reales).
- Provider Claude CLI: **hecho** (tests offline; validación en vivo fuera de una sesión
  Claude Code anidada).
- Generalización a un 2º dominio (química): **en corrida** — siembra la memoria de ese campo
  y prueba si el motor generaliza fuera de astronomía.
