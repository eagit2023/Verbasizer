# Estado del arte — herramientas de cut-up existentes

Relevamiento hecho en septiembre de 2026. La conclusión corta: **ninguna herramienta de
cut-up existente implementa peso por columna.** Lo más lejos que llega alguien es un
único slider global de proporción entre dos fuentes.

## Categoría A — cut-up simple

Todas hacen lo mismo: barajar.

| Herramienta | Controles reales | Estado |
|---|---|---|
| **Text Mixing Desk v3** (Lazarus Corp.) | Tamaño de trozo en palabras (default 6) + módulo "Echo Chamber". Orden de módulos fijo. | Activo, JS del lado cliente |
| **cutuptechnique.com** | Fuente única o múltiple, corte grueso/fino, formato de salida | Activo, propietario |
| **StickBucket** | "Chunkiness" 1-10, espacios aleatorios, búsqueda web como fuente | Activo |
| **Cut-Up Machine** (languageisavirus) | Ninguno. Pegar texto y botón. | Activo |
| **verbasizer.com** | 6 botones "Enable", cargar titulares o letras de Bowie, generar, copiar | Activo |
| **mikeatronic/Verbasizer** | — | .NET Core, 2 commits, abandonado |

El **Text Mixing Desk** es el único que documenta su algoritmo: parte el texto en un
array de trozos de N palabras y aplica **shuffle de Durstenfeld** (Fisher-Yates). Eso es
todo lo que hace la mayoría.

### enkiv2/verbasizer-verbalizer

El único open source con columnas de verdad. Script zsh:

1. Borra todo carácter que no sea alfanumérico o espacio
2. Reparte las palabras round-robin en N archivos (default 5) = las columnas
3. `shuf` sobre cada columna por separado
4. `paste` para recomponer en filas

Estructuralmente es lo más parecido al Verbasizer que existe publicado. Pero: sin pesos,
sin categoría gramatical, **destruye la puntuación**, y tiene un off-by-one — `{0..$cols}`
más el reset en `-gt $cols` genera N+1 columnas, no N. Sirve como prueba de concepto de
veinte líneas, no como base.

## Categoría B — los dos que aportan ideas

### Liptikl 2 (Intermorphic)

El más completo que existió. Discontinuado en 2017, sucedido por Wotja (comercial,
cerrado). macOS, Windows, iOS.

- **Cinco campos de fuentes** simultáneos.
- **Blend slider** — lo más cerca del peso que encontramos: *"Moving the slider to the
  left allows a greater proportion of words to be selected from the User Library and/or
  Liptikl Word Bank… Moving the slider to the right allows a greater proportion of words
  to be selected from your Sources."* Es un peso, pero **global y de dos vías**, no por
  columna.
- **Rules** — plantillas numéricas de estructura: cada número es la cantidad de palabras
  de una línea.
- **Lock de palabras** — se fija una palabra (se muestra en rojo) y no cambia al
  regenerar. **Es el "sifting and panning" convertido en interfaz, y es la mejor idea del
  relevamiento.**
- Reemplazo puntual de una palabra eligiendo entre alternativas en pantalla.
- Rima de fin de línea opcional. Word bank de 650+ palabras.
- El manual **no documenta el algoritmo**.

### WordPalette (Christopher Garver)

iPad/iPhone/Mac, gratis con compras internas. Última actualización septiembre de 2019,
v1.9.4. **Palettes** (pools de texto importado) que alimentan un teclado de hasta **seis
lanes deslizables independientes**, con frases agrupadas y escalonadas entre lanes.

Es el análogo de UX más cercano a las columnas del Verbasizer que existe hoy. El peso es
implícito: se controla combinando Palettes, no con un número.

## Categoría C — motores genéricos con pesos reales

No son cut-up, pero tienen la matemática.

**RiTa** (Daniel C. Howe) — toolkit open source **GPL**, Java y JavaScript, v3.0 en 2023.
Gramática libre de contexto probabilística con peso por alternativa
(`"start": "coffee[2] | bread | milk"`), más POS tagging, lexicón, flexión, sílabas,
rima y Markov.

**Descartado para este proyecto**: como el backend tiene que ser Python de todos modos
(por el castellano), spaCy cubre lo mismo con una dependencia menos. Ver
`docs/decisiones/ADR-0001-stack.md`.

`[no verificado]` Perchance (listas con odds) y JanusNode (reglas probabilísticas). No
pudimos verificar la sintaxis ni los detalles: la wiki de Perchance devolvió error 402 y
su tutorial no expuso contenido legible.

## El hueco

Nadie combina **columnas + peso explícito por columna + restricción gramatical por
columna + herramientas de curaduría del output**. Esa es la especificación del Verbasizer
de 1995 y sigue sin implementarse treinta años después.

El patrón en todo lo relevado: implementan el paso 7 de los ocho que reconstruimos —
apretar Randomize. El paso 8, la selección humana, queda tercerizado al copiar y pegar.

---

## Fuentes

- Text manipulation, Cut-up technique and related links — Lazarus Corporation
  <https://www.lazaruscorporation.co.uk/cutup/links>
- The Lazarus Corporation Text Mixing Desk
  <https://www.lazaruscorporation.co.uk/cutup/text-mixing-desk>
- Cut-Up Technique Generator <https://cutuptechnique.com/>
- The Ultimate Cut-Up Generator — StickBucket
  <https://stickbucket.com/cut-up-technique-generator/>
- The Cut-Up Machine — Language is a Virus
  <https://www.languageisavirus.com/cutupmachine.php>
- enkiv2/verbasizer-verbalizer <https://github.com/enkiv2/verbasizer-verbalizer>
- Liptikl 2: User Guide (archivado)
  <https://intermorphic.com/archive/tiklapp/liptikl/2/guide/>
- WordPalette <https://www.wordpalette.io/>
- RiTa — Tutorial: Grammars <https://rednoise.org/rita/tutorials/grammars.html>
- RiTa — Wikipedia <https://en.wikipedia.org/wiki/RiTa>
