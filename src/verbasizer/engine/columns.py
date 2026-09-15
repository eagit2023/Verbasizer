"""Columnas: el elemento central del Verbasizer.

Cada columna tiene fragmentos, un peso y, opcionalmente, una restricción
gramatical. Las dos últimas son lo que ninguna otra herramienta de cut-up
implementa (ver docs/research/04-estado-del-arte.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .tokens import Fragment


@dataclass
class Column:
    """Una columna del tablero.

    - `weight`: probabilidad relativa de que esta columna aporte el siguiente
      fragmento. Peso 3 contra peso 1 aparece tres veces más seguido.
      Es la semántica de ruleta decidida en ADR-0002.
    - `pos_filter`: categoría gramatical (UPOS) que admite esta columna. Solo
      filtra fragmentos que ya vengan etiquetados; si nadie etiquetó, no filtra
      nada. El motor no etiqueta: eso es trabajo del backend con spaCy.
    - `locked`: la columna no se regenera. Reservado para la fase de curaduría.
    """

    name: str
    fragments: list[Fragment] = field(default_factory=list)
    weight: float = 1.0
    pos_filter: str | None = None
    locked: bool = False

    def __post_init__(self) -> None:
        if self.weight < 0:
            raise ValueError(f"El peso de '{self.name}' no puede ser negativo")

    def eligible(self) -> list[Fragment]:
        """Fragmentos que esta columna puede aportar."""
        if self.pos_filter is None:
            return list(self.fragments)
        wanted = self.pos_filter.upper()
        return [f for f in self.fragments if f.pos is not None and f.pos.upper() == wanted]

    def is_usable(self) -> bool:
        return self.weight > 0 and bool(self.eligible())


def round_robin(fragments: list[Fragment], count: int, *, prefix: str = "col") -> list[Column]:
    """Reparte fragmentos entre `count` columnas, alternando uno a uno.

    Es el reparto por defecto, equivalente al que hacía el único cut-up open
    source con columnas que encontramos — pero sin su error de fuera-por-uno:
    acá `count` columnas son exactamente `count`.
    """
    if count < 1:
        raise ValueError("Hacen falta al menos 1 columna")

    columns = [Column(name=f"{prefix}{i + 1}") for i in range(count)]
    for index, fragment in enumerate(fragments):
        columns[index % count].fragments.append(fragment)
    return columns


def by_pos(fragments: list[Fragment], categories: list[str]) -> list[Column]:
    """Arma una columna por categoría gramatical.

    Reproduce la configuración que describía Ty Roberts: columnas restringidas a
    sustantivos, verbos, adjetivos. Requiere que los fragmentos vengan
    etiquetados; los que no encajen en ninguna categoría quedan afuera.
    """
    columns = [Column(name=c.upper(), pos_filter=c.upper()) for c in categories]
    index = {c.pos_filter: c for c in columns}
    for fragment in fragments:
        if fragment.pos is None:
            continue
        column = index.get(fragment.pos.upper())
        if column is not None:
            column.fragments.append(fragment)
    return columns
