# ACERO — Cómo funciona la investigación (y el rol real de Hipatia)

Merari planteó la pregunta correcta: *"¿Esto sirve solo para confirmar lo ya confirmado
porque lee papers? Lo nuevo lo confirmaría un experimento. ¿Es así como funciona? ¿Falta
algo? No quiero que todo se reduzca a buscar papers."* Aquí está el modelo honesto.

## Dos preguntas DISTINTAS sobre cualquier resultado

No hay que confundirlas — son ejes independientes:

1. **¿Es NUEVO?** → **novedad** (Hipatia, literatura). Es una **PUERTA**, no una
   confirmación. Contesta "¿alguien ya lo hizo?", nunca "¿es verdad?".
2. **¿Es VERDAD / está justificado?** → **evidencia**. Esto NO lo dan los papers; lo dan
   la prueba o el experimento (abajo).

Un resultado publicable = **NUEVO** (Hipatia: likely_open) **+ JUSTIFICADO** (prueba o
experimento). Las dos cosas, no una.

## Las 3 formas de JUSTIFICAR (confirmar) algo

| Tipo | Qué es | Quién lo hace en ACERO | Qué da |
|------|--------|------------------------|--------|
| **Prueba deductiva** | argumento lógico verificable | 📐 Euclides (sympy: álgebra/análisis) · 🔭 futuro Gödel (asistente tipo Lean: también combinatoria) · humano | **certeza** dentro de los axiomas |
| **Experimento matemático / con datos** | verificación exhaustiva, simulación, análisis de datos, cruce | 🎨 Da Vinci + ❌ Popper (con nuestro cómputo, sandbox) | **soporte empírico fuerte**, NO certeza (`holds_empirically`) |
| **Experimento físico** | laboratorio, mediciones | ACERO lo **diseña** y analiza datos; no tiene laboratorio propio | evidencia empírica del mundo real |

**Tenías razón en todo:**
- Leer papers (Hipatia) solo dice si algo **ya se sabe** — nunca confirma algo nuevo.
- Para confirmar algo **NUEVO** necesitas **prueba** o **experimento**.
- Si es **matemático con datos** → lo hacemos nosotros con nuestro cómputo.
- Si es **físico** → queda como **tesis teórica esperando comprobación** (o diseñamos el
  experimento para que alguien lo corra).

## ¿Ambos caminos son válidos en ciencia? Sí

- Un paper de **matemática pura** = una **prueba** (argumento lógico). Válido.
- Un paper **empírico** = **evidencia experimental** reproducible. Válido.
- Muchos combinan ambos. Los dos son contribuciones legítimas.

## Lo que FALTA en el modelo (para completarlo honestamente)

1. **La confirmación es por GRADOS, no binaria:**
   `probado` (prueba) > `evidencia empírica fuerte` (conjetura bien soportada) >
   `propuesta teórica sin comprobar`. Un resultado nuevo con solo evidencia computacional
   es una **conjetura bien soportada**, NO un teorema, hasta que se pruebe o se replique.
2. **Revisión por pares / validación externa** (🏅 Gauss): ni la prueba ni el experimento
   "confirman" solos hasta que **otros humanos** los verifican y **reproducen**. Por eso
   el techo de ACERO es *"listo para revisión científica humana"*, nunca "descubrimiento
   confirmado".
3. **Reproducibilidad**: el experimento/prueba debe poder rehacerlo un tercero (paquete de
   verificación).
4. **Falsabilidad** (❌ Popper): una buena hipótesis debe poder ser refutada; si nada
   podría refutarla, no es ciencia.

## El rol REAL de Hipatia (no colapsar todo a "buscar papers")

Hipatia es una **PUERTA en dos momentos**, jamás la que confirma:

- **AL INICIO** — "¿ya está resuelto?" → si sí, no gastamos cómputo (anti-Erdősgate); si
  `likely_open`, **seguimos a confirmarlo nosotros**.
- **AL FINAL** — posicionar el resultado frente a la literatura: ¿cuál es el **delta**
  exacto vs lo previo? (la sección "trabajo relacionado" del paper).

Entre esos dos momentos, **la CONFIRMACIÓN de algo nuevo NO es de Hipatia** — es de
📐 Euclides/Gödel (prueba) o de 🎨 Da Vinci + ❌ Popper (experimento/datos con cómputo).
Así **no** volvemos a "solo validar lo ya corroborado": Hipatia nos dice qué es realmente
nuevo **para entonces confirmarlo con experimento o prueba**.

## El flujo completo de una contribución NUEVA

```
🏛️ Hilbert plantea  →  🔎 Hipatia (¿nuevo? likely_open)  →  CONFIRMAR:
        ├─ camino PRUEBA:      📐 Euclides (sympy) / 🔭 Gödel (Lean) / humano
        └─ camino EXPERIMENTO: 🎨 Da Vinci + ❌ Popper (cómputo/datos)  ó  diseño físico
   →  🔎 Hipatia otra vez (posicionar: delta vs literatura)
   →  🏅 Gauss (empaqueta, validación externa)  →  revisión científica humana
```

Dos tipos de entregable, ambos válidos:
- **Tesis con prueba** (argumento lógico cerrado) → si es matemática, puede quedar
  `verified`/`formally_supported`.
- **Tesis con respaldo experimental** (datos/cómputo) → `holds_empirically` + paquete
  reproducible; conjetura fuerte esperando prueba o réplica.

## ¿Quién tiene el poder de sympy? ¿Y el "Lean"?

- **📐 Euclides** = `formal_verify.py` (sympy). Prueba **álgebra y análisis** (identidades,
  desigualdades, sumatorias, límites). Su límite: **no** expresa argumentos de conteo/
  combinatoria (por eso la conjetura B quedó en revisión humana).
- **🔭 Gödel** (nuevo fichaje propuesto) = un **asistente de pruebas tipo Lean**, detrás
  de la MISMA interfaz `verify()` (ya está diseñada para enchufar otro backend). Podría
  **mecanizar pruebas** que sympy no alcanza (combinatoria, inducción estructural). Es un
  build pesado (instalar Lean + mathlib + capa de traducción); se decide aparte.
