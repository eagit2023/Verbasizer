"""El generador.

Determinístico: la misma semilla, las mismas columnas y la misma regla producen
exactamente el mismo resultado. Eso permite reproducir una sesión que funcionó,
que es algo que ninguna herramienta de cut-up existente ofrece.

El peso es una ruleta: la probabilidad de que una columna aporte el siguiente
fragmento es su peso sobre la suma de los pesos de las columnas utilizables
(ADR-0002, decisión 2).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .columns import Column
from .tokens import Fragment, Line, Placement

# Cuántas veces reintentar antes de aceptar un fragmento repetido en una línea.
_RETRY_LIMIT = 12


@dataclass
class Generation:
    """El resultado de una tirada, con todo lo necesario para reproducirla."""

    seed: int
    rule: list[int]
    lines: list[Line] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)

    def __str__(self) -> str:
        return self.text


def _pick_column(rng: random.Random, columns: list[Column]) -> Column | None:
    """Elige una columna por ruleta, proporcional al peso."""
    usable = [c for c in columns if c.is_usable()]
    if not usable:
        return None

    total = sum(c.weight for c in usable)
    threshold = rng.uniform(0.0, total)
    running = 0.0
    for column in usable:
        running += column.weight
        if threshold <= running:
            return column
    return usable[-1]


def _pick_fragment(
    rng: random.Random,
    columns: list[Column],
    used: set[int],
    avoid_repeats: bool,
) -> tuple[Fragment, Column] | None:
    """Elige columna y fragmento, evitando repetir dentro de la misma línea."""
    for _ in range(_RETRY_LIMIT):
        column = _pick_column(rng, columns)
        if column is None:
            return None
        pool = column.eligible()
        fragment = pool[rng.randrange(len(pool))]
        if not avoid_repeats or id(fragment) not in used:
            return fragment, column

    # Se agotaron los reintentos: se acepta la repetición antes que devolver
    # una línea corta.
    column = _pick_column(rng, columns)
    if column is None:
        return None
    pool = column.eligible()
    return pool[rng.randrange(len(pool))], column


def generate(
    columns: list[Column],
    *,
    rule: list[int] | None = None,
    lines: int = 8,
    words_per_line: int = 6,
    seed: int | None = None,
    avoid_repeats: bool = True,
) -> Generation:
    """Produce una tirada.

    `rule` es una plantilla de estructura al estilo de las Rules de Liptikl: una
    lista de enteros donde cada número es la cantidad de fragmentos de una línea.
    Se repite cíclicamente hasta completar `lines`. Si no se pasa, todas las
    líneas tienen `words_per_line` fragmentos.

    `seed` se guarda en el resultado. Si no se pasa, se genera una y se registra
    igual, para que cualquier tirada sea reproducible después.
    """
    if not columns:
        raise ValueError("Hacen falta columnas para generar")
    if lines < 1:
        raise ValueError("Hay que generar al menos una línea")

    if rule is None:
        rule = [words_per_line]
    if any(n < 1 for n in rule):
        raise ValueError("Cada línea de la regla tiene que tener al menos 1 fragmento")

    if seed is None:
        seed = random.randrange(2**32)
    rng = random.Random(seed)

    if not any(c.is_usable() for c in columns):
        raise ValueError(
            "Ninguna columna puede aportar fragmentos: revisá pesos y restricciones "
            "gramaticales (una columna con pos_filter sobre texto sin etiquetar "
            "nunca entrega nada)"
        )

    result = Generation(seed=seed, rule=list(rule))
    for index in range(lines):
        width = rule[index % len(rule)]
        used: set[int] = set()
        line = Line()
        for _ in range(width):
            chosen = _pick_fragment(rng, columns, used, avoid_repeats)
            if chosen is None:
                break
            fragment, column = chosen
            used.add(id(fragment))
            line.placements.append(Placement(fragment=fragment, column=column.name))
        result.lines.append(line)

    return result
