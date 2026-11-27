# ADR-0003 — Aplicación de escritorio, sin servidor

**Fecha:** 2026-11-26
**Estado:** aceptada. Reemplaza las secciones *Arquitectura* (backend) y
*Empaquetado* de ADR-0001.

## Contexto

La primera arquitectura era web con backend: una API en FastAPI que etiquetaba con
spaCy y una interfaz en el navegador. Se llegó a preparar un despliegue en
contenedor para alojarla en un servidor.

La definición cambió: **la herramienta tiene que correr local, en macOS (Apple
Silicon) y Windows 11, sin usar ningún servidor.** Quien la use no debería instalar
Python, abrir un navegador ni tener conexión.

## Decisión

**pywebview + PyInstaller.** Un `.app` para macOS y un `.exe` para Windows, que
llevan adentro Python, el motor, spaCy y los dos modelos.

- pywebview abre una ventana nativa (WebKit en macOS, WebView2 en Windows) con la
  misma interfaz de `web/`.
- La interfaz llama a Python **directamente** por el puente de pywebview: los
  métodos de `desktop.Bridge` aparecen como `window.pywebview.api.<nombre>` y
  devuelven Promises. No hay HTTP entre la interfaz y el motor.
- La lógica que vivía en los endpoints pasa a `service.py`, un módulo sin
  transporte que recibe y devuelve JSON simple.
- **Se eliminan** FastAPI, la API HTTP, el contenedor y la autenticación por clave.

### Verificado en la documentación y el código de pywebview (v6.2.1)

- Las funciones se exponen con `js_api` y se llaman como `window.pywebview.api.X`;
  devuelven Promises; un error en Python rechaza la Promise con un `Error` cuyo
  `message` es `str(excepción)`.
- `window.pywebview.api` **no** está garantizado en `window.onload`: hay que esperar
  el evento `pywebviewready`. La interfaz lo hace.
- Cada llamada corre en un hilo aparte: un etiquetado largo no congela la ventana.
- `ALLOW_DOWNLOADS` es `False` por defecto. **Las descargas del navegador no
  funcionan dentro de la ventana**, así que guardar y abrir sesiones, fuentes y la
  bandeja pasa por diálogos nativos (`create_file_dialog`).
- pywebview declara sus dependencias por plataforma: `pyobjc` en macOS,
  `pythonnet` en Windows. No hay que declararlas aparte.
- pywebview levanta un servidor HTTP interno para entregar los archivos de la
  interfaz cuando se carga por ruta. No se puede desactivar. Escucha solo en la
  máquina local y no participa de las llamadas al motor.

### Verificado en el empaquetado (compilación de prueba en Linux)

- `pyinstaller-hooks-contrib` trae hooks para spaCy y thinc (código y datos). **No
  cubren** los modelos de idioma ni los metadatos con que spacy-legacy y
  spacy-loggers registran componentes; la configuración los agrega a mano.
- El binario congelado, corrido en un entorno limpio, carga los dos modelos,
  etiqueta, reparte por categoría y genera: el autotest pasa.
- Medido: 294 MB descomprimido, 123 MB comprimido, 1,2 s de autotest completo.

## Compilación

GitHub Actions, disparada por tag de versión:

| Runner | Arquitectura | Salida |
|---|---|---|
| `macos-latest` | arm64 (Apple Silicon) | `Verbasizer-macos-arm64.zip` |
| `windows-2025` | x64 | `Verbasizer-windows-x64.zip` |

Arquitecturas verificadas en la documentación de GitHub. `macos-14` figuraba en esa documentación pero GitHub ya lo había retirado: la primera compilación falló con "configuration not supported". Por eso macOS usa `macos-latest`, que según la documentación siempre apunta a la versión estable más nueva y es arm64. Windows queda fijado en `windows-2025`. Gratis e ilimitados en
repositorios públicos. Cada job corre los tests, compila, **ejecuta el autotest
dentro del binario** y solo entonces lo adjunta a un Release en borrador.

## Autoverificación

`--selftest` recorre el circuito completo sin abrir ventana. En Windows una
aplicación de ventana no tiene salida estándar (`sys.stdout` es `None`), así que
el reporte también puede escribirse a archivo con `--report`.

## Riesgos abiertos

Lo que no se pudo verificar fuera de una máquina real:

- **Compilación en macOS con PyInstaller.** La documentación de pywebview recomienda
  py2app para macOS y PyInstaller para Windows. Usamos PyInstaller en ambos para
  tener una sola configuración. Si en macOS falla, la alternativa es py2app.
- **Respuestas grandes por el puente.** pywebview devuelve el resultado a JS
  embebido en una llamada a `evaluate_js`. Para textos normales no pesa; con el
  límite de 2 MB serían ~28 MB por esa vía. No medido en una ventana real.
- **WebView2 en Windows.** pywebview usa el runtime instalado en el sistema. Que
  venga con Windows 11 actualizado es conocimiento general, no verificado acá.
- **Windows 11 en ARM.** Se compila x64. GitHub ofrece runners Windows arm64 si
  hiciera falta un build nativo.
- **Sin firma de código.** macOS y Windows advierten la primera vez. Firmar cuesta
  99 USD/año en Apple y un certificado aparte en Windows; no se justifica en esta
  etapa.

## Alternativas descartadas

- **Mantener FastAPI y abrir el navegador del sistema.** Funciona, pero es un
  servidor local con puerto, y la definición es no usar servidor.
- **Tkinter.** Viene con Python, pero el diseño de columnas con pesos, fichas
  bloqueables y procedencia por color es justo donde Tk pelea y CSS no.
- **Qt (PySide6).** Potente, pero más de 100 MB extra y una segunda forma de
  escribir interfaz, cuando la de HTML ya existe y está probada.
- **Electron o Tauri.** Agregan un segundo entorno (Node o Rust) para lo que
  pywebview ya resuelve desde Python.
