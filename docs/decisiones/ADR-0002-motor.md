# ADR-0002 — Semántica del motor

**Fecha:** 2026-09-15
**Estado:** aceptada

## Contexto

La especificación del Verbasizer tiene huecos que ninguna fuente resuelve (ver
`docs/research/03-verbasizer-spec.md`). Estas tres decisiones no son reconstrucción
histórica: son diseño nuestro, y quedan registradas como tales.

---

## 1. Unidad atómica

**Hueco:** no se sabe si el Verbasizer trabajaba con palabras sueltas o con sintagmas.
Bowie a mano cortaba fragmentos de 4-5 palabras; en el software parece haber sido palabra.

**Decisión:** configurable, **default palabra**. El modo sintagma se cubre con el
parámetro de tamaño de fragmento, que además permite reproducir el método manual de
Bowie.

**Implementación:** un fragmento nunca cruza el límite de una frase ni mezcla fuentes. Un
tramo de cinco palabras tiene que ser un tramo real del original para significar algo.

---

## 2. Qué significa el peso

**Hueco:** Roberts dice que las columnas *"could be weighted"* y nada más.

**Decisión: ruleta.** El peso es la probabilidad relativa de que esa columna aporte el
siguiente fragmento al armar la línea. Peso 3 contra peso 1 significa que aparece tres
veces más seguido.

**Implementación:** la ruleta se calcula solo sobre las columnas *utilizables* — peso
mayor a cero y con al menos un fragmento que pase su restricción gramatical. Un peso de
cero silencia la columna sin borrarla.

**Alternativa considerada y descartada:** que el peso fije cuántos slots ocupa la columna
en cada línea. Produce resultados rígidos y previsibles — la misma forma en todas las
líneas — que es lo contrario de lo que se busca.

---

## 3. Categoría gramatical

**Hueco:** `[supuesto]` que en el original la declaración era manual por columna.

**Decisión: declaración manual, con el etiquetador sugiriendo.** Al cargar un texto,
spaCy clasifica automáticamente cada palabra; el usuario decide qué categoría lleva cada
columna. Se respeta el comportamiento histórico y se elimina el trabajo tedioso.

**Implementación:** el motor **no etiqueta**. Recibe tokens con o sin categoría y filtra
según lo que le hayan puesto; el etiquetado es responsabilidad del backend (fase 2). Eso
mantiene el motor sin dependencias y testeable.

**Convención propia:** cuando la unidad atómica es mayor a una palabra, un fragmento no
tiene una sola categoría gramatical. Se usa la del **primer token** del fragmento. No hay
antecedente histórico para esto; es decisión nuestra.

---

## Decisiones ya tomadas

**Puntuación:** se preserva, como opción activable. `[desconocido]` qué hacía el original.
El único cut-up open source con columnas que existe la destruye por completo, y eso
degrada el resultado sin necesidad.

**Seed:** cada generación guarda la semilla del generador, para poder reproducir una
sesión exacta. Sin antecedente histórico; es sentido común de software.

**Procedencia:** cada palabra del resultado registra de qué fuente y qué columna vino.
No es adorno — los *"intersection points"* de Burroughs eran colisiones entre textos
determinados, y sin saber qué chocó con qué no se puede repetir ni ajustar la mezcla que
funcionó.

---

## Peso adaptativo — propuesto y reservado

La idea: que marcar un resultado como bueno ajuste los pesos de las columnas que lo
produjeron, de modo que la herramienta aprenda qué mezcla está funcionando.

**Reservado para una segunda etapa, o descartado.** Tiene un riesgo real: converge hacia
lo que ya le gusta al usuario y mata lo inesperado, que es exactamente para lo que existe
el método.
