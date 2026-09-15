# Verbasizer

Herramienta de cut-up: reconstrucción del software que Ty Roberts construyó para
David Bowie entre 1994 y 1995, más los métodos manuales de William S. Burroughs y
Brion Gysin que lo precedieron.

**Estado: pre-alfa.** El motor funciona y tiene tests. No hay interfaz todavía.

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
src/verbasizer/     Motor, API y CLI
web/                Interfaz de navegador
tests/              Tests del motor
```

## Arquitectura

- **Motor**: Python puro, sin dependencias, determinístico dado un seed. No sabe que
  existe HTTP. Sirve igual desde la API o desde la línea de comandos.
- **Backend**: FastAPI. Dos responsabilidades: exponer el motor y etiquetar
  gramaticalmente con spaCy (castellano e inglés).
- **Frontend**: JavaScript sin build step, sin framework. Es un proyecto sobre
  preservación de software; un bundle armado hoy no compila en cinco años.
- **Persistencia**: archivos JSON. Una sesión, un archivo. Sin base de datos.

El etiquetado gramatical ocurre **una sola vez, al cargar cada fuente**. Generar es
matemática pura. Eso significa que una vez etiquetada una sesión, todo el resto
—columnas, pesos, generación, curaduría— funciona sin servidor.

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
pip install -e ".[server,dev]"
python -m spacy download es_core_news_sm
python -m spacy download en_core_web_sm
```

Los modelos pesan unos 13 MB cada uno. Sin ellos, todo lo demás funciona igual.

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

## API

```bash
verbasizer serve
```

Levanta en `http://127.0.0.1:8000`. Documentación interactiva en `/docs`.

| Endpoint | Qué hace |
|---|---|
| `GET /api/health` | Estado y qué modelos de idioma están instalados |
| `POST /api/tag` | Tokeniza un texto, con etiquetado gramatical si se pide idioma |
| `POST /api/distribute` | Reparte tokens en columnas: uno a uno, o por categoría |
| `POST /api/generate` | Genera una tirada, con la procedencia de cada fragmento |

La API es chica a propósito. Lo único que exige servidor es el etiquetado, porque
spaCy es Python y el navegador no puede correrlo; el resto puede vivir del lado del
cliente una vez que los tokens están etiquetados.

## Hoja de ruta

1. ~~Motor + CLI mínimo~~ ✅
2. ~~API~~ ✅
3. Interfaz de columnas
4. Curaduría (bandeja, lock, historial, procedencia)
5. Módulos históricos (cuadrantes, fold-in, tres columnas, permutación de Gysin)
6. Empaquetado como aplicación de escritorio

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
