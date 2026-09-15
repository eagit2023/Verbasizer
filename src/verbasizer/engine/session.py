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
from .serialization import (
    column_from_dict,
    column_to_dict,
    generation_from_dict,
    generation_to_dict,
    token_from_dict,
    token_to_dict,
)
from .tokens import Token

FORMAT_VERSION = 1


@dataclass
class Source:
    """Un texto cargado, con sus tokens ya extraídos.

    `lang` queda en None si el texto se tokenizó sin etiquetador.
    """

    name: str
    text: str
    lang: str | None = None
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
                    "lang": s.lang,
                    "tokens": [token_to_dict(t) for t in s.tokens],
                }
                for s in self.sources
            ],
            "columns": [column_to_dict(c) for c in self.columns],
            "generations": [generation_to_dict(g) for g in self.generations],
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
                    lang=raw.get("lang"),
                    tokens=[token_from_dict(t) for t in raw.get("tokens", [])],
                )
            )

        for raw in data.get("columns", []):
            session.columns.append(column_from_dict(raw))

        for raw in data.get("generations", []):
            session.generations.append(generation_from_dict(raw))

        return session

    def save(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> Session:
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

