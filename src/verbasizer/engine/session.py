"""La sesión: estado completo de trabajo, serializable a JSON.

Una sesión, un archivo. Sin base de datos. El archivo guarda las fuentes, las
columnas con sus pesos y restricciones, cada tirada con su semilla, y la bandeja
de líneas guardadas.

La bandeja es el cuaderno de Burroughs adentro del programa: sin ella, el usuario
termina copiando a un archivo aparte, que es exactamente lo que hace fracasar a
todas las herramientas de cut-up existentes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .columns import Column
from .generator import Generation
from .tokens import Fragment, Line, Placement, Token

FORMAT_VERSION = 1


@dataclass
class Source:
    """Un texto cargado, con sus tokens ya extraídos."""

    name: str
    text: str
    tokens: list[Token] = field(default_factory=list)


@dataclass
class Session:
    """Estado completo de trabajo."""

    name: str = "sin título"
    unit: int = 1
    keep_punctuation: bool = True
    sources: list[Source] = field(default_factory=list)
    columns: list[Column] = field(default_factory=list)
    generations: list[Generation] = field(default_factory=list)
    saved: list[str] = field(default_factory=list)

    # ---------- bandeja de guardados ----------

    def keep(self, text: str) -> None:
        """Manda una línea a la bandeja."""
        if text and text not in self.saved:
            self.saved.append(text)

    def discard(self, text: str) -> None:
        if text in self.saved:
            self.saved.remove(text)

    # ---------- serialización ----------

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT_VERSION,
            "name": self.name,
            "unit": self.unit,
            "keep_punctuation": self.keep_punctuation,
            "sources": [
                {
                    "name": s.name,
                    "text": s.text,
                    "tokens": [_token_to_dict(t) for t in s.tokens],
                }
                for s in self.sources
            ],
            "columns": [
                {
                    "name": c.name,
                    "weight": c.weight,
                    "pos_filter": c.pos_filter,
                    "locked": c.locked,
                    "fragments": [
                        [_token_to_dict(t) for t in f.tokens] for f in c.fragments
                    ],
                }
                for c in self.columns
            ],
            "generations": [
                {
                    "seed": g.seed,
                    "rule": g.rule,
                    "lines": [
                        [
                            {
                                "column": p.column,
                                "tokens": [_token_to_dict(t) for t in p.fragment.tokens],
                            }
                            for p in line.placements
                        ]
                        for line in g.lines
                    ],
                }
                for g in self.generations
            ],
            "saved": list(self.saved),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Session:
        version = data.get("format")
        if version != FORMAT_VERSION:
            raise ValueError(
                f"Formato de sesión desconocido: {version!r} "
                f"(esta versión lee {FORMAT_VERSION})"
            )

        session = cls(
            name=data.get("name", "sin título"),
            unit=data.get("unit", 1),
            keep_punctuation=data.get("keep_punctuation", True),
            saved=list(data.get("saved", [])),
        )

        for raw in data.get("sources", []):
            session.sources.append(
                Source(
                    name=raw["name"],
                    text=raw["text"],
                    tokens=[_token_from_dict(t) for t in raw.get("tokens", [])],
                )
            )

        for raw in data.get("columns", []):
            session.columns.append(
                Column(
                    name=raw["name"],
                    weight=raw.get("weight", 1.0),
                    pos_filter=raw.get("pos_filter"),
                    locked=raw.get("locked", False),
                    fragments=[
                        Fragment(tuple(_token_from_dict(t) for t in frag))
                        for frag in raw.get("fragments", [])
                    ],
                )
            )

        for raw in data.get("generations", []):
            generation = Generation(seed=raw["seed"], rule=list(raw["rule"]))
            for raw_line in raw.get("lines", []):
                line = Line()
                for raw_placement in raw_line:
                    fragment = Fragment(
                        tuple(_token_from_dict(t) for t in raw_placement["tokens"])
                    )
                    line.placements.append(
                        Placement(fragment=fragment, column=raw_placement["column"])
                    )
                generation.lines.append(line)
            session.generations.append(generation)

        return session

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> Session:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _token_to_dict(token: Token) -> dict[str, Any]:
    return {
        "text": token.text,
        "source": token.source,
        "line": token.line,
        "position": token.position,
        "pos": token.pos,
    }


def _token_from_dict(data: dict[str, Any]) -> Token:
    return Token(
        text=data["text"],
        source=data["source"],
        line=data["line"],
        position=data["position"],
        pos=data.get("pos"),
    )
