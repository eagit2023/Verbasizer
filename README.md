# Verbasizer

Herramienta de cut-up: reconstrucción del software que Ty Roberts construyó para
David Bowie entre 1994 y 1995, más los métodos manuales de William S. Burroughs y
Brion Gysin que lo precedieron.

**Estado: pre-alfa.** Aplicación de escritorio para macOS (Apple Silicon) y
Windows 11. Corre entera en la máquina: sin servidor, sin cuenta, sin internet.

---

## Por qué existe

Hay decenas de generadores de cut-up dando vueltas. Casi todos hacen lo mismo:
barajan un texto y te devuelven un bloque. Ninguno implementa las dos cosas que
distinguían al Verbasizer original —**peso y restricción gramatical por columna**— ni
las que hacían que el método sirviera para escribir de verdad: **las herramientas de
curaduría del resultado**.

Ni Burroughs ni Bowie usaban el output crudo. Burroughs lo llamaba *"sifting and
panning"*: la máquina produce material en bruto y el trabajo es elegir. Bowie leía la
salida del Verbasizer y seleccionaba a mano lo que le resonaba. Ese paso —el más
importante del método— no está implementado en ninguna herramienta existente; queda
tercerizado al copiar y pegar del usuario.

Este proyecto implementa el ciclo completo: generar, filtrar, guardar, iterar.

## Qué documenta

El código original del Verbasizer nunca se publicó y no hay evidencia de que sobreviva.
Lo que hay en `docs/research/` es una reconstrucción a partir de las fuentes públicas,
con una regla estricta: **cada afirmación está marcada según su estatus**.

| Marca | Significado |
|---|---|
| `[documentado]` | Hay fuente primaria o secundaria confiable, citada |
| `[supuesto]` | Inferencia nuestra, explicada y justificada |
| `[no verificado]` | Circula en fuentes secundarias, no pudimos confirmarlo |
| `[desconocido]` | Hueco real: nadie lo sabe, lo decidimos nosotros |

Esa separación es deliberada. Buena parte de lo que se repite en internet sobre el
Verbasizer es incorrecto —hay artículos que le atribuyen letras de discos grabados
quince años antes de que el software existiera—, y este repositorio no va a agregar
ruido a esa pila.

## Estructura

```
docs/research/      Reconstrucción histórica, con fuentes
docs/decisiones/    Registro de decisiones de arquitectura (ADR)
src/verbasizer/     Motor, servicio, aplicación de escritorio y CLI
web/                Interfaz (HTML/CSS/JS)
packaging/          Configuración de PyInstaller
.github/workflows/  Compilación automática para macOS y Windows
tests/              Tests
```

## Arquitectura

- **Motor**: Python puro, sin dependencias, determinístico dado un seed.
- **Servicio**: las operaciones de la aplicación (etiquetar, repartir, generar,
  regenerar) como funciones que reciben y devuelven JSON simple.
- **Ventana**: pywebview. Abre una ventana nativa —WebKit en macOS, WebView2 en
  Windows— y deja que la interfaz llame al servicio **directamente**, sin HTTP: cada
  llamada es una Promise del lado de JavaScript, y corre en su propio hilo para no
  congelar la ventana.
- **Interfaz**: JavaScript sin build step, sin framework. Es un proyecto sobre
  preservación de software; un bundle armado hoy no compila en cinco años.
- **Etiquetado gramatical**: spaCy, castellano e inglés.
- **Persistencia**: archivos JSON elegidos con diálogos del sistema. Una sesión, un
  archivo. Sin base de datos.

pywebview levanta internamente un servidor local solo para entregar los archivos de
la interfaz. No se configura, escucha solo en la propia máquina y no participa de las
llamadas al motor.

Ver `docs/decisiones/` para el detalle y las razones.

## Instalación

