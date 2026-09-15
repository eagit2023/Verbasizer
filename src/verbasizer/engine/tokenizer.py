"""Tokenización de las fuentes.

Decisión de ADR-0002: la puntuación se preserva por defecto. El único cut-up
open source con columnas que relevamos la destruye por completo, y eso degrada
el resultado sin necesidad.

Sin dependencias externas a propósito: el motor es Python puro y determinístico.
"""

from __future__ import annotations

import re
import unicodedata

from .tokens import Fragment, Token

# Una "palabra" es una secuencia de caracteres alfanuméricos, permitiendo
# apóstrofos y guiones internos (d'Artagnan, cut-up, ¿qué?).
_WORD = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*|\d+(?:[.,]\d+)*", re.UNICODE)

# Puntuación pegada a la palabra que conviene conservar con ella.
_TRAILING = re.compile(r"[.,;:!?…)\]»\"”]+$")
_LEADING = re.compile(r"^[¡¿(\[«\"“]+")


def strip_punctuation(text: str) -> str:
    """Quita la puntuación de los bordes de una palabra."""
    text = _LEADING.sub("", text)
    return _TRAILING.sub("", text)


def split_lines(text: str) -> list[str]:
    """Divide un texto en frases.

    Corta por salto de línea y por puntuación de fin de oración. Es deliberadamente
    simple: no queremos una dependencia de NLP en el motor.
    """
    chunks: list[str] = []
    for raw_line in text.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        parts = re.split(r"(?<=[.!?…])\s+", raw_line)
        chunks.extend(p.strip() for p in parts if p.strip())
    return chunks


def tokenize(
    text: str,
    source: str,
    *,
    keep_punctuation: bool = True,
) -> list[Token]:
    """Convierte un texto en tokens con su procedencia.

    `source` es el nombre de la fuente, y viaja con cada token hasta el
    resultado final.
    """
    tokens: list[Token] = []
    for line_index, line in enumerate(split_lines(text)):
        position = 0
        for raw in line.split():
            word = raw if keep_punctuation else strip_punctuation(raw)
            if not _WORD.search(unicodedata.normalize("NFC", word)):
                continue
            tokens.append(
                Token(
                    text=word,
                    source=source,
                    line=line_index,
                    position=position,
                )
            )
            position += 1
    return tokens


def to_fragments(tokens: list[Token], unit: int = 1) -> list[Fragment]:
    """Agrupa tokens en fragmentos de `unit` palabras consecutivas.

    Los fragmentos nunca cruzan el límite de una frase ni mezclan fuentes: un
    fragmento de cinco palabras tiene que ser un tramo real del original para
    que signifique algo. Es el método manual de Bowie —cortar en secciones de
    cuatro o cinco palabras— cuando `unit` es mayor a 1.
    """
    if unit < 1:
        raise ValueError("La unidad atómica tiene que ser 1 o más")

    fragments: list[Fragment] = []
    buffer: list[Token] = []

    def flush() -> None:
        if buffer:
            fragments.append(Fragment(tuple(buffer)))
            buffer.clear()

    previous: Token | None = None
    for token in tokens:
        broke = previous is not None and (
            token.source != previous.source or token.line != previous.line
        )
        if broke:
            flush()
        buffer.append(token)
        if len(buffer) == unit:
            flush()
        previous = token
    flush()

    return fragments
