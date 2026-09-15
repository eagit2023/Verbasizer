# Verbasizer

Herramienta de cut-up: reconstrucción del software que Ty Roberts construyó para
David Bowie entre 1994 y 1995, más los métodos manuales de William S. Burroughs y
Brion Gysin que lo precedieron.

**Estado: pre-alfa.** No hay nada funcional todavía. Este repositorio arranca con la
investigación histórica documentada y la arquitectura definida; el código viene después.

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

## Hoja de ruta

1. Motor + CLI mínimo
2. API
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