El motor no tiene dependencias, pero conviene un entorno virtual: los Python instalados
por Homebrew o por el sistema rechazan instalar paquetes fuera de uno (PEP 668).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Eso deja disponible el comando `verbasizer` y las herramientas de test. Cada vez que
abrís una terminal nueva hay que reactivar el entorno con `source .venv/bin/activate`.

Sin instalar nada, el motor también corre directo:

```bash
PYTHONPATH=src python3 -m verbasizer.cli generate texto.txt
```

### Etiquetado gramatical (opcional)

Hace falta solo para la restricción gramatical por columna. Agrega spaCy y los
modelos de idioma:

```bash
pip install -e ".[desktop,dev]"
python -m spacy download es_core_news_sm
python -m spacy download en_core_web_sm
```

Los modelos pesan unos 13 MB cada uno. Sin ellos, todo lo demás funciona igual.

`desktop` incluye pywebview, que instala por su cuenta lo que corresponde a cada
sistema: `pyobjc` en macOS, `pythonnet` en Windows.

## Uso

Por ahora solo desde la línea de comandos.

```bash
verbasizer generate texto.txt -c 5 -n 8
```

Cut-up por palabra, cinco columnas, ocho líneas. Cada tirada informa su semilla; pasarla
con `-s` reproduce el resultado exacto.

Opciones que importan:

| Opción | Qué hace |
|---|---|
| `-c, --columns` | Cantidad de columnas |
| `-w, --weights` | Peso por columna: `-w 1,8,1,1,2`. Peso 0 la silencia |
| `-u, --unit` | Palabras por fragmento. `1` = palabra suelta; `4` o `5` = el método manual de Bowie |
| `-r, --rule` | Plantilla de estructura: `-r 6,4,6,4` fragmentos por línea, cíclica |
| `-s, --seed` | Reproducir una tirada anterior |
| `--show-origin` | Mostrar de qué columna y fuente vino cada fragmento |
| `--strip-punctuation` | Descartar la puntuación (por defecto se conserva) |
| `-o, --save` | Guardar la sesión como JSON |
| `--lang es\|en` | Etiquetar gramaticalmente con spaCy |
| `--by-pos` | Una columna por categoría: `--by-pos NOUN,VERB,ADJ`. Requiere `--lang` |

Se le pueden pasar varias fuentes a la vez: es ahí donde aparecen los *intersection
points* de Burroughs, las colisiones entre textos que no tienen nada que ver.

```bash
verbasizer generate diario.txt informe.txt -c 3 -u 4 -w 1,8,1 -n 6 -l 3 --show-origin
```

Columnas restringidas por categoría gramatical — la configuración que describía Ty
Roberts, y lo que ninguna otra herramienta de cut-up implementa:

```bash
verbasizer generate uno.txt dos.txt --lang es --by-pos NOUN,VERB,ADJ -w 1,5,1
```

Tests:

```bash
pytest -q
```

## Interfaz

Desde el código:

```bash
verbasizer-app            # o: verbasizer-app --debug, con herramientas de inspección
```

O con la aplicación compilada, ver más abajo. El flujo es el del Verbasizer original,
en cinco pasos:

1. **Fuentes** — pegá o subí dos o más textos. El idioma solo hace falta si vas a usar
   categorías gramaticales.
2. **Columnas** — repartí uno a uno o por categoría. Cada columna tiene su peso
   ajustable y su restricción gramatical.
3. **Generar** — líneas, largo o regla, semilla. Clic en un fragmento para **fijarlo**;
   "Regenerar sin tocar lo fijado" vuelve a tirar preservando lo que ya funcionaba.
4. **Bandeja** — las líneas que se salvan. "Usar como fuente" las devuelve al circuito,
   que es el fold-in aplicado al propio material.
5. **Historial** — cada tirada con su semilla, para volver a cualquiera.

Los colores indican de qué fuente vino cada fragmento. Atajos: `g` genera, `r` regenera.

