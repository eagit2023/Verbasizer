"""Motor de generación.

Python puro y determinístico: la misma semilla produce el mismo resultado. No
sabe que existe HTTP ni spaCy — recibe tokens ya etiquetados o sin etiquetar y
hace su trabajo igual.

Las decisiones de diseño y los huecos históricos que las motivan están en
docs/decisiones/ADR-0002-motor.md.
"""

from .columns import Column, by_pos, round_robin
from .generator import Generation, generate
from .session import Session, Source
from .tokenizer import to_fragments, tokenize
from .tokens import Fragment, Line, Placement, Token

__all__ = [
    "Column",
    "Fragment",
    "Generation",
    "Line",
    "Placement",
    "Session",
    "Source",
    "Token",
    "by_pos",
    "generate",
    "round_robin",
    "to_fragments",
    "tokenize",
]
