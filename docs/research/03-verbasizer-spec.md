# El Verbasizer (1994-95) — reconstrucción funcional

## Qué fue

Software a medida que **Ty Roberts** construyó para **David Bowie**, usado durante las
sesiones del álbum *1. Outside* (grabado 1994-95, editado en septiembre de 1995).
Corría en una laptop Mac. Automatizaba el método de cut-up que Bowie venía haciendo a
mano con tijeras desde *Diamond Dogs* (1974).

Roberts había fundado Ion (Ion Music) entre 1992 y 1994, produciendo CD-ROMs
interactivos para músicos, entre ellos Bowie y Brian Eno. Lo invitaron al estudio en
Inglaterra y ahí propuso automatizar el proceso. `[documentado]`

## Estado del software original

- **Nunca se publicó ni se comercializó.** Fue una herramienta interna. `[documentado]`
- **No hay binario, código fuente ni imagen de disco en circulación.** `[documentado]`
- El archivo del V&A (David Bowie Centre, abierto en septiembre de 2025, más de 90.000
  piezas) describe públicamente vestuario, instrumentos, cuadernos, letras,
  correspondencia y fotografías. **No menciona computadoras ni software.** `[documentado]`
- Existió una **Verbasizer 2.0** que el equipo de I+D de Gracenote recreó para la muestra
  *David Bowie Is* (V&A, marzo-agosto 2013). Esa versión tomaba news feeds y generaba
  letras automáticamente. Tampoco está publicada. `[documentado]`

**La mejor fuente primaria accesible es un video:** en el documental *Inspirations*
(1997, dir. Michael Apted) Bowie opera el programa en cámara. Es el único registro
visual de la interfaz real.

## El flujo, paso a paso

### 1. Entrada
El usuario carga palabras y frases. Roberts menciona "distintos métodos de entrada,
incluyendo simplemente tipear palabras". La materia prima de Bowie eran textos propios,
diarios y recortes. `[documentado]`

### 2. Reparto en columnas
Cada frase se distribuye entre columnas.

> "It'll take the sentence, and I'll divide it up between the columns."
> — Bowie, *Inspirations* (1997) `[documentado]`

### 3. Restricción gramatical por columna
Las columnas podían restringirse a categorías gramaticales.

> Las columnas *"could be restricted to nouns, verbs, adjectives, etc."*
> — Ty Roberts, entrevista con Hypebot (2013) `[documentado]`

**`[supuesto]`** Que la declaración de categoría era **manual** por columna, no
etiquetado automático. Fundamento: en 1994-95, sobre una laptop Mac y sin recursos de
NLP accesibles, el etiquetado automático de calidad no era viable. Es inferencia
razonable, no dato.

### 4. Peso por columna
> *"Each column could be weighted."* — Ty Roberts (2013) `[documentado]`

**`[desconocido]`** Qué significaba el peso. Las lecturas posibles son al menos tres:
probabilidad de que esa columna aporte la siguiente palabra; frecuencia de aparición en
el resultado; o largo del fragmento que aporta. Ninguna fuente lo aclara. Es un hueco a
decidir, no a reconstruir. Ver `docs/decisiones/ADR-0002-motor.md`.

### 5. Múltiples palabras por columna
> *"…and have multiple words if desired."* — Ty Roberts (2013) `[documentado]`

### 6. Escala
Entre 3 y 25 frases simultáneas.

> "Three or four or five — sometimes I'll go as much as 20, 25 different sentences
> going across here." — Bowie, *Inspirations* `[documentado]`

### 7. Randomize
Un botón. Toma palabras de **distintas columnas y distintas filas a la vez**, cruzando
frases.

> "Picking out, choosing different words from different columns." `[documentado]`

> "What you end up with is a real kaleidoscope of meanings and topic and nouns and verbs
> all sort of slamming into each other." — Bowie `[documentado]`

### 8. Filtrado humano
El paso que define todo el método. Bowie leía el resultado y elegía.

> "The choices that I now make from this form, I can then reimbue it with an emotive
> form if I want to." `[documentado]`

> "The key is there is something new and fresh and unexpected to respond to." `[documentado]`

Es el mismo *"sifting and panning"* que Burroughs describía para el cut-up manual.

## Huecos: lo que nadie sabe

| Pregunta | Estado |
|---|---|
| Lenguaje y framework (HyperCard, Director, C, otro) | `[desconocido]` |
| Unidad atómica: ¿palabra suelta o sintagma? | `[desconocido]` |
| Matemática exacta del peso | `[desconocido]` |
| Etiquetado gramatical: ¿manual o automático? | `[supuesto]` manual |
| ¿Preservaba estructura sintáctica? | `[desconocido]` |
| ¿Cuántas líneas generaba por pulsación? ¿Había historial? | `[desconocido]` |

Todo esto lo **decidimos nosotros** y queda registrado como decisión de diseño, no como
reconstrucción.

## Errores que circulan

Fuentes secundarias con datos verificablemente falsos, anotados para no propagarlos:

- Se afirma que el output del Verbasizer alimentó *Low*, *"Heroes"* y *Lodger*.
  **Imposible:** la trilogía de Berlín es de 1977-79 y el software es de mediados de los
  90. En esa época Bowie usaba cut-up manual.
- Las fechas oscilan entre "early 1990s" y "1995". Lo consistente con las sesiones de
  *Outside* es **1994-95**; 1997 es solo la fecha del documental.
- El artículo de Vice, que es el más citado, **no contiene ninguna cita directa de
  Roberts**: todo lo que le atribuye viene del artículo de Hypebot de 2013. Es una única
  fuente reciclada muchas veces.

## Vías abiertas

1. **El video de *Inspirations***, cuadro por cuadro: muestra la interfaz real.
2. **Ty Roberts.** Sigue activo en la industria. Dio una sola entrevista sustancial sobre
   esto, en 2013, y nadie parece haberle vuelto a preguntar. Es la única persona que
   puede llenar los huecos de la tabla de arriba.
3. **Consulta formal al archivo del V&A**, para saber si la colección incluye soportes
   digitales de los 90.

Si alguna de estas devuelve información, se asienta acá y se actualizan las marcas.

---

## Fuentes

- Ty Roberts: From Working With David Bowie To Co-Founding Gracenote — Hypebot, 2013
  <https://www.hypebot.com/hypebot/2013/03/ty-roberts-on-the-trail-from-working-with-david-bowie-to-co-founding-gracenote.html>
- Versión ampliada de la misma entrevista — All About Jazz
  <https://www.allaboutjazz.com/news/ty-roberts-from-working-with-david-bowie-to-co-founding-gracenote/>
- The Verbasizer was David Bowie's 1995 Lyric-Writing Mac App — Vice
  <https://www.vice.com/en/article/the-verbasizer-was-david-bowies-1995-lyric-writing-mac-app/>
- Other tools: more about Verbasizer — Gnoetry Daily
  <https://gnoetrydaily.wordpress.com/2010/09/15/other-tools-more-about-verbasizer/>
- Bowie demostrando el Verbasizer (*Inspirations*, 1997)
  <https://www.youtube.com/watch?v=x3IKLMgFaDA>
- 5 things to know about the David Bowie Centre — V&A
  <https://www.vam.ac.uk/blog/museum-life/5-things-to-know-about-the-david-bowie-centre>
