"""Unidades de texto del motor.

Un `Token` es una palabra con su procedencia. Un `Fragment` es la unidad atómica
que el generador coloca en una línea: una o más palabras consecutivas de la misma
fuente (ver ADR-0002, decisión 1).

La procedencia no es decorativa: los "intersection points" de Burroughs eran
colisiones entre textos determinados, y sin saber qué chocó con qué no se puede
repetir ni ajustar la mezcla que funcionó.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Token:
    """Una palabra con su origen.

    `pos` es la categoría gramatical en notación UPOS (NOUN, VERB, ADJ, ...).
    Queda en None hasta que un etiquetador la complete; el motor no etiqueta,
    solo respeta lo que le pasen.
    """

    text: str
    source: str
    line: int
    position: int
    pos: str | None = None

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True)
class Fragment:
    """Una o más palabras consecutivas de la misma fuente."""

    tokens: tuple[Token, ...]

    def __post_init__(self) -> None:
        if not self.tokens:
            raise ValueError("Un fragmento no puede estar vacío")

    @property
    def text(self) -> str:
        return " ".join(t.text for t in self.tokens)

    @property
    def head(self) -> Token:
        """Token de referencia para la restricción gramatical.

        Cuando la unidad atómica es mayor a una palabra, un fragmento no tiene
        una sola categoría gramatical. Se usa la del primer token. Es una
        convención nuestra, documentada en ADR-0002.
        """
        return self.tokens[0]

    @property
    def source(self) -> str:
        return self.tokens[0].source

    @property
    def pos(self) -> str | None:
        return self.head.pos

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True)
class Placement:
    """Un fragmento ya colocado en una línea, con la columna que lo aportó."""

    fragment: Fragment
    column: str

    @property
    def text(self) -> str:
        return self.fragment.text


@dataclass
class Line:
    """Una línea generada."""

    placements: list[Placement] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(p.text for p in self.placements)

    def __str__(self) -> str:
        return self.text