Las sesiones se guardan y se abren como archivo con "Guardar sesión" y "Abrir sesión",
usando los diálogos del sistema. La bandeja se puede exportar como `.txt`.

## Aplicación de escritorio

### Descargar

Los binarios compilados están en la sección **Releases** del repositorio:

- `Verbasizer-macos-arm64.zip` — macOS con Apple Silicon (M1 en adelante)
- `Verbasizer-windows-x64.zip` — Windows 11 x64

No hace falta instalar Python ni nada más: todo viaja adentro.

### Primer arranque

La aplicación no está firmada con un certificado de desarrollador, así que el
sistema avisa la primera vez. Es esperable.

**macOS.** Descomprimir y mover `Verbasizer.app` a Aplicaciones. Al abrirla, macOS
dice que no puede verificar al desarrollador. Clic derecho sobre la app → **Abrir** →
**Abrir**. Si no ofrece la opción: Ajustes del Sistema → Privacidad y seguridad →
**Abrir igualmente**. Solo la primera vez.

**Windows.** Descomprimir la carpeta completa —el `.exe` necesita lo que tiene al
lado— y abrir `Verbasizer.exe`. SmartScreen muestra "Windows protegió su PC":
**Más información** → **Ejecutar de todas formas**. Solo la primera vez.

Windows necesita el runtime **WebView2**, que la aplicación usa para dibujar la
ventana. Viene con Windows 11 actualizado; si faltara, Microsoft lo distribuye como
"WebView2 Runtime".

### Verificar una instalación

```bash
# macOS
Verbasizer.app/Contents/MacOS/Verbasizer --selftest

# Windows (PowerShell): la app no tiene consola, el reporte va a archivo
Start-Process .\Verbasizer.exe -ArgumentList "--selftest","--report","reporte.json" -Wait
Get-Content reporte.json
```

Recorre el circuito completo —modelos, etiquetado, reparto, generación— sin abrir
ventana, y dice si algo falta.

### Compilar

Se compila solo en GitHub Actions al publicar un tag de versión:

```bash
git tag v0.2.0
git push --tags
```

Cada plataforma corre los tests, compila, **ejecuta el autotest dentro del binario
compilado** y, si todo pasa, lo adjunta a un Release en borrador para revisarlo antes
de publicarlo. También se puede disparar a mano desde la pestaña Actions.

Para compilar localmente, en la plataforma de destino:

```bash
pip install -e ".[desktop,build]"
python -m spacy download es_core_news_sm
python -m spacy download en_core_web_sm
pyinstaller packaging/verbasizer.spec --noconfirm
```

**Medido** (compilación en Linux, como referencia; macOS y Windows pueden variar):
294 MB descomprimido, 123 MB comprimido, autotest completo en 1,2 s. Más de un
tercio del peso son las extensiones compiladas de spaCy, que no se pueden recortar.

## Hoja de ruta

1. ~~Motor + CLI mínimo~~ ✅
2. ~~Etiquetado gramatical~~ ✅
3. ~~Interfaz de columnas~~ ✅
4. ~~Curaduría (bandeja, lock, historial, procedencia)~~ ✅
5. ~~Aplicación de escritorio para macOS y Windows~~ ✅
6. Módulos históricos (cuadrantes, fold-in, tres columnas, permutación de Gysin)

## Licencia

GPL-3.0.

La razón es concreta: el modelo de spaCy para castellano (`es_core_news_sm`) se
distribuye bajo GPL-3.0, y usarlo obliga a que el proyecto entero lo sea. El modelo de
inglés (`en_core_web_sm`) es MIT. Detalle completo en
`docs/decisiones/ADR-0001-stack.md`.

## Sobre el nombre

"Verbasizer" es el nombre que David Bowie usó para el programa original. Este proyecto
no tiene relación con Bowie, con su patrimonio ni con Ty Roberts. Es una reconstrucción
independiente hecha desde fuentes públicas, y el nombre se usa como referencia histórica
y crédito, no como marca.
