"""Conversión entre los objetos del motor y estructuras JSON.

Está separado porque lo usan dos consumidores: el guardado de sesiones y la API.
Un solo lugar donde vive el formato.
"""

from __future__ import annotations

from typing import Any

from .columns import Column
from .generator import Generation
from .tokens import Fragment, Line, Placement, Token


def token_to_dict(token: Token) -> dict[str, Any]:
    return {
        "text": token.text,
        "source": token.source,
        "line": token.line,
        "position": token.position,
        "pos": token.pos,
    }


def token_from_dict(data: dict[str, Any]) -> Token:
    return Token(
        text=data["text"],
        source=data["source"],
        line=data["line"],
        position=data["position"],
        pos=data.get("pos"),
    )


def fragment_to_list(fragment: Fragment) -> list[dict[str, Any]]:
    return [token_to_dict(t) for t in fragment.tokens]


def fragment_from_list(data: list[dict[str, Any]]) -> Fragment:
    return Fragment(tuple(token_from_dict(t) for t in data))


def column_to_dict(column: Column) -> dict[str, Any]:
    return {
        "name": column.name,
        "weight": column.weight,
        "pos_filter": column.pos_filter,
        "locked": column.locked,
        "fragments": [fragment_to_list(f) for f in column.fragments],
    }


def column_from_dict(data: dict[str, Any]) -> Column:
    return Column(
        name=data["name"],
        weight=data.get("weight", 1.0),
        pos_filter=data.get("pos_filter"),
        locked=data.get("locked", False),
        fragments=[fragment_from_list(f) for f in data.get("fragments", [])],
    )


def generation_to_dict(generation: Generation) -> dict[str, Any]:
    return {
        "seed": generation.seed,
        "rule": generation.rule,
        "lines": [
            {
                "text": line.text,
                "placements": [
                    {
                        "text": placement.text,
                        "column": placement.column,
                        "source": placement.fragment.source,
                        "tokens": fragment_to_list(placement.fragment),
                    }
                    for placement in line.placements
                ],
            }
            for line in generation.lines
        ],
    }


def generation_from_dict(data: dict[str, Any]) -> Generation:
    generation = Generation(seed=data["seed"], rule=list(data["rule"]))
    for raw_line in data.get("lines", []):
        line = Line()
        for raw in raw_line.get("placements", []):
            line.placements.append(
                Placement(
                    fragment=fragment_from_list(raw["tokens"]),
                    column=raw["column"],
                )
            )
        generation.lines.append(line)
    return generation
