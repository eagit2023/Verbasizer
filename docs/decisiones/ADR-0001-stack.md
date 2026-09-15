# ADR-0001 — Stack y licencia

**Fecha:** 2026-09-15
**Estado:** aceptada

## Contexto

Tres definiciones de partida:

1. El proyecto se publica como **open source público**.
2. Tiene que procesar texto en **castellano e inglés**.
3. La plataforma es **web con backend**.

La restricción gramatical por columna (punto 3 de la especificación del Verbasizer)
requiere etiquetado morfosintáctico en ambos idiomas. Eso es lo que define el stack.

## Licencias verificadas

| Componente | Licencia | Entrenado sobre |
|---|---|---|
| `en_core_web_sm` (inglés) | **MIT** | OntoNotes 5, ClearNLP, WordNet 3.0 |
| `es_core_news_sm` (castellano) | **GPL-3.0** | UD Spanish AnCora v2.8, WikiNER, spaCy lookups |
| UD_Spanish-AnCora (treebank) | CC BY 4.0 | — |
| UD_Spanish-GSD (alternativo) | CC BY-SA 4.0 | 16.013 oraciones |

`[no resuelto]` El treebank AnCora figura como CC BY 4.0 en Universal Dependencies, pero
el modelo español que distribuye spaCy está publicado como GPL-3.0. No pudimos determinar
qué componente arrastra la GPL — probablemente WikiNER o los lookups. Si en algún momento
se necesitara licencia permisiva, hay que investigarlo a fondo.

## Decisión

**Licencia del proyecto: GPL-3.0.** El modelo de castellano es GPL y usarlo obliga a
serlo. Como el destino ya es open source público, no hay conflicto.

**Etiquetado: spaCy.** Cubre los dos idiomas con una sola dependencia.

**RiTa queda descartado.** Resolvía pesos y POS, pero el backend tiene que ser Python de
todos modos por el castellano, y spaCy hace lo mismo. Una dependencia menos, y la
matemática de los pesos la escribimos nosotros: son veinte líneas.

`[no verificado]` Alternativa permisiva existente: Stanza (librería Apache 2.0, modelos
bajo Open Data Commons). Leído en el planteo de un issue, sin confirmación de los
mantenedores.

## Arquitectura

- **Motor**: Python puro, sin dependencias, determinístico dado un seed. No conoce HTTP.
  Separado para poder testearlo y para servir también como CLI.
- **Backend**: FastAPI. Expone el motor y hace el etiquetado.
- **Frontend**: JavaScript sin build step, sin framework.
- **Persistencia**: archivos JSON, una sesión por archivo. Sin base de datos.

### Sobre el frontend sin framework

Es una decisión de longevidad, no de simplicidad. Este es un proyecto sobre preservación
de software y el relevamiento del estado del arte está lleno de herramientas abandonadas
que ya no corren. Un bundle armado en 2026 no compila en 2031; un HTML que se abre y
anda, sí.

### Consecuencia no obvia

**El etiquetado gramatical ocurre una sola vez, al cargar cada fuente. Generar es
matemática pura.** Entonces el backend solo hace falta al ingerir textos: una vez
etiquetada la sesión, columnas, pesos, generación y curaduría corren en el navegador sin
servidor.

Eso permite dos entregables desde la misma base de código: la aplicación empaquetada
(completa) y una versión web pura que funciona con sesiones ya etiquetadas o sin
restricción gramatical.

## Empaquetado

PyInstaller + pywebview. **Solo Apple Silicon por ahora**, sin build de Windows.
Compilación desde GitHub Actions, disparada por tags de versión.

- Tamaño estimado: **150-300 MB**. `[supuesto]` Los modelos son la parte chica
  (`es_core_news_sm` pesa 12,9 MB); el bulto es Python + numpy + thinc.
- **Riesgo conocido:** hay un caso documentado donde bundlear spaCy con PyInstaller trepó
  de 40 MB a 1,8 GB por arrastrar PyTorch y las DLLs de Intel MKL. Es un issue de 2019
  sobre spaCy 2.x, pero el arrastre de dependencias hay que controlarlo explícitamente en
  la configuración del build.
- Sin firma de código, macOS muestra la advertencia de desarrollador no identificado. Se
  documenta el rodeo en el README; notarizar cuesta 99 USD por año y no se justifica hoy.

El empaquetado es la última fase. Hacerlo antes significa pelear con PyInstaller en cada
cambio sin que aporte nada mientras el motor está en discusión.

## Fuentes

- <https://huggingface.co/spacy/es_core_news_sm>
- <https://huggingface.co/spacy/en_core_web_sm>
- <https://universaldependencies.org/treebanks/es_ancora/index.html>
- <https://universaldependencies.org/treebanks/es_gsd/index.html>
- <https://github.com/explosion/spaCy/issues/4548>
